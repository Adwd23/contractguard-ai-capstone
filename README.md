# ContractGuard AI

**v1.3 Trainer-Fix Edition** — a secure, observable, resumable multi-agent system for vendor-contract auditing and compliance review.

**Repository owner / project implementer:** Adwd23
**Training program:** SDAIA Academy — *Advanced Agentic AI Systems Engineering*
**Cohort/session:** June 2026
**SDAIA Academy GitHub:** https://github.com/SDAIAAcademy

> GitHub About description to use: **Secure LangGraph multi-agent system for vendor contract auditing, compliance analysis, guardrails, human approval, and production monitoring.**

## What the system does

ContractGuard AI receives a vendor contract, blocks prompt-injection attempts before any tool can run, extracts clauses, retrieves internal policy evidence, evaluates compliance, scores risk, pauses for a human decision when the contract is high risk, validates and redacts the final report, and stores the approved artifact. The workflow is implemented as a genuine `langgraph.graph.StateGraph` with durable SQLite checkpoints.

The project intentionally demonstrates both the happy path and the failure/security paths required by the capstone rubric: a blocked indirect prompt injection, a real tool retry, a Reflexion re-search loop, a persistent Human-in-the-Loop interrupt that survives process restart, `Command(resume=...)`, output-schema regeneration, PII masking, structured logs, Prometheus metrics, Docker, MinIO/S3, FastAPI, and executed evidence.

## v1.3 trainer-feedback fixes

This edition was rebuilt so the requirements are visible in executable code rather than only in documentation.

| Trainer observation | v1.3 implementation | Primary proof |
|---|---|---|
| `uvicorn` and `ipykernel` were declared but not visibly used | `uvicorn` is imported and invoked in the API launcher; `ipykernel` is imported and printed by the notebook evidence builder | `src/contractguard/server.py`, `scripts/build_executed_notebook.py`, `tests/test_trainer_fixes.py` |
| Guardrail wording looked like a comment/claim | `InputGuardrail.enforce()` raises `GuardrailViolation` and is called before any tool-capable node; `OutputGuardrail.enforce()` masks/validates before storage | `src/contractguard/guardrails.py`, `src/contractguard/agents/input_security.py`, `src/contractguard/agents/output_guardian.py` |
| State graph appeared linear | The workflow contains five explicit `add_conditional_edges(...)` calls plus three bounded cycles | `src/contractguard/workflow.py`, `/graph`, `evidence/graph_spec.json` |
| `interrupt()` appeared without a demonstrated resume | The approval node calls `interrupt(...)`; the external resume path calls `graph.invoke(Command(resume=...))`; the node returns `Command(goto=...)` | `src/contractguard/workflow.py`, restart/HITL evidence files |
| Multiple roles looked like one agent role-playing personas | Each specialist is a separate Python class in its own module, with its own responsibility and tool allow-list | `src/contractguard/agents/` and structured `AgentMessage` records |
| GitHub About description was empty | The exact description is documented in this README and `docs/github_publication.md` | GitHub repository About panel after publication |
| Grader JSON confidence failure | All generated evidence JSON is parsed by the pre-publication gate and the CI workflow fails on invalid JSON | `scripts/prepublish_check.py` |

See [`docs/trainer_feedback_fixes.md`](docs/trainer_feedback_fixes.md) for the evaluator-oriented checklist.

## Architecture

### Real graph orchestration

The workflow is built with:

```python
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

workflow = StateGraph(AuditState)
```

The graph contains 16 named nodes and explicit branches. Five calls to `add_conditional_edges(...)` implement:

1. safe input vs. blocked input;
2. policy-search success vs. bounded retry vs. terminal failure;
3. quality pass vs. Reflexion/re-search;
4. automatic continuation vs. human approval;
5. valid output vs. bounded report revision vs. terminal failure.

Three cycles are deliberate and bounded:

```text
policy_research -> policy_research      # failed tool retry
quality_reviewer -> policy_research     # Reflexion / targeted re-search
output_guardian -> report_writer        # schema/output revision
```

The shared state is `AuditState`, a typed object read and updated by graph nodes. The compiled graph receives the real LangGraph SQLite checkpointer:

```python
graph = workflow.compile(checkpointer=sqlite_persistence.saver)
```

### Human-in-the-Loop

High-risk contracts route to `approval_gate -> human_approval`. The approval node pauses with:

```python
decision_payload = interrupt(state["interrupt_payload"])
```

A different service process can reopen the SQLite checkpoint database and resume the same thread with:

```python
graph.invoke(Command(resume={"decision": "approve", ...}), config=config)
```

The approval node then uses `Command(goto="report_writer")` or `Command(goto="rejected")`.

### Multi-agent team

ContractGuard AI uses centralized coordination with independent specialist classes:

- **Input Security Agent** — enforces the prompt-injection boundary before tools.
- **Coordinator Agent** — Plan-and-Execute decomposition and handoff tracking.
- **Document Analyst Agent** — reads the contract and extracts clauses.
- **Policy Research Agent** — retrieves policy evidence through schema-described functions.
- **Compliance Analyst Agent** — compares clauses with policy evidence.
- **Quality Reviewer Agent** — Reflexion/self-critique and re-search decisions.
- **Security Reviewer Agent** — calculates risk and decides whether HITL is required.
- **Report Writer Agent** — creates the structured compliance report.
- **Output Guardian Agent** — validates schema and masks PII.
- **Artifact Storage Agent** — persists the final report to filesystem or MinIO/S3.

Each agent is instantiated separately. Agents communicate through structured `AgentMessage` objects stored in the shared state. Tool-capable agents have explicit least-privilege allow-lists.

### Agentic reasoning and tools

The system names and implements course patterns:

- **Plan-and-Execute** — the Coordinator creates a staged plan and specialists execute it.
- **ReAct** — each function call records a decision summary/action and the returned observation.
- **Reflexion/self-critique** — the Quality Reviewer can send the graph back to policy research.
- **Hierarchical Delegation** — a central coordinator delegates work to specialist agents.

Six real local functions are registered with strict Pydantic-generated JSON schemas. The default reproducible mode uses an MCP-style JSON-schema router. Optional provider-native function calling is available for Gemini, OpenRouter, and Groq.

## Security and guardrails

### Enforced input guardrail

`InputGuardrail.enforce()` inspects the user request and untrusted contract content before the document/tool nodes are reachable. A detected injection raises `GuardrailViolation`; the graph routes directly to `blocked`. The attack evidence asserts that the number of tool calls remains zero.

### Enforced output/data protection

`OutputGuardrail.enforce()` performs:

- email, phone, Saudi national-ID, IBAN, and card masking;
- secret-like pattern blocking;
- strict `AuditReport` schema validation;
- bounded report regeneration on schema failure.

Additional controls include contract-path allow-listing, safe thread-ID validation, API-key authentication when configured, per-agent tool permissions, minimized model context, and structured security logs.

## Observability

The project records JSONL logs and Prometheus metrics instead of relying on print statements. Captured signals include:

- node starts/completions/failures and latency;
- tool calls, failures, and latency;
- LLM provider/operation status, token estimates, and latency;
- guardrail blocks;
- graph retries/replans;
- human interrupts;
- terminal workflow outcomes.

Prometheus configuration is in `deploy/prometheus.yml`; metrics are also exposed at `GET /metrics`.

## Production story

- **Persistence:** `langgraph.checkpoint.sqlite.SqliteSaver` survives service restart.
- **HITL:** real `interrupt()` + `Command(resume=...)` workflow.
- **API:** FastAPI service with optional `X-API-Key` protection.
- **Runtime:** `python -m contractguard.server` imports and calls `uvicorn.run(...)`.
- **Containerization:** `Dockerfile` and `docker-compose.yml`.
- **Object storage:** MinIO/S3-backed artifact storage with a filesystem fallback for local deterministic evidence.
- **Monitoring:** Prometheus-compatible metrics and JSONL logs.
- **CI:** GitHub Actions installs the actual dependencies, runs tests and the complete evidence demonstration, executes the notebook, validates JSON, and runs a Docker/MinIO smoke test.

## Repository layout

```text
contractguard-ai/
├── src/contractguard/
│   ├── agents/                  # independent specialist agent classes
│   ├── api.py                   # FastAPI app and endpoints
│   ├── server.py                # direct uvicorn launcher
│   ├── state.py                 # shared AuditState
│   ├── workflow.py              # StateGraph + add_conditional_edges + interrupt/Command
│   ├── persistence.py           # LangGraph SqliteSaver
│   ├── guardrails.py            # executable input/output guardrails
│   ├── tools.py                 # strict schema-described function registry
│   ├── llm.py                   # offline schema router + optional native function calling
│   └── observability.py         # JSONL logs + Prometheus metrics
├── data/
│   ├── policies/
│   └── samples/
├── docs/
├── evidence/                    # regenerated by the evidence runner/CI
├── notebooks/
├── scripts/
├── tests/
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Quick start

### 1. Prerequisites

- Python 3.11 or newer
- Git
- Docker Desktop only if you want the MinIO/container demonstration

### 2. Create an environment and install

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

### 3. Configure environment variables

```bash
cp .env.example .env
```

The default `LLM_PROVIDER=offline` requires no API key and still executes real local functions through the schema-described tool registry. To demonstrate provider-native function calling, configure exactly one optional provider in the untracked `.env` file.

Never commit `.env` or real API keys.

### 4. Run tests

```bash
pytest
```

### 5. Reproduce capstone evidence

```bash
python scripts/run_capstone_demo.py
python scripts/build_executed_notebook.py
python scripts/prepublish_check.py --skip-runtime
```

The demo fails immediately if a required security, retry, persistence, HITL, redaction, or graph assertion does not hold.

### 6. Run the API

```bash
python -m contractguard.server
```

Default address:

```text
http://127.0.0.1:8000
```

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

If `CONTRACTGUARD_API_KEY` is set, all `/audits` routes require an `X-API-Key` header.

## Docker + MinIO

```bash
docker compose up --build -d
python scripts/docker_minio_smoke.py
docker compose down -v
```

This proves that the validated report is written through the configured MinIO/S3 backend. The same smoke path runs in GitHub Actions.

## Evidence index

After a successful evidence run, the repository contains:

| Evidence | What it proves |
|---|---|
| `evidence/01_prompt_injection_blocked.json` | real attack blocked before any function tool |
| `evidence/02_low_risk_completed.json` | autonomous safe path and real tool calls |
| `evidence/03_high_risk_paused_for_human.json` | tool retry, Reflexion loop, and HITL pause |
| `evidence/04_checkpoint_loaded_after_restart.json` | persisted interrupt restored by a new service instance |
| `evidence/05_high_risk_resumed_and_completed.json` | `Command(resume=...)`, human decision, output revision, PII masking |
| `evidence/graph_spec.json` | LangGraph nodes, edges, branches, loops, APIs, checkpointer |
| `evidence/execution_log.jsonl` | structured security/tool/retry/HITL monitoring |
| `evidence/metrics_before_restart.prom` | Prometheus metrics |
| `evidence/pytest_results.txt` | automated regression results |
| `evidence/run_summary.json` | machine-readable rubric assertions |
| `notebooks/ContractGuard_Capstone_Executed.ipynb` | executed evidence notebook with captured outputs |

The complete rubric mapping is in [`docs/rubric_traceability.md`](docs/rubric_traceability.md).

## Publication checklist

Before resubmitting:

1. Publish this Git repository as `https://github.com/Adwd23/contractguard-ai-capstone`.
2. In the GitHub **About** panel, set the repository description to:
   **Secure LangGraph multi-agent system for vendor contract auditing, compliance analysis, guardrails, human approval, and production monitoring.**
3. Wait until both GitHub Actions jobs are green.
4. Confirm the executed notebook and evidence files were regenerated by the current v1.3 commit.
5. Confirm the repository is public if the trainer requires direct access.

Detailed instructions are in [`docs/github_publication.md`](docs/github_publication.md).

## License

Project code is released under the MIT License. See `THIRD_PARTY_NOTICES.md` for major runtime dependencies and their upstream project references.
