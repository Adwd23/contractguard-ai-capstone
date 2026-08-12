# Capstone Rubric Traceability

| Deliverable | v1.3 implementation | Execution evidence |
|---|---|---|
| 1. Agentic reasoning & tool use — 15 | Plan-and-Execute coordinator; ReAct tool decisions/observations; Reflexion reviewer; hierarchical delegation; six real schema-validated functions; shared short-term state | `evidence/02_low_risk_completed.json`, `evidence/run_summary.json`, executed notebook sections 1–3 |
| 2. Graph-based orchestration — 20 | Real LangGraph `StateGraph(AuditState)`; 16 nodes; normal edges; five explicit `add_conditional_edges(...)` calls; retry/re-search/output loops with termination conditions | `src/contractguard/workflow.py`, `evidence/graph_spec.json`, `/graph`, executed notebook sections 4–5 |
| 3. Multi-agent specialization — 20 | Separate specialist classes/modules; distinct responsibilities; centralized coordinator; structured `AgentMessage` communication; per-agent tool permissions | `src/contractguard/agents/`, agent messages in scenario evidence, executed notebook section 6 |
| 4. Security, guardrails & observability — 20 | Enforced `InputGuardrail.enforce()` and `GuardrailViolation`; real indirect attack blocked with zero tool calls; enforced output PII/schema guardrail; JSONL logs; Prometheus metrics | `01_prompt_injection_blocked.json`, `execution_log.jsonl`, `metrics_before_restart.prom`, notebook section 7 |
| 5. Persistence, HITL & cloud — 20 | LangGraph `SqliteSaver`; real `interrupt()`; restart with a new service; `Command(resume=...)`; FastAPI; direct `uvicorn.run(...)`; Docker; MinIO/S3; Prometheus | `03_high_risk_paused_for_human.json`, `04_checkpoint_loaded_after_restart.json`, `05_high_risk_resumed_and_completed.json`, Docker/Compose, CI MinIO smoke evidence |
| 6. Documentation & execution evidence — 5 | English README; architecture and graph docs; executed notebook; machine-readable evidence; trainer-fix regression tests; incremental Git history | `README.md`, `docs/`, `notebooks/ContractGuard_Capstone_Executed.ipynb`, `evidence/`, Git history |

## Evaluator search strings

The trainer can verify the main disputed requirements directly in source:

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
import ipykernel
```

`tests/test_trainer_fixes.py` is a regression gate for these exact implementation requirements.
