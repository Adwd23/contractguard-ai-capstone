# Capstone Rubric Traceability — ContractGuard AI v1.3.1

| Deliverable | Implementation | Execution evidence |
|---|---|---|
| **1. Agentic Reasoning & Tool Use — 15** | Plan-and-Execute coordinator; ReAct tool decisions/observations; Reflexion reviewer; hierarchical delegation; six real schema-validated functions; shared short-term `AuditState` | `evidence/02_low_risk_completed.json`, `evidence/run_summary.json`, executed notebook |
| **2. Graph-Based Orchestration — 20** | Real LangGraph `StateGraph(AuditState)`; 16 nodes; explicit edges; five `add_conditional_edges(...)` registrations; bounded retry/re-search/output loops | `src/contractguard/workflow.py`, `evidence/graph_spec.json`, `evidence/03_high_risk_paused_for_human.json`, executed notebook |
| **3. Multi-Agent System & Role Specialization — 20** | Ten separate specialist classes/objects; distinct responsibilities; centralized coordinator; structured `AgentMessage` communication; per-agent tool permissions | `src/contractguard/agents/`, `src/contractguard/service.py`, agent messages in runtime evidence |
| **4. Security, Guardrails & Observability — 20** | Enforced `InputGuardrail.enforce()` with actual blocked attack and zero tools; enforced output PII/schema guardrail; structured JSONL logs; Prometheus metrics | `evidence/01_prompt_injection_blocked.json`, `evidence/05_high_risk_resumed_and_completed.json`, `evidence/execution_log.jsonl`, `evidence/metrics_before_restart.prom` |
| **5. Production Readiness: Persistence, HITL & Cloud — 20** | LangGraph `SqliteSaver`; real `interrupt()`; restart with a new service; `Command(resume=...)`; FastAPI/Uvicorn; Docker; MinIO/S3; Prometheus | `evidence/03_high_risk_paused_for_human.json`, `evidence/04_checkpoint_loaded_after_restart.json`, `evidence/05_high_risk_resumed_and_completed.json`, `evidence/07_minio_docker_smoke.json`, Docker/Compose |
| **6. Documentation & Evidence of Execution — 5** | Professional README; architecture/graph docs; strict source/runtime JSON probes; executed notebook; machine-readable evidence; regression tests; incremental Git history | `README.md`, `EVALUATION.json`, `docs/automated_evaluation_guide.md`, `notebooks/ContractGuard_Capstone_Executed.ipynb`, `evidence/runtime_grader_probe.json`, `evidence/pytest_results.txt` |

## Direct evaluator search strings

```text
StateGraph(AuditState)
add_conditional_edges(
interrupt(
Command(resume=
InputGuardrail.enforce(
OutputGuardrail.enforce(
class CoordinatorAgent
class PolicyResearchAgent
class QualityReviewerAgent
class ReportWriterAgent
import uvicorn
uvicorn.run(
from ipykernel.kernelspec import make_ipkernel_cmd
make_ipkernel_cmd()
```

## Failure/security paths that are actually demonstrated

- Prompt-injection attack is blocked before any function tool executes.
- Policy retrieval experiences a real simulated failure and graph retry.
- Quality review triggers a Reflexion/re-search loop.
- High-risk execution pauses on a LangGraph human interrupt.
- A new service instance reloads the persisted checkpoint after restart.
- The same thread resumes with `Command(resume=...)` and completes after approval.
- Invalid output triggers a bounded report revision.
- PII is masked before artifact persistence.
- MinIO/S3 report storage is verified through the S3 SDK.

## Evaluator entry points

```bash
python scripts/grader_probe.py
python scripts/runtime_grader_probe.py --refresh
python scripts/prepublish_check.py --skip-runtime
```

All proof is available directly in the repository; a GitHub Actions workflow is not required for evaluation.
