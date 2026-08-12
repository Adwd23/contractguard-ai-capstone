# Capstone Rubric Traceability

| Rubric deliverable | Implementation | Executed evidence |
|---|---|---|
| 1. Agentic reasoning & tool use (15) | Plan-and-Execute coordinator; concise ReAct Thought/Action/Observation records; six strict schema-described real functions; offline MCP-style schema router; optional provider-native function calling; shared short-term state | `evidence/02_low_risk_completed.json`, `evidence/05_high_risk_resumed_and_completed.json`, notebook sections 3–5, `tests/test_llm.py` |
| 2. Graph orchestration (20) | Real `transitions.Machine` 0.9.3 finite-state framework; 16 nodes; conditional edges; shared state; retry, re-search, and revision cycles with termination controls | `evidence/graph_spec.json`, checkpoint histories, graph assertions in `evidence/run_summary.json`, notebook section 4 |
| 3. Multi-agent specialization (20) | Ten separately instantiated agent classes; centralized coordinator; typed `AgentMessage` handoffs; per-agent function allow-lists | Agent message arrays, tool permission map in `run_summary.json`, notebook section 6 |
| 4. Security, guardrails & observability (20) | Prompt-injection block; strict function schemas; path/identifier boundaries; least privilege; pre-model context minimization/PII masking; output secret/schema/PII gate; optional API key; JSONL logs; Prometheus metrics | `01_prompt_injection_blocked.json`, `execution_log.jsonl`, `metrics_before_restart.prom`, masked report, security/API/tool tests |
| 5. Persistence, HITL & cloud (20) | SQLite WAL checkpointer; durable `awaiting_approval`; resume with a new service; FastAPI, Dockerfile, hardened Compose, MinIO, Prometheus; Docker-to-MinIO CI smoke test | `03_high_risk_paused_for_human.json`, `04_checkpoint_loaded_after_restart.json`, `05_high_risk_resumed_and_completed.json`, deployment files, optional `07_minio_docker_smoke.json` CI artifact |
| 6. Documentation & execution evidence (5) | Professional README, English documentation, architecture/graph/API/security docs, executed notebook, logs, metrics, test report, pre-publication checker | `README.md`, `README.md`, `docs/`, `notebooks/ContractGuard_Capstone_Executed.ipynb`, `evidence/`, `scripts/prepublish_check.py` |

## Non-happy paths proved

1. A malicious instruction embedded in an uploaded contract is blocked before any tool call.
2. A simulated policy-index timeout creates a failed `ToolObservation` and fires a retry edge.
3. A Reflexion quality score routes the graph back to research.
4. A deliberately malformed first report fails strict output validation and is regenerated.
5. A high-risk contract pauses for human approval and resumes after a new service opens the
   same SQLite database.
6. Email, Saudi phone, and Saudi national-ID values are absent from the stored report.
7. An unauthorized agent function call is denied.
8. A contract path outside the configured roots is rejected.
9. Extra model-generated function arguments are rejected by strict schemas.
10. Unsafe thread identifiers that could traverse artifact paths are rejected by the API.
11. Optional model-summary context excludes raw contract excerpts and masks PII before a
    provider adapter can receive it.
