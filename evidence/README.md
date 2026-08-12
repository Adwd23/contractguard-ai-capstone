# Executed Evidence

This directory is intentionally committed because the capstone rubric requires captured
execution output, not code-only claims.

- JSON files are full shared-state snapshots from real graph runs.
- `execution_log.jsonl` contains structured node, tool, security, retry, checkpoint,
  latency, and HITL events.
- `metrics_before_restart.prom` and `metrics_after_restart.prom` are Prometheus snapshots.
- `artifacts/` contains the generated compliance reports.
- `checkpoints.sqlite` is generated locally and excluded from Git because the JSON
  checkpoint snapshots and ordered history are sufficient evidence without committing a
  mutable binary database.
- `run_summary.json` contains hard-asserted evaluator proof flags.
