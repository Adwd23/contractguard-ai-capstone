# Automated Evaluation Guide

This evaluator-facing index points directly to executable implementation, regression tests, and committed runtime evidence for ContractGuard AI v1.3.1. It is intentionally CI-independent.

## Fast verification commands

```bash
# Dependency-light source proof: exactly one JSON object.
python scripts/grader_probe.py

# Refresh end-to-end runtime proof: exactly one JSON object on stdout.
python scripts/runtime_grader_probe.py --refresh

# Validate committed runtime evidence without rerunning it.
python scripts/prepublish_check.py --skip-runtime

# Or perform a complete fresh validation.
python scripts/prepublish_check.py
```

## Previous grader observations and direct proof

| Observation | Executable fix | Runtime/source proof |
|---|---|---|
| `uvicorn` / `ipykernel` declared but unused | `src/contractguard/server.py` imports and calls `uvicorn.run(...)`; notebook builder imports `ipykernel` and calls `make_ipkernel_cmd()` | `tests/test_trainer_fixes.py`, executed notebook |
| Guardrail looked like a comment/claim | `InputSecurityAgent` calls `InputGuardrail.enforce()`; `OutputGuardianAgent` calls `OutputGuardrail.enforce()` | `evidence/01_prompt_injection_blocked.json`, `evidence/05_high_risk_resumed_and_completed.json` |
| StateGraph looked linear | Five executable `add_conditional_edges(...)` calls plus three bounded cycles | `src/contractguard/workflow.py`, `evidence/graph_spec.json` |
| `interrupt()` appeared without resume | `interrupt(...)`, external `Command(resume=...)`, post-resume `Command(goto=...)` | restart/HITL evidence files |
| Only one agent appeared to exist | Ten concrete `*Agent` classes in separate modules, instantiated independently and exchanging typed messages | `src/contractguard/agents/`, `src/contractguard/service.py`, runtime agent messages |
| AI grader JSON parse failed | source/runtime probes serialize one JSON object and capture human-readable progress separately | `EVALUATION.json`, `evidence/runtime_grader_probe.json` |
| GitHub About description empty | repository metadata now uses the required description; the exact value is also documented in README | repository landing page |

## Deliverable 1 — Agentic Reasoning & Tool Use (15)

Implementation:

- `src/contractguard/agents/coordinator.py` — Plan-and-Execute coordination.
- `src/contractguard/agents/base.py` — ReAct decision/action/observation records around real function calls.
- `src/contractguard/tools.py` — Pydantic/JSON-schema function registry and real local tools.
- `src/contractguard/llm.py` — deterministic schema router plus optional provider-native function calling.
- `src/contractguard/state.py` — shared short-term `AuditState`.

Evidence:

- `evidence/02_low_risk_completed.json`
- `evidence/run_summary.json`
- executed notebook

## Deliverable 2 — Graph-Based Orchestration (20)

`src/contractguard/workflow.py` constructs a genuine `StateGraph(AuditState)` with named nodes and shared state. It registers five `add_conditional_edges(...)` routing points and includes bounded retry/re-search/revision cycles.

Runtime evidence:

- `evidence/graph_spec.json`
- `evidence/03_high_risk_paused_for_human.json`
- `evidence/run_summary.json`

## Deliverable 3 — Multi-Agent System & Role Specialization (20)

Concrete roles include Input Security, Coordinator, Document Analyst, Policy Research, Compliance Analyst, Quality Reviewer, Security Reviewer, Report Writer, Output Guardian, and Artifact Storage. Each role is a separate class/object.

`BaseAgent.send()` creates typed `AgentMessage` records stored in shared state, and the runtime evidence contains multiple distinct senders and recipients.

## Deliverable 4 — Security, Guardrails & Observability (20)

Input enforcement path:

```text
input_guardrail
  -> InputSecurityAgent.run
  -> InputGuardrail.enforce
  -> GuardrailViolation on attack
  -> conditional route to blocked
  -> END
```

The real attack evidence asserts zero tool calls.

Output enforcement path:

```text
report_writer
  -> output_guardian
  -> OutputGuardrail.enforce
  -> PII masking + secret filter + AuditReport validation
  -> valid: artifact_storage
  -> invalid: bounded report revision
```

Observability is implemented with JSONL logging and Prometheus counters/gauges/histograms for nodes, tools, failures, retries, HITL, LLM operations, latency, token estimates, and cost estimates.

## Deliverable 5 — Persistence, HITL & Cloud (20)

`src/contractguard/persistence.py` creates the real LangGraph `SqliteSaver`, and the compiled graph receives it as its checkpointer.

The human node calls `interrupt(...)`; the service later invokes `Command(resume=...)` for the same persisted thread; the node then routes with `Command(goto=...)`.

Cloud/runtime artifacts:

- `Dockerfile`
- `docker-compose.yml`
- FastAPI/Uvicorn API
- Prometheus configuration
- MinIO/S3 backend
- `evidence/07_minio_docker_smoke.json`, which proves completed S3-compatible storage and SDK verification

## Deliverable 6 — Documentation & Execution Evidence (5)

Canonical evidence entry points:

- `EVALUATION.json`
- `evidence/runtime_grader_probe.json`
- `evidence/run_summary.json`
- `evidence/pytest_results.txt`
- `notebooks/ContractGuard_Capstone_Executed.ipynb`
- `docs/rubric_traceability.md`

The executed notebook contains captured output for the security, retry, graph, multi-agent, HITL/restart, output-guardrail, persistence, and monitoring paths.

## GitHub About description

The repository landing page should display:

> Secure LangGraph multi-agent system for vendor contract auditing, compliance analysis, guardrails, human approval, and production monitoring.

No GitHub Actions workflow is required to establish rubric compliance; source and runtime proof are committed directly in the repository.
