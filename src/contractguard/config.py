"""Runtime configuration for ContractGuard AI."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    project_root: Path
    policy_dir: Path
    checkpoint_db: Path
    log_file: Path
    artifact_dir: Path
    metrics_file: Path
    allowed_contract_roots: tuple[Path, ...]
    max_graph_steps: int = 60
    max_policy_retries: int = 2
    max_quality_retries: int = 1
    max_report_revisions: int = 2
    approval_risk_threshold: int = 50
    approval_value_threshold_sar: float = 500_000.0
    llm_provider: str = "offline"
    llm_timeout_seconds: float = 45.0
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    openrouter_api_key: str | None = None
    openrouter_model: str = "google/gemini-2.5-flash"
    openrouter_site_url: str = "https://github.com/SDAIAAcademy"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    api_key: str | None = None
    minio_endpoint: str | None = None
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    minio_secure: bool = False
    minio_bucket: str = "contractguard-reports"

    @classmethod
    def from_env(cls, project_root: str | Path | None = None) -> "Settings":
        initial_root = Path(
            project_root or os.getenv("CONTRACTGUARD_ROOT") or Path(__file__).resolve().parents[2]
        ).resolve()
        # Local development can use an untracked .env file. Explicit process/container
        # environment variables always win because override=False.
        load_dotenv(initial_root / ".env", override=False)
        root = Path(project_root or os.getenv("CONTRACTGUARD_ROOT") or initial_root).resolve()
        evidence = root / "evidence"
        allowed_roots = cls._parse_allowed_roots(os.getenv("CONTRACT_ALLOWED_ROOTS"), root)
        return cls(
            project_root=root,
            policy_dir=Path(os.getenv("POLICY_DIR", root / "data" / "policies")).expanduser().resolve(),
            checkpoint_db=Path(os.getenv("CHECKPOINT_DB", evidence / "checkpoints.sqlite")).expanduser().resolve(),
            log_file=Path(os.getenv("LOG_FILE", evidence / "execution_log.jsonl")).expanduser().resolve(),
            artifact_dir=Path(os.getenv("ARTIFACT_DIR", evidence / "artifacts")).expanduser().resolve(),
            metrics_file=Path(os.getenv("METRICS_FILE", evidence / "metrics.prom")).expanduser().resolve(),
            allowed_contract_roots=allowed_roots,
            max_graph_steps=int(os.getenv("MAX_GRAPH_STEPS", "60")),
            max_policy_retries=int(os.getenv("MAX_POLICY_RETRIES", "2")),
            max_quality_retries=int(os.getenv("MAX_QUALITY_RETRIES", "1")),
            max_report_revisions=int(os.getenv("MAX_REPORT_REVISIONS", "2")),
            approval_risk_threshold=int(os.getenv("APPROVAL_RISK_THRESHOLD", "50")),
            approval_value_threshold_sar=float(os.getenv("APPROVAL_VALUE_THRESHOLD_SAR", "500000")),
            llm_provider=os.getenv("LLM_PROVIDER", "offline").lower().strip(),
            llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "45")),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            groq_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
            openrouter_model=os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash"),
            openrouter_site_url=os.getenv("OPENROUTER_SITE_URL", "https://github.com/SDAIAAcademy"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            api_key=os.getenv("CONTRACTGUARD_API_KEY"),
            minio_endpoint=os.getenv("MINIO_ENDPOINT"),
            minio_access_key=os.getenv("MINIO_ACCESS_KEY"),
            minio_secret_key=os.getenv("MINIO_SECRET_KEY"),
            minio_secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
            minio_bucket=os.getenv("MINIO_BUCKET", "contractguard-reports"),
        )

    @staticmethod
    def _parse_allowed_roots(raw: str | None, root: Path) -> tuple[Path, ...]:
        if not raw:
            return ((root / "data").resolve(),)
        roots = tuple(
            Path(value).expanduser().resolve()
            for value in raw.split(os.pathsep)
            if value.strip()
        )
        return roots or ((root / "data").resolve(),)

    def is_contract_path_allowed(self, path: str | Path) -> bool:
        resolved = Path(path).expanduser().resolve()
        return any(resolved == root or resolved.is_relative_to(root) for root in self.allowed_contract_roots)

    def ensure_directories(self) -> None:
        for path in (
            self.policy_dir,
            self.checkpoint_db.parent,
            self.log_file.parent,
            self.artifact_dir,
            self.metrics_file.parent,
        ):
            path.mkdir(parents=True, exist_ok=True)
