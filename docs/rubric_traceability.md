# Capstone Rubric Traceability

| Rubric deliverable | Implementation | Executed evidence |
|---|---|---|
| 1. Agentic reasoning & tool use (15) | Plan-and-Execute coordinator; ReAct records; six schema-described tools; state carried across nodes | `evidence/02_low_risk_completed.json`, `evidence/05_high_risk_resumed_and_completed.json`, notebook sections 3–5 |
| 2. Graph orchestration (20) | `transitions.Machine`; 16 nodes; conditional edges; shared state; retry, re-search, and revision loops | `evidence/graph_spec.json`, checkpoint histories, retry assertions in `run_summary.json` |
| 3. Multi-agent specialization (20) | Ten separately instantiated agent classes; centralized coordinator; typed `AgentMessage` handoffs | Agent message arrays in scenario evidence and notebook agent table |
| 4. Security, guardrails & observability (20) | Prompt-injection block; PII/secret/output schema gate; JSONL logs; Prometheus metrics | `01_prompt_injection_blocked.json`, `execution_log.jsonl`, `metrics_before_restart.prom`, final report redactions |
| 5. Persistence, HITL & cloud (20) | SQLite WAL checkpointer; durable `awaiting_approval`; resume after new process; FastAPI, Dockerfile, Compose, MinIO | `03_high_risk_paused_for_human.json`, `04_checkpoint_loaded_after_restart.json`, `05_high_risk_resumed_and_completed.json`, deployment files |
| 6. Documentation & execution evidence (5) | README, architecture, API, security, executed notebook, logs, test report | `README.md`, `docs/`, `notebooks/ContractGuard_Capstone_Executed.ipynb`, `evidence/` |

## Failure and non-happy paths proved

1. A real malicious prompt is blocked before any tool call.
2. A simulated policy-index timeout produces a failed tool observation and a graph retry.
3. A Reflexion quality score routes the graph back to research.
4. A deliberately malformed first report fails output schema validation and is regenerated.
5. A high-risk contract pauses for approval and resumes after a fresh service process opens the same SQLite database.
6. PII in contract excerpts is absent from the final report and replaced with redaction tokens.
