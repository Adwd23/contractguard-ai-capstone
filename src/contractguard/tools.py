"""MCP-style function-tool registry and real contract-analysis tools."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
import json
import math
import mimetypes
from pathlib import Path
import re
import shutil
from typing import Any, Callable, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pypdf import PdfReader

from .config import Settings
from .guardrails import mask_pii
from .models import ToolCall, ToolObservation
from .observability import Observability

InputT = TypeVar("InputT", bound=BaseModel)


class ToolExecutionError(RuntimeError):
    pass


@dataclass(slots=True)
class FunctionTool(Generic[InputT]):
    name: str
    description: str
    input_model: type[InputT]
    handler: Callable[[InputT], Any]

    @property
    def json_schema(self) -> dict[str, Any]:
        return self.input_model.model_json_schema()

    def invoke(self, arguments: dict[str, Any]) -> Any:
        try:
            validated = self.input_model.model_validate(arguments)
        except ValidationError as exc:
            raise ToolExecutionError(f"Invalid arguments for tool {self.name}: {exc}") from exc
        return self.handler(validated)


class ToolRegistry:
    """A small function-calling interface: name + description + JSON schema + invoke."""

    def __init__(self, observability: Observability):
        self._tools: dict[str, FunctionTool[Any]] = {}
        self.observability = observability

    def register(self, tool: FunctionTool[Any]) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def describe(self, names: set[str] | None = None) -> list[dict[str, Any]]:
        selected = (
            tool
            for name, tool in self._tools.items()
            if names is None or name in names
        )
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.json_schema,
            }
            for tool in selected
        ]

    def describe_openai(self, names: set[str] | None = None) -> list[dict[str, Any]]:
        """Return standard local function definitions for model tool calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": item["name"],
                    "description": item["description"],
                    "parameters": item["input_schema"],
                },
            }
            for item in self.describe(names)
        ]

    def call(self, call: ToolCall, *, thread_id: str) -> tuple[Any, ToolObservation]:
        if call.tool_name not in self._tools:
            raise ToolExecutionError(f"Unknown tool: {call.tool_name}")
        tool = self._tools[call.tool_name]
        timing: dict[str, float] = {}
        try:
            with self.observability.tool(tool.name, thread_id, call.call_id) as timing:
                output = tool.invoke(call.arguments)
        except Exception as exc:
            observation = ToolObservation(
                call_id=call.call_id,
                tool_name=call.tool_name,
                status="error",
                summary=f"{type(exc).__name__}: {exc}",
                output=None,
                latency_ms=timing.get("latency_ms", 0.0),
            )
            return None, observation

        summary = _summarize_tool_output(output)
        observation = ToolObservation(
            call_id=call.call_id,
            tool_name=call.tool_name,
            status="success",
            summary=summary,
            output=output,
            latency_ms=timing.get("latency_ms", 0.0),
        )
        return output, observation


class StrictToolInput(BaseModel):
    """Base class for tool arguments: reject undeclared model-generated fields."""

    model_config = ConfigDict(extra="forbid")


class ReadContractInput(StrictToolInput):
    contract_path: str | None = None
    contract_text: str | None = Field(default=None, max_length=1_000_000)
    max_chars: int = Field(default=250_000, ge=1000, le=1_000_000)


class ExtractClausesInput(StrictToolInput):
    contract_text: str = Field(min_length=20)


class SearchPoliciesInput(StrictToolInput):
    query: str = Field(min_length=2)
    topic: str = "general"
    top_k: int = Field(default=3, ge=1, le=10)
    attempt: int = Field(default=0, ge=0)
    simulate_primary_failure: bool = False


class CalculateRiskInput(StrictToolInput):
    findings: list[dict[str, Any]]
    contract_value_sar: float = Field(default=0, ge=0)
    approval_risk_threshold: int = Field(default=50, ge=0, le=100)
    approval_value_threshold_sar: float = Field(default=500_000, ge=0)


class MaskPIIInput(StrictToolInput):
    text: str


class StoreArtifactInput(StrictToolInput):
    thread_id: str = Field(
        min_length=3,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    markdown: str = Field(min_length=10)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyKnowledgeBase:
    def __init__(self, policy_dir: Path):
        self.policy_dir = policy_dir
        self.documents = self._load_documents()
        self._corpus_tokens = [self._tokenize(doc["content"]) for doc in self.documents]
        self._average_length = (
            sum(len(tokens) for tokens in self._corpus_tokens) / len(self._corpus_tokens)
            if self._corpus_tokens
            else 1.0
        )
        self._document_frequency: dict[str, int] = {}
        for tokens in self._corpus_tokens:
            for token in set(tokens):
                self._document_frequency[token] = self._document_frequency.get(token, 0) + 1

    def _load_documents(self) -> list[dict[str, str]]:
        docs: list[dict[str, str]] = []
        for path in sorted(self.policy_dir.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            docs.append({"name": path.stem.replace("_", " ").title(), "path": str(path), "content": content})
        if not docs:
            raise ToolExecutionError(f"No policy documents found in {self.policy_dir}")
        return docs

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[A-Za-z0-9_]+", text.lower())

    def search(self, query: str, *, topic: str, top_k: int) -> list[dict[str, Any]]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        n_docs = max(len(self.documents), 1)
        scored: list[tuple[float, int]] = []
        k1, b = 1.5, 0.75
        for index, tokens in enumerate(self._corpus_tokens):
            token_counts: dict[str, int] = {}
            for token in tokens:
                token_counts[token] = token_counts.get(token, 0) + 1
            score = 0.0
            doc_len = max(len(tokens), 1)
            for token in query_tokens:
                df = self._document_frequency.get(token, 0)
                idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                tf = token_counts.get(token, 0)
                denominator = tf + k1 * (1 - b + b * doc_len / self._average_length)
                if denominator:
                    score += idf * (tf * (k1 + 1)) / denominator
            if score > 0:
                scored.append((score, index))
        scored.sort(reverse=True)

        results: list[dict[str, Any]] = []
        for score, index in scored[:top_k]:
            doc = self.documents[index]
            excerpt, section = self._best_excerpt(doc["content"], query_tokens)
            results.append(
                {
                    "policy_name": doc["name"],
                    "policy_path": doc["path"],
                    "section": section,
                    "excerpt": excerpt,
                    "score": round(score, 4),
                    "topic": topic,
                }
            )
        return results

    @staticmethod
    def _best_excerpt(content: str, query_tokens: list[str]) -> tuple[str, str]:
        blocks = [block.strip() for block in re.split(r"\n\s*\n", content) if block.strip()]
        best_block = blocks[0] if blocks else content[:500]
        best_score = -1
        current_section = "General"
        best_section = current_section
        for block in blocks:
            first_line = block.splitlines()[0]
            if first_line.startswith("#"):
                current_section = first_line.lstrip("# ")
            lower = block.lower()
            score = sum(lower.count(token) for token in query_tokens)
            if score > best_score:
                best_score = score
                best_block = block
                best_section = current_section
        return best_block[:900], best_section


def _summarize_tool_output(output: Any) -> str:
    if isinstance(output, list):
        return f"Returned {len(output)} items"
    if isinstance(output, dict):
        keys = ", ".join(list(output.keys())[:6])
        return f"Returned object with keys: {keys}"
    if isinstance(output, str):
        return f"Returned {len(output)} characters"
    return f"Returned {type(output).__name__}"


def _read_contract(payload: ReadContractInput, allowed_roots: tuple[Path, ...]) -> dict[str, Any]:
    if payload.contract_text and payload.contract_text.strip():
        text = payload.contract_text.strip()
        source = "inline_text"
    elif payload.contract_path:
        path = Path(payload.contract_path).expanduser().resolve()
        if not any(path == root or path.is_relative_to(root) for root in allowed_roots):
            allowed = ", ".join(str(root) for root in allowed_roots)
            raise ToolExecutionError(f"Contract path is outside allowed roots: {allowed}")
        if not path.exists() or not path.is_file():
            raise ToolExecutionError(f"Contract file does not exist: {path}")
        if path.stat().st_size > 10_000_000:
            raise ToolExecutionError("Contract file exceeds the 10 MB safety limit")
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif suffix in {".txt", ".md"}:
            text = path.read_text(encoding="utf-8")
        else:
            raise ToolExecutionError(f"Unsupported contract format: {suffix}")
        source = str(path)
    else:
        raise ToolExecutionError("Either contract_path or contract_text is required")

    text = text[: payload.max_chars]
    if len(text.strip()) < 20:
        raise ToolExecutionError("The extracted contract text is empty or too short")
    return {"source": source, "text": text, "characters": len(text)}


def _topic_for_clause(text: str) -> str:
    lowered = text.lower()
    # Headings are stronger signals than body keywords. Prioritizing them avoids
    # a liability clause being misclassified merely because its carve-outs mention
    # privacy and security.
    heading_signals = (
        ("data_protection", ("data protection", "privacy", "data location", "breach notification")),
        ("security", ("information security", "cybersecurity", "security controls")),
        ("payment", ("payment", "fees", "invoicing")),
        ("liability", ("liability", "indemnity")),
        ("termination", ("termination", "term and termination", "renewal")),
        ("governing_law", ("governing law", "jurisdiction")),
        ("service_levels", ("service level", "sla", "availability")),
    )
    heading = lowered.split("\n", 1)[0][:120]
    for topic, signals in heading_signals:
        if any(signal in heading for signal in signals):
            return topic

    topic_keywords = {
        "data_protection": ["data", "privacy", "personal information", "residency", "subprocessor", "breach"],
        "security": ["security", "encryption", "iso 27001", "penetration", "access control"],
        "payment": ["payment", "invoice", "fees", "sar", "price"],
        "liability": ["liability", "indemnity", "damages", "cap"],
        "termination": ["terminate", "termination", "renewal", "notice"],
        "governing_law": ["governing law", "jurisdiction", "kingdom of saudi arabia", "ksa"],
        "service_levels": ["sla", "availability", "uptime", "service level"],
    }
    scores = {topic: sum(keyword in lowered for keyword in keywords) for topic, keywords in topic_keywords.items()}
    topic, score = max(scores.items(), key=lambda item: item[1])
    return topic if score else "general"


def _extract_clauses(payload: ExtractClausesInput) -> list[dict[str, Any]]:
    text = payload.contract_text.replace("\r\n", "\n")
    lines = [line.strip() for line in text.splitlines()]
    sections: list[tuple[str, list[str]]] = []
    current_heading = "Preamble"
    current_lines: list[str] = []
    heading_pattern = re.compile(r"^(?:\d+(?:\.\d+)*[.)]?|[A-Z][A-Z\s/&-]{3,}:?)\s+(.+)$")

    for line in lines:
        if not line:
            continue
        is_heading = bool(re.match(r"^\d+(?:\.\d+)*[.)]?\s+", line)) or (
            len(line) < 90 and line.endswith(":")
        )
        if is_heading and current_lines:
            sections.append((current_heading, current_lines))
            current_heading = line.rstrip(":")
            current_lines = []
        elif is_heading:
            current_heading = line.rstrip(":")
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_heading, current_lines))

    if not sections:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        sections = [(f"Clause {index}", [paragraph]) for index, paragraph in enumerate(paragraphs, 1)]

    clauses: list[dict[str, Any]] = []
    for index, (heading, section_lines) in enumerate(sections, 1):
        clause_text = " ".join(section_lines).strip()
        if not clause_text:
            continue
        clauses.append(
            {
                "clause_id": f"C-{index:02d}",
                "heading": heading,
                "text": clause_text,
                "topic": _topic_for_clause(f"{heading}\n{clause_text}"),
            }
        )
    return clauses


def _calculate_risk(payload: CalculateRiskInput) -> dict[str, Any]:
    severity_points = {"critical": 25, "high": 15, "medium": 8, "low": 3, "info": 0}
    score = sum(severity_points.get(str(item.get("severity", "info")).lower(), 0) for item in payload.findings)
    if payload.contract_value_sar >= 1_000_000:
        score += 15
    elif payload.contract_value_sar >= payload.approval_value_threshold_sar:
        score += 8
    score = min(score, 100)
    if score >= 80:
        level = "CRITICAL"
    elif score >= 50:
        level = "HIGH"
    elif score >= 25:
        level = "MEDIUM"
    else:
        level = "LOW"
    approval_required = (
        score >= payload.approval_risk_threshold
        or payload.contract_value_sar >= payload.approval_value_threshold_sar
    )
    return {"risk_score": score, "risk_level": level, "approval_required": approval_required}


def _mask_pii_tool(payload: MaskPIIInput) -> dict[str, Any]:
    masked, count, categories = mask_pii(payload.text)
    return {"masked_text": masked, "redactions": count, "categories": categories}


class ArtifactStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def store(self, payload: StoreArtifactInput) -> dict[str, Any]:
        object_name = f"{payload.thread_id}/compliance_report.md"
        metadata_name = f"{payload.thread_id}/run_metadata.json"
        if self.settings.minio_endpoint:
            minio_result = self._store_minio(payload, object_name, metadata_name)
            if minio_result is not None:
                return minio_result

        thread_dir = self.settings.artifact_dir / payload.thread_id
        thread_dir.mkdir(parents=True, exist_ok=True)
        report_path = thread_dir / "compliance_report.md"
        metadata_path = thread_dir / "run_metadata.json"
        report_path.write_text(payload.markdown, encoding="utf-8")
        metadata_path.write_text(json.dumps(payload.metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "uri": report_path.as_uri(),
            "metadata_uri": metadata_path.as_uri(),
            "backend": "filesystem-fallback",
        }

    def _store_minio(
        self,
        payload: StoreArtifactInput,
        object_name: str,
        metadata_name: str,
    ) -> dict[str, Any] | None:
        try:
            from minio import Minio  # type: ignore
        except ImportError:
            return None
        if not self.settings.minio_access_key or not self.settings.minio_secret_key:
            return None
        try:
            client = Minio(
                self.settings.minio_endpoint,
                access_key=self.settings.minio_access_key,
                secret_key=self.settings.minio_secret_key,
                secure=self.settings.minio_secure,
            )
            if not client.bucket_exists(self.settings.minio_bucket):
                client.make_bucket(self.settings.minio_bucket)
            report_bytes = payload.markdown.encode("utf-8")
            metadata_bytes = json.dumps(payload.metadata, ensure_ascii=False, indent=2).encode("utf-8")
            client.put_object(
                self.settings.minio_bucket,
                object_name,
                BytesIO(report_bytes),
                len(report_bytes),
                content_type="text/markdown",
            )
            client.put_object(
                self.settings.minio_bucket,
                metadata_name,
                BytesIO(metadata_bytes),
                len(metadata_bytes),
                content_type="application/json",
            )
            scheme = "https" if self.settings.minio_secure else "http"
            return {
                "uri": f"s3://{self.settings.minio_bucket}/{object_name}",
                "metadata_uri": f"s3://{self.settings.minio_bucket}/{metadata_name}",
                "endpoint": f"{scheme}://{self.settings.minio_endpoint}",
                "backend": "minio-s3",
            }
        except Exception:
            return None


def build_tool_registry(settings: Settings, observability: Observability) -> ToolRegistry:
    knowledge_base = PolicyKnowledgeBase(settings.policy_dir)
    artifact_store = ArtifactStore(settings)
    registry = ToolRegistry(observability)

    registry.register(
        FunctionTool(
            name="read_contract",
            description="Read a PDF, TXT, or Markdown contract, or use inline contract text.",
            input_model=ReadContractInput,
            handler=lambda payload: _read_contract(payload, settings.allowed_contract_roots),
        )
    )
    registry.register(
        FunctionTool(
            name="extract_contract_clauses",
            description="Split contract text into structured clauses and classify each clause topic.",
            input_model=ExtractClausesInput,
            handler=_extract_clauses,
        )
    )

    def search_handler(payload: SearchPoliciesInput) -> list[dict[str, Any]]:
        if payload.simulate_primary_failure and payload.attempt == 0:
            raise ConnectionError("Simulated primary policy-index timeout for retry-path evidence")
        return knowledge_base.search(payload.query, topic=payload.topic, top_k=payload.top_k)

    registry.register(
        FunctionTool(
            name="search_policy_knowledge_base",
            description="Search corporate policy documents with BM25 ranking and return evidence excerpts.",
            input_model=SearchPoliciesInput,
            handler=search_handler,
        )
    )
    registry.register(
        FunctionTool(
            name="calculate_contract_risk",
            description="Calculate a bounded risk score and whether human approval is required.",
            input_model=CalculateRiskInput,
            handler=_calculate_risk,
        )
    )
    registry.register(
        FunctionTool(
            name="mask_pii",
            description="Mask emails, Saudi phone numbers, national IDs, IBANs, and card numbers.",
            input_model=MaskPIIInput,
            handler=_mask_pii_tool,
        )
    )
    registry.register(
        FunctionTool(
            name="store_report_artifact",
            description="Store the final report in MinIO/S3 when configured, otherwise in a durable filesystem fallback.",
            input_model=StoreArtifactInput,
            handler=artifact_store.store,
        )
    )
    return registry
