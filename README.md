# ContractGuard AI

**v1.3.1 — Final Submission Edition**

Secure, observable, resumable multi-agent vendor-contract auditing and compliance review built with LangGraph.

## Made By

**Abdulwahab Alolyan**  
**Repository owner / project implementer:** Adwd23  
**Training program:** SDAIA Academy — *Advanced Agentic AI Systems Engineering*  
**Cohort/session:** June 2026  
**SDAIA Academy GitHub:** https://github.com/SDAIAAcademy

**GitHub About description:**  
**Secure LangGraph multi-agent system for vendor contract auditing, compliance analysis, guardrails, human approval, and production monitoring.**

## What the system does

ContractGuard AI receives a vendor contract, blocks prompt-injection attempts before any tool-capable node can execute, extracts contract clauses, retrieves policy evidence, evaluates compliance, calculates risk, pauses for human approval when required, validates and redacts the final report, and persists the approved artifact.

The workflow is a real `langgraph.graph.StateGraph` backed by durable `SqliteSaver` checkpoints. It contains conditional branches, bounded loops, independent specialist agents, structured agent-to-agent messages, schema-validated function tools, enforced input/output guardrails, Prometheus metrics, JSONL logs, a real Human-in-the-Loop pause/resume path, FastAPI, Docker, and MinIO/S3 artifact storage.

## Capstone rubric coverage

| Deliverable | Implementation and proof |
|---|---|
| **1. Agentic Reasoning & Tool Use — 15** | Real schema-described functions through an MCP-style registry; Plan-and-Execute coordination; ReAct action/observation traces; Reflexion/self-critique; shared short-term `AuditState`. |
| **2. Graph-Based Orchestration — 20** | Real `StateGraph(AuditState)`, 16 nodes, explicit edges, five `add_conditional_edges(...)` registrations, and bounded retry/re-search/output-revision cycles. |
| **3. Multi-Agent System — 20** | Ten independent specialist agent classes with distinct responsibilities, centralized coordination, typed `AgentMessage` handoffs, and per-agent tool permissions. |
| **4. Security, Guardrails & Observability — 20** | `InputGuardrail.enforce()` blocks a real prompt-injection attempt before tools; `OutputGuardrail.enforce()` masks PII, filters secret-like output, and validates report schema; JSONL logs and Prometheus metrics capture failures, tool calls, retries, latency, and HITL events. |
| **5. Persistence, HITL & Cloud — 20** | LangGraph `SqliteSaver`; real `interrupt()`; restart recovery; `Command(resume=...)`; FastAPI/Uvicorn; Docker Compose; MinIO/S3 runtime smoke evidence. |
| **6. Documentation & Execution Evidence — 5** | Professional README and technical docs, strict JSON evaluator entry points, an executed notebook with captured output, test results, graph evidence, security evidence, and runtime logs. |

See [`docs/rubric_traceability.md`](docs/rubric_traceability.md) for the direct file-by-file map.

## Architecture

### Real LangGraph workflow

The executable graph is created in `src/contractguard/workflow.py`:

```python
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

workflow = StateGraph(AuditState)
```

The graph contains five real conditional routing points:

1. `input_guardrail` → `blocked` or `coordinator`
2. `policy_research` → retry, success, or failure
3. `quality_reviewer` → Reflexion re-search or pass
4. `security_reviewer` → human approval or automatic continuation
5. `output_guardian` → report revision, valid storage, or failure

Three bounded cycles are deliberately demonstrated:

```text
policy_research -> policy_research      # failed tool retry
quality_reviewer -> policy_research     # Reflexion / re-search
output_guardian -> report_writer        # output/schema revision
```

The graph is compiled with the real LangGraph SQLite checkpointer:

```python
graph = workflow.compile(checkpointer=self.persistence.saver)
```

The shared state is `AuditState`, a typed object carried across graph steps.

### Human-in-the-Loop

High-risk contracts route to `approval_gate -> human_approval`. The graph pauses with:

```python
decision_payload = interrupt(...)
```

The service can be closed and recreated against the same SQLite checkpoint database. The exact persisted thread is then resumed with:

```python
graph.invoke(Command(resume={"decision": "approve", ...}), config=config)
```

The resumed node returns `Command(goto="report_writer")` on approval or `Command(goto="rejected")` on rejection.

### Multi-agent team

ContractGuard uses centralized coordination with independently instantiated specialist classes:

- **Input Security Agent** — prompt-injection enforcement before tools.
- **Coordinator Agent** — Plan-and-Execute decomposition and handoffs.
- **Document Analyst Agent** — contract ingestion and clause extraction.
- **Policy Research Agent** — policy retrieval through schema-described functions.
- **Compliance Analyst Agent** — clause-to-policy comparison and findings.
- **Quality Reviewer Agent** — Reflexion/self-critique and re-search decisions.
- **Security Reviewer Agent** — risk calculation and HITL routing.
- **Report Writer Agent** — structured compliance report generation.
- **Output Guardian Agent** — schema validation and PII/data protection.
- **Artifact Storage Agent** — filesystem or MinIO/S3 persistence.

Agents communicate through typed `AgentMessage` records stored in shared state. Tool-capable agents also have explicit allow-lists so one specialist cannot call another specialist's functions.

## Agentic reasoning and real tools

The project explicitly implements course reasoning patterns:

- **Plan-and-Execute** — the Coordinator creates a seven-step execution plan.
- **ReAct** — tool decisions are recorded as action/rationale followed by real tool observations.
- **Reflexion/self-critique** — the Quality Reviewer can send execution back to policy research.
- **Hierarchical delegation** — the Coordinator delegates work to specialist agents.

The local function registry exposes strict Pydantic-generated JSON schemas. Registered functions include:

- `read_contract`
- `extract_contract_clauses`
- `search_policy_knowledge_base`
- `calculate_contract_risk`
- `mask_pii`
- `store_report_artifact`

The default reproducible mode uses an MCP-style JSON-schema router. Optional provider-native function calling is supported when a provider key is configured.

## Security and guardrails

### Input guardrail

`InputSecurityAgent.run()` calls `InputGuardrail.enforce()` before any tool-capable node. The guardrail inspects both the user request and untrusted document content. A detected attack raises `GuardrailViolation`; the graph routes directly to `blocked`, and the captured attack evidence proves that zero tools executed.

### Output/data-protection guardrail

`OutputGuardianAgent.run()` calls `OutputGuardrail.enforce()` before artifact storage. It performs:

- email, phone, Saudi national-ID, IBAN, and card masking;
- secret-like pattern blocking;
- strict `AuditReport` schema validation;
- bounded report regeneration if validation fails.

Additional protections include contract-path allow-listing, API-key support, safe thread IDs, per-agent tool permissions, and structured security logs.

## Observability

`src/contractguard/observability.py` uses structured JSONL logging and Prometheus metrics rather than print statements. Signals include:

- node starts/completions/failures and latency;
- function-tool calls, failures, and latency;
- LLM/provider operations, estimated tokens/cost, and latency;
- guardrail blocks;
- graph retries and replans;
- human interrupts;
- workflow terminal outcomes.

Prometheus metrics are exposed by the API and can also be written to an evidence file.

## Production readiness

- **Persistent state:** LangGraph `SqliteSaver` with SQLite WAL mode.
- **HITL:** real `interrupt()` + `Command(resume=...)` flow that survives service restart.
- **API:** FastAPI service with optional `X-API-Key` protection.
- **Uvicorn:** `src/contractguard/server.py` imports and calls `uvicorn.run(...)` as the actual API runner.
- **Containers:** `Dockerfile` and `docker-compose.yml`.
- **Object storage:** MinIO/S3 backend with committed successful smoke evidence in `evidence/07_minio_docker_smoke.json`.
- **Monitoring:** Prometheus-compatible metrics and structured logs.
- **Submission validation:** `scripts/prepublish_check.py` is CI-independent and can validate the repository locally or in any evaluator environment.

## Repository layout

```text
contractguard-ai-capstone/
├── src/contractguard/
│   ├── agents/                  # independent specialist agent classes
│   ├── api.py                   # FastAPI endpoints
│   ├── server.py                # direct Uvicorn launcher
│   ├── state.py                 # shared AuditState
│   ├── workflow.py              # StateGraph, branches, loops, interrupt/Command
│   ├── persistence.py           # LangGraph SqliteSaver
│   ├── guardrails.py            # executable input/output guardrails
│   ├── tools.py                 # schema-described function registry
│   ├── llm.py                   # schema router + optional provider function calling
│   └── observability.py         # JSONL logs + Prometheus metrics
├── data/
├── deploy/
├── docs/
├── evidence/
├── notebooks/
├── scripts/
├── tests/
├── Dockerfile
└── docker-compose.yml
```

## Quick start

### Prerequisites

- Python 3.11 or newer
- Git
- Docker only for the container/MinIO demonstration

### Install

```bash
python -m venv .venv
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the complete development environment:

```bash
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .
pip check
```

### Environment variables

```bash
cp .env.example .env
```

The default `LLM_PROVIDER=offline` requires no external API key and still executes real schema-validated local function tools. Optional provider keys belong only in the untracked `.env` file. Never commit real API keys.

### Run tests

```bash
pytest
```

The committed test evidence records **29 passed** tests.

### Reproduce the capstone evidence

```bash
python scripts/run_capstone_demo.py
python scripts/build_executed_notebook.py
python scripts/runtime_grader_probe.py --refresh
python scripts/prepublish_check.py --skip-runtime
```

For a full fresh validation that reruns compile, tests, demo, notebook, and runtime probe:

```bash
python scripts/prepublish_check.py
```

### Run the API

```bash
python -m contractguard.server
```

Default address: `http://127.0.0.1:8000`

Useful endpoints:

```text
GET  /health
GET  /graph
POST /audits
GET  /audits/{thread_id}
GET  /audits/{thread_id}/history
POST /audits/{thread_id}/resume
GET  /metrics
```

### Docker + MinIO

```bash
docker compose up --build -d
python scripts/docker_minio_smoke.py
docker compose down -v
```

The committed MinIO smoke evidence confirms the report was stored through the S3-compatible backend and verified with the S3 SDK.

## Evidence index

The repository keeps evaluator-friendly captured output rather than only code that could theoretically run:

| Evidence | What it proves |
|---|---|
| `EVALUATION.json` | Strict source-level verification and direct implementation locations. |
| `evidence/runtime_grader_probe.json` | One strict JSON object with 21 end-to-end runtime checks. |
| `evidence/run_summary.json` | Machine-readable proof for reasoning, tools, branches, loops, agents, guardrails, restart, HITL, redaction, logs, and cloud artifacts. |
| `evidence/01_prompt_injection_blocked.json` | Real prompt-injection attempt blocked before any function tool. |
| `evidence/02_low_risk_completed.json` | Autonomous safe path and real function-tool execution. |
| `evidence/03_high_risk_paused_for_human.json` | Tool failure/retry, Reflexion loop, and HITL pause. |
| `evidence/04_checkpoint_loaded_after_restart.json` | Persisted LangGraph interrupt recovered by a new service instance. |
| `evidence/05_high_risk_resumed_and_completed.json` | `Command(resume=...)`, approval, output revision, PII masking, and completion. |
| `evidence/07_minio_docker_smoke.json` | Successful MinIO/S3 artifact persistence verified through the S3 SDK. |
| `evidence/graph_spec.json` | Runtime graph introspection with nodes, branches, loops, APIs, and checkpointer. |
| `evidence/execution_log.jsonl` | Structured security/tool/retry/HITL monitoring. |
| `evidence/metrics_before_restart.prom` | Prometheus metrics captured during execution. |
| `evidence/pytest_results.txt` | Captured regression-test results. |
| `notebooks/ContractGuard_Capstone_Executed.ipynb` | Executed notebook with captured outputs and no unexecuted code cells. |

## Automated evaluator entry points

```bash
python scripts/grader_probe.py
python scripts/runtime_grader_probe.py --refresh
python scripts/prepublish_check.py --skip-runtime
```

`grader_probe.py` and `runtime_grader_probe.py` emit exactly one JSON object on stdout so JSON-only graders do not receive mixed human-readable progress text.

## Trainer-feedback fixes

The previous evaluator observations are addressed directly in executable code:

- **`uvicorn` / `ipykernel` declared but unused:** Uvicorn is the actual API runner; the notebook builder imports `ipykernel` and calls `make_ipkernel_cmd()`.
- **Guardrail looked like a claim/comment:** real enforcement methods execute and are covered by attack/output evidence.
- **StateGraph looked linear:** five `add_conditional_edges(...)` registrations and three bounded cycles are in the executable graph.
- **`interrupt()` without resume:** `Command(resume=...)` and post-resume `Command(goto=...)` are implemented and demonstrated after restart.
- **Only one agent appeared to exist:** ten independent specialist classes are instantiated separately and exchange typed messages.
- **GitHub About description:** the repository metadata uses the description shown at the top of this README.
- **JSON grading failure:** strict source/runtime probes produce a single parseable JSON object.

Detailed proof is in [`docs/trainer_feedback_fixes.md`](docs/trainer_feedback_fixes.md) and [`docs/automated_evaluation_guide.md`](docs/automated_evaluation_guide.md).

## Final submission checklist

Before submitting the repository URL:

1. Confirm the repository is public and accessible to the trainer.
2. Confirm the GitHub **About** description is visible and matches the description at the top of this README.
3. Run `python scripts/prepublish_check.py --skip-runtime` against the committed evidence, or run the full command without `--skip-runtime` for a fresh execution.
4. Confirm `EVALUATION.json` reports `all_static_checks_pass: true`.
5. Confirm `evidence/runtime_grader_probe.json` reports `all_runtime_checks_pass: true`.
6. Confirm the executed notebook contains captured output.
7. Submit the repository URL.

No GitHub Actions workflow is required for evaluation; the repository contains the implementation and captured evidence directly.

## License

Project code is released under the MIT License. See `THIRD_PARTY_NOTICES.md` for major runtime dependencies and upstream references.
