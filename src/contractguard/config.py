"""Runtime configuration for ContractGuard AI."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(slots=True)
class Settings:
    project_root: Path
    policy_dir: Path
    checkpoint_db: Path
    log_file: Path
    artifact_dir: Path
    metrics_file: Path
    max_graph_steps: int = 60
    max_policy_retries: int = 2
    max_quality_retries: int = 1
    max_report_revisions: int = 2
    approval_risk_threshold: int = 50
    approval_value_threshold_sar: float = 500_000.0
    llm_provider: str = "offline"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    minio_endpoint: str | None = None
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    minio_secure: bool = False
    minio_bucket: str = "contractguard-reports"

    @classmethod
    def from_env(cls, project_root: str | Path | None = None) -> "Settings":
        root = Path(project_root or os.getenv("CONTRACTGUARD_ROOT") or Path(__file__).resolve().parents[2]).resolve()
        evidence = root / "evidence"
        return cls(
            project_root=root,
            policy_dir=Path(os.getenv("POLICY_DIR", root / "data" / "policies")),
            checkpoint_db=Path(os.getenv("CHECKPOINT_DB", evidence / "checkpoints.sqlite")),
            log_file=Path(os.getenv("LOG_FILE", evidence / "execution_log.jsonl")),
            artifact_dir=Path(os.getenv("ARTIFACT_DIR", evidence / "artifacts")),
            metrics_file=Path(os.getenv("METRICS_FILE", evidence / "metrics.prom")),
            max_graph_steps=int(os.getenv("MAX_GRAPH_STEPS", "60")),
            max_policy_retries=int(os.getenv("MAX_POLICY_RETRIES", "2")),
            max_quality_retries=int(os.getenv("MAX_QUALITY_RETRIES", "1")),
            max_report_revisions=int(os.getenv("MAX_REPORT_REVISIONS", "2")),
            approval_risk_threshold=int(os.getenv("APPROVAL_RISK_THRESHOLD", "50")),
            approval_value_threshold_sar=float(os.getenv("APPROVAL_VALUE_THRESHOLD_SAR", "500000")),
            llm_provider=os.getenv("LLM_PROVIDER", "offline").lower(),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            groq_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            minio_endpoint=os.getenv("MINIO_ENDPOINT"),
            minio_access_key=os.getenv("MINIO_ACCESS_KEY"),
            minio_secret_key=os.getenv("MINIO_SECRET_KEY"),
            minio_secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
            minio_bucket=os.getenv("MINIO_BUCKET", "contractguard-reports"),
        )

    def ensure_directories(self) -> None:
        for path in (
            self.policy_dir,
            self.checkpoint_db.parent,
            self.log_file.parent,
            self.artifact_dir,
            self.metrics_file.parent,
        ):
            path.mkdir(parents=True, exist_ok=True)
