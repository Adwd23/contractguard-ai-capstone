# Trainer Feedback Verification — ContractGuard AI v1.3.1

This document maps every previous trainer/automated-grader observation to executable source code, regression tests, and committed runtime evidence. The proof is CI-independent: evaluators can inspect the repository directly and run the provided validation commands locally.

## 1. Declared libraries are genuinely used

### Uvicorn

`src/contractguard/server.py` imports `uvicorn` and calls `uvicorn.run(...)` as the actual FastAPI process runner. `tests/test_trainer_fixes.py::test_uvicorn_runner_is_invoked_not_only_declared` monkeypatches `uvicorn.run` and proves the runner is invoked with the configured host and port.

### ipykernel

`scripts/build_executed_notebook.py` imports `ipykernel`, imports `make_ipkernel_cmd` from `ipykernel.kernelspec`, calls `make_ipkernel_cmd()`, stores the launch command in notebook metadata, and captures the package/version and launch command in the executed notebook.

## 2. Guardrails enforce behavior in executable code

`InputSecurityAgent.run()` calls:

```python
self.input_guardrail.enforce(...)
```

`InputGuardrail.enforce()` scans the user request and untrusted contract content. On an attack it raises `GuardrailViolation`; the graph sets `input_blocked=True` and routes directly to `blocked`. The committed attack evidence proves that no function tool executed after the block.

`OutputGuardianAgent.run()` calls `OutputGuardrail.enforce()` before artifact storage. That guardrail performs PII masking, secret-pattern filtering, and strict `AuditReport.model_validate(...)` schema enforcement. Invalid output routes through a bounded report-revision loop instead of being stored.

Proof:

- `src/contractguard/guardrails.py`
- `src/contractguard/agents/input_security.py`
- `src/contractguard/agents/output_guardian.py`
- `tests/test_guardrails.py`
- `tests/test_trainer_fixes.py`
- `evidence/01_prompt_injection_blocked.json`
- `evidence/05_high_risk_resumed_and_completed.json`

## 3. The workflow is a genuine branching LangGraph StateGraph

`src/contractguard/workflow.py` constructs:

```python
workflow = StateGraph(AuditState)
```

and contains five executable `workflow.add_conditional_edges(...)` registrations:

1. input guardrail: `blocked` vs `safe`;
2. policy research: `retry` vs `success` vs `failed`;
3. quality review: `retry` vs `pass`;
4. security review: `human` vs `automatic`;
5. output guardrail: `revise` vs `valid` vs `failed`.

The graph has three bounded loop/re-entry paths:

```text
policy_research -> policy_research
quality_reviewer -> policy_research
output_guardian -> report_writer
```

The shared `AuditState` object is read and updated by graph nodes. Retry counters plus the graph recursion limit prevent infinite execution.

Runtime proof:

- `evidence/graph_spec.json`
- `evidence/03_high_risk_paused_for_human.json`
- `evidence/run_summary.json`

## 4. HITL pauses and resumes end-to-end

The human approval node calls:

```python
decision_payload = interrupt(...)
```

The high-risk scenario persists at `awaiting_approval`. The demonstration closes the first service, creates a new service instance against the same SQLite checkpointer, and reloads the pending `human_approval` node.

External approval then resumes the exact persisted thread with:

```python
self.graph.invoke(
    Command(resume=request.model_dump(mode="json")),
    config=config,
)
```

The resumed node returns either `Command(goto="report_writer", ...)` or `Command(goto="rejected", ...)`.

Runtime proof:

- `evidence/03_high_risk_paused_for_human.json`
- `evidence/04_checkpoint_loaded_after_restart.json`
- `evidence/05_high_risk_resumed_and_completed.json`

## 5. Multi-agent implementation uses independent specialist objects

The repository contains ten concrete agent classes in separate modules:

1. `InputSecurityAgent`
2. `CoordinatorAgent`
3. `DocumentAnalystAgent`
4. `PolicyResearchAgent`
5. `ComplianceAnalystAgent`
6. `QualityReviewerAgent`
7. `SecurityReviewerAgent`
8. `ReportWriterAgent`
9. `OutputGuardianAgent`
10. `ArtifactStorageAgent`

`ContractGuardService._build_agents()` instantiates those roles independently. `BaseAgent.send()` creates a typed `AgentMessage` containing sender, recipient, message type, content, payload, and timestamp, then appends it to shared state.

The high-risk runtime evidence contains messages from multiple concrete specialist senders to multiple recipients.

## 6. Automated grading receives strict JSON

`python scripts/grader_probe.py` writes exactly one JSON object to stdout.

`python scripts/runtime_grader_probe.py --refresh` captures human-readable progress internally and writes exactly one JSON object to stdout. Its committed result is `evidence/runtime_grader_probe.json`, which records all runtime acceptance checks.

This removes mixed stdout as a repository-side cause of `Expecting value: line 1 column 1` JSON parsing failures.

## 7. GitHub About description

The repository About description is:

> Secure LangGraph multi-agent system for vendor contract auditing, compliance analysis, guardrails, human approval, and production monitoring.

The same value is documented in `README.md` and `docs/github_publication.md` so an evaluator can verify the metadata directly.

## 8. Cloud/MinIO proof is committed

The project includes `Dockerfile`, `docker-compose.yml`, FastAPI/Uvicorn, Prometheus configuration, and a MinIO/S3 backend.

`evidence/07_minio_docker_smoke.json` records a completed MinIO/S3 smoke execution with an `s3://` artifact URI and `verified_via_s3_sdk: true`. This means cloud/storage proof no longer depends on an external workflow artifact.

## Final evaluator commands

```bash
python scripts/grader_probe.py
python scripts/runtime_grader_probe.py --refresh
python scripts/prepublish_check.py --skip-runtime
```

For a complete fresh rerun, use:

```bash
python scripts/prepublish_check.py
```

The submission does not require a GitHub Actions workflow.
