"""Structured logging and Prometheus metrics for the agent workflow."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import time
from typing import Any, Iterator
from uuid import uuid4

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = record.msg if isinstance(record.msg, dict) else {"message": str(record.msg)}
        envelope = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            **payload,
        }
        return json.dumps(envelope, ensure_ascii=False, default=str)


class Observability:
    def __init__(self, log_file: Path):
        log_file.parent.mkdir(parents=True, exist_ok=True)
        self.log_file = log_file
        self.registry = CollectorRegistry(auto_describe=True)
        suffix = uuid4().hex
        self.logger = logging.getLogger(f"contractguard.{suffix}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(JsonLineFormatter())
        self.logger.addHandler(handler)

        self.node_runs = Counter(
            "contractguard_node_runs_total",
            "Node executions by result",
            ["node", "status"],
            registry=self.registry,
        )
        self.node_latency = Histogram(
            "contractguard_node_latency_seconds",
            "Node execution latency",
            ["node"],
            registry=self.registry,
        )
        self.tool_calls = Counter(
            "contractguard_tool_calls_total",
            "Function-tool calls by status",
            ["tool", "status"],
            registry=self.registry,
        )
        self.tool_latency = Histogram(
            "contractguard_tool_latency_seconds",
            "Function-tool latency",
            ["tool"],
            registry=self.registry,
        )
        self.llm_calls = Counter(
            "contractguard_llm_calls_total",
            "LLM calls by provider, operation, and status",
            ["provider", "operation", "status"],
            registry=self.registry,
        )
        self.llm_latency = Histogram(
            "contractguard_llm_latency_seconds",
            "LLM call latency",
            ["provider", "operation"],
            registry=self.registry,
        )
        self.guardrail_blocks = Counter(
            "contractguard_guardrail_blocks_total",
            "Blocked inputs or outputs",
            ["guardrail"],
            registry=self.registry,
        )
        self.retries = Counter(
            "contractguard_retries_total",
            "Graph retries and replans",
            ["reason"],
            registry=self.registry,
        )
        self.human_interrupts = Counter(
            "contractguard_human_interrupts_total",
            "Human approval interrupts",
            registry=self.registry,
        )
        self.workflow_runs = Counter(
            "contractguard_workflow_runs_total",
            "Workflow terminal outcomes",
            ["status"],
            registry=self.registry,
        )
        self.active_workflows = Gauge(
            "contractguard_active_workflows",
            "Currently active workflow instances",
            registry=self.registry,
        )
        self.estimated_cost = Counter(
            "contractguard_estimated_llm_cost_usd_total",
            "Estimated LLM cost in USD",
            registry=self.registry,
        )
        self.estimated_tokens = Counter(
            "contractguard_estimated_llm_tokens_total",
            "Estimated LLM tokens",
            ["direction"],
            registry=self.registry,
        )

    def log(self, event: str, *, level: str = "info", **fields: Any) -> None:
        payload = {"event": event, **fields}
        getattr(self.logger, level.lower(), self.logger.info)(payload)

    @contextmanager
    def node(self, node: str, thread_id: str) -> Iterator[None]:
        started = time.perf_counter()
        self.log("node_started", node=node, thread_id=thread_id)
        try:
            yield
        except Exception as exc:
            elapsed = time.perf_counter() - started
            self.node_runs.labels(node=node, status="error").inc()
            self.node_latency.labels(node=node).observe(elapsed)
            self.log(
                "node_failed",
                level="error",
                node=node,
                thread_id=thread_id,
                latency_ms=round(elapsed * 1000, 3),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise
        else:
            elapsed = time.perf_counter() - started
            self.node_runs.labels(node=node, status="success").inc()
            self.node_latency.labels(node=node).observe(elapsed)
            self.log(
                "node_completed",
                node=node,
                thread_id=thread_id,
                latency_ms=round(elapsed * 1000, 3),
            )

    @contextmanager
    def tool(self, tool: str, thread_id: str, call_id: str) -> Iterator[dict[str, float]]:
        started = time.perf_counter()
        timing: dict[str, float] = {}
        self.log("tool_call_started", tool=tool, thread_id=thread_id, call_id=call_id)
        try:
            yield timing
        except Exception as exc:
            elapsed = time.perf_counter() - started
            timing["latency_ms"] = elapsed * 1000
            self.tool_calls.labels(tool=tool, status="error").inc()
            self.tool_latency.labels(tool=tool).observe(elapsed)
            self.log(
                "tool_call_failed",
                level="error",
                tool=tool,
                thread_id=thread_id,
                call_id=call_id,
                latency_ms=round(elapsed * 1000, 3),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise
        else:
            elapsed = time.perf_counter() - started
            timing["latency_ms"] = elapsed * 1000
            self.tool_calls.labels(tool=tool, status="success").inc()
            self.tool_latency.labels(tool=tool).observe(elapsed)
            self.log(
                "tool_call_completed",
                tool=tool,
                thread_id=thread_id,
                call_id=call_id,
                latency_ms=round(elapsed * 1000, 3),
            )

    def record_guardrail(self, guardrail: str, thread_id: str, reason: str) -> None:
        self.guardrail_blocks.labels(guardrail=guardrail).inc()
        self.log("guardrail_blocked", guardrail=guardrail, thread_id=thread_id, reason=reason)

    def record_retry(self, reason: str, thread_id: str, attempt: int) -> None:
        self.retries.labels(reason=reason).inc()
        self.log("workflow_retry", reason=reason, thread_id=thread_id, attempt=attempt)

    def record_interrupt(self, thread_id: str, payload: dict[str, Any]) -> None:
        self.human_interrupts.inc()
        self.log("human_interrupt", thread_id=thread_id, payload=payload)

    def record_terminal(self, thread_id: str, status: str) -> None:
        self.workflow_runs.labels(status=status).inc()
        self.log("workflow_terminal", thread_id=thread_id, status=status)

    def record_llm_call(
        self,
        *,
        provider: str,
        model: str,
        operation: str,
        status: str,
        latency_seconds: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
    ) -> None:
        self.llm_calls.labels(provider=provider, operation=operation, status=status).inc()
        self.llm_latency.labels(provider=provider, operation=operation).observe(max(latency_seconds, 0.0))
        self.record_llm_usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )
        self.log(
            "llm_call",
            provider=provider,
            model=model,
            operation=operation,
            status=status,
            latency_ms=round(max(latency_seconds, 0.0) * 1000, 3),
            input_tokens=max(input_tokens, 0),
            output_tokens=max(output_tokens, 0),
            estimated_cost_usd=max(estimated_cost_usd, 0.0),
        )

    def record_llm_usage(self, *, input_tokens: int, output_tokens: int, estimated_cost_usd: float) -> None:
        self.estimated_tokens.labels(direction="input").inc(max(input_tokens, 0))
        self.estimated_tokens.labels(direction="output").inc(max(output_tokens, 0))
        self.estimated_cost.inc(max(estimated_cost_usd, 0.0))

    def export_metrics(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(generate_latest(self.registry))
        self.log("metrics_exported", path=str(path))

    def metrics_bytes(self) -> bytes:
        return generate_latest(self.registry)

    def close(self) -> None:
        for handler in list(self.logger.handlers):
            handler.flush()
            handler.close()
            self.logger.removeHandler(handler)
