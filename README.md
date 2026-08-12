# ContractGuard AI

**Secure, observable, resumable multi-agent vendor-contract audit platform**

**Repository owner and project implementer:** [Adwd23](https://github.com/Adwd23)

ContractGuard AI audits vendor contracts against corporate policies. It reads PDF, TXT,
or Markdown contracts; extracts and classifies clauses; retrieves policy evidence;
produces clause-level findings; calculates risk; pauses high-risk decisions for human
approval; resumes from a durable checkpoint after restart; validates and redacts the
output; and stores the final report in MinIO/S3 or a filesystem fallback.

This repository was completed for the **SDAIA Academy — Advanced Agentic AI Systems
Engineering** five-day capstone, **June 2026 session (30 training hours)**. Program
reference: [SDAIA Academy on GitHub](https://github.com/SDAIAAcademy).

## Why this is an agentic system

The implementation combines four named course patterns:

- **Plan-and-Execute:** the Coordinator creates a seven-step typed plan.
- **ReAct:** tool decisions and observations are recorded as structured traces.
- **Reflexion/self-critique:** the Quality Reviewer can route the graph back to research.
- **Hierarchical delegation:** a central Coordinator delegates to independent specialists.

Ten separately instantiated agents exchange typed messages through one serializable
shared state. The workflow is controlled by the real `transitions.Machine` finite-state
orchestration library—not a hand-written linear `if/else` chain. It contains 16 nodes,
conditional branches, three bounded cycles, terminal outcomes, and a durable human pause.
See the [renderable graph](docs/agent_graph.md) and
[architecture document](docs/architecture.md).

## Tool use and function calling

Six real functions are exposed with names, descriptions, and Pydantic-generated JSON
Schemas. Every invocation passes through schema validation, an agent-specific allow-list,
structured logging, latency metrics, and a ReAct observation.

Tool schemas reject undeclared fields. Thread IDs and file paths are bounded to prevent
artifact/path traversal, and optional external summary generation receives no raw contract
excerpts: the minimum context is selected and PII-masked before a provider call.

The default `LLM_PROVIDER=offline` mode uses a deterministic **schema-aware MCP-style tool
router**, so the full evidence suite is reproducible without sending contract data to an
external service. For a live model-native function-call demonstration, the same interface
supports **Gemini**, **OpenRouter**, and **Groq** through environment variables. Application
code keeps path, retry, simulation, approval, and persistence arguments locked even when a
model may refine safe search arguments.

## Architecture at a glance

```text
Input Security -> Coordinator -> Document Analyst -> Policy Research
        |                               ^                 |
        +-> BLOCKED             Reflexion/re-search <--- Quality Reviewer
                                                          |
Compliance Analyst -> Security Reviewer -> [HITL approval] -> Report Writer
                                                        ^          |
                                                        +-- Output Guardian
                                                                   |
                                                            Artifact Storage
```

### Specialist agents

| Agent | Responsibility |
|---|---|
| Input Security | Blocks direct and indirect prompt injection before any function executes |
| Coordinator | Creates the plan and coordinates specialist handoffs |
| Document Analyst | Reads the contract and extracts structured clauses |
| Policy Research | Selects and invokes policy-search functions through the schema router |
| Compliance Analyst | Compares clauses with retrieved policy evidence |
| Quality Reviewer | Scores coverage and performs Reflexion/re-search |
| Security Reviewer | Calculates risk and decides whether approval is mandatory |
| Report Writer | Produces the structured report and optional LLM summary |
| Output Guardian | Enforces the strict schema, secret checks, and PII masking |
| Artifact Storage | Persists the validated report and audit metadata |

## Capstone feature map

- **Agentic reasoning and tools:** real function registry, JSON Schema, ReAct traces,
  Plan-and-Execute, short-term state, offline MCP routing, and optional live function calling.
- **Graph orchestration:** 16 framework nodes, conditional edges, shared state, retries,
  Reflexion, report revision, and bounded termination controls.
- **Multi-agent specialization:** ten named roles with typed messages and centralized
  coordination.
- **Security and observability:** attack blocking, strict tool schemas, per-agent tool
  permissions, safe thread IDs, contract-path allow-list, pre-model data minimization,
  output validation, PII masking, JSONL logs, Prometheus metrics, and optional API-key
  authentication.
- **Production readiness:** SQLite WAL checkpoints, restart recovery, real HITL pause/resume,
  FastAPI, non-root Docker image, hardened Compose service, MinIO, and Prometheus.
- **Execution evidence:** tests, JSON snapshots, checkpoint histories, logs, metrics,
  reports, graph specification, and an executed notebook.

## Repository structure

```text
src/contractguard/       Agents, graph, reasoner, tools, guardrails, persistence, API
src/contractguard/_vendor/transitions/
                         Exact MIT-licensed offline fallback for transitions 0.9.3
data/policies/           Educational corporate-policy knowledge base
data/samples/            Safe, high-risk, and prompt-injection contract samples
scripts/                 Evidence, live function-call, MinIO smoke, and publish gates
tests/                   Security, graph, persistence, function-routing, and API tests
notebooks/               Source and executed evaluator notebooks
evidence/                Captured outputs, logs, metrics, reports, and test results
docs/                    Graph, architecture, security, API, and rubric traceability
deploy/                   Prometheus configuration
SECURITY.md               Responsible disclosure and secret-handling policy
```

## Local setup

Prerequisites: Python 3.11+, Git, and optionally Docker Desktop.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .
```

Run all tests and reproduce the scored evidence:

```bash
pytest
python scripts/run_capstone_demo.py
python scripts/build_executed_notebook.py
python scripts/prepublish_check.py --skip-runtime
```

The demo deliberately proves the non-happy paths:

1. an uploaded indirect prompt injection is blocked before any tool runs;
2. a low-risk contract completes autonomously;
3. a simulated policy-index timeout fires the retry edge;
4. a quality failure fires the Reflexion/re-search edge;
5. a high-risk contract pauses at the human-approval node;
6. the service is closed and recreated from SQLite;
7. human approval resumes the same thread;
8. an intentionally malformed first report fires the schema-revision loop;
9. email, phone, and Saudi national ID values are masked before storage.

Open `notebooks/ContractGuard_Capstone_Executed.ipynb` for captured output and
`evidence/run_summary.json` for evaluator-friendly proof flags.

## Optional live LLM function calling

Copy the environment template and enable one provider. Never commit the real key.

```bash
cp .env.example .env
```

Local commands automatically load the untracked `.env`; explicit shell/container
environment variables take precedence.

Gemini example:

```dotenv
LLM_PROVIDER=gemini
GEMINI_API_KEY=replace_me
GEMINI_MODEL=gemini-2.5-flash
```

OpenRouter example:

```dotenv
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=replace_me
OPENROUTER_MODEL=google/gemini-2.5-flash
```

Groq example:

```dotenv
LLM_PROVIDER=groq
GROQ_API_KEY=replace_me
GROQ_MODEL=openai/gpt-oss-20b
```

Run the native-call proof after exporting the selected provider variables or loading them
from the ignored `.env` file:

```bash
python scripts/run_live_function_call_demo.py
```

The script writes `evidence/06_live_llm_function_call.json` only when a real model-native
function call occurs. Live calls log provider, model, operation, success/failure, latency,
and token usage without logging the API key. Raw contract excerpts are never sent by the
summary adapter, and its minimal context is PII-masked first. Offline evidence remains the
grading-safe default because it requires no secret and makes no external model request.

## CLI examples

Start a low-risk audit:

```bash
contractguard start \
  --thread-id demo-low \
  --request "Audit this contract against all corporate policies" \
  --contract data/samples/vendor_contract_low_risk.txt
```

Start the high-risk retry/HITL scenario:

```bash
contractguard start \
  --thread-id demo-high \
  --request "Audit and enforce approval policy" \
  --contract data/samples/vendor_contract_high_risk.txt \
  --simulate-primary-failure \
  --simulate-quality-retry \
  --simulate-output-validation-failure
```

Resume the durable human interrupt:

```bash
contractguard resume demo-high approve \
  --approver "legal.manager" \
  --comment "Approved subject to redline remediation."
```

## FastAPI

```bash
uvicorn contractguard.api:app --reload
```

Use `/docs` for OpenAPI. Endpoints include health, graph, start, status, checkpoint history,
resume, and Prometheus metrics. When `CONTRACTGUARD_API_KEY` is set, all `/audits`
endpoints require the `X-API-Key` header. Contract file paths are restricted to
`CONTRACT_ALLOWED_ROOTS`. See [docs/api.md](docs/api.md).

## Docker Compose simulated cloud environment

```bash
cp .env.example .env
# Replace the sample MinIO password and optionally set CONTRACTGUARD_API_KEY.
docker compose up --build
```

Services:

- ContractGuard API: port 8000
- MinIO S3 API: port 9000; console: port 9001
- Prometheus: port 9090

The API container runs as a non-root user with a read-only root filesystem, dropped Linux
capabilities, `no-new-privileges`, a bounded temporary filesystem, persistent evidence
volume, health check, environment-only secrets, and MinIO-backed artifact storage. The
second GitHub Actions job runs `scripts/docker_minio_smoke.py`, submits a real audit, and
verifies both stored objects through the MinIO SDK.

## Evidence index

| Evidence | What it proves |
|---|---|
| `evidence/01_prompt_injection_blocked.json` | Real attack blocked with zero tool calls |
| `evidence/02_low_risk_completed.json` | Complete autonomous path and schema-routed tools |
| `evidence/03_high_risk_paused_for_human.json` | Retry, Reflexion, risk routing, and HITL pause |
| `evidence/04_checkpoint_loaded_after_restart.json` | State survived a new service process/object |
| `evidence/05_high_risk_resumed_and_completed.json` | Human resume, output revision, PII masking, artifact |
| `evidence/execution_log.jsonl` | Structured node, tool, model, failure, and security events |
| `evidence/metrics_*.prom` | Prometheus counters and latency histograms |
| `evidence/graph_spec.json` | Framework package/version, nodes, edges, branches, and loops |
| `evidence/pytest_results.txt` | Automated regression-test results |
| `evidence/06_live_llm_function_call.json` | Optional real provider-native function-call proof |
| `evidence/07_minio_docker_smoke.json` | Docker API stored and verified objects in MinIO (CI artifact) |
| executed notebook | Captured narrative and outputs for every rubric deliverable |

The exact rubric-to-evidence map is in
[docs/rubric_traceability.md](docs/rubric_traceability.md), and the course-file mapping is
in [docs/course_alignment.md](docs/course_alignment.md).

## Before pushing to GitHub

Run the full publication gate first. It recompiles the repository, reruns all tests and
scenarios, rebuilds the executed notebook, scans tracked files for likely secrets, and
validates Git/documentation/evidence readiness.

```bash
python scripts/prepublish_check.py
```

Then connect the Adwd23-owned repository:

```bash
git status
git log --oneline --decorate
git remote add origin https://github.com/Adwd23/contractguard-ai-capstone.git
git push -u origin main
```

Confirm that the README renders, the executed notebook displays outputs, both GitHub
Actions jobs pass, and no `.env`, API key, mutable SQLite database, or real personal
contract data is tracked. The detailed checklist is in
[docs/submission_checklist.md](docs/submission_checklist.md).

## Limitations

The bundled policies and contracts are educational simulations, not legal advice.
Authentication is optional for local grading and should be mandatory behind an enterprise
identity provider in a real deployment. Replace sample policies with approved sources,
add organization-specific RBAC, and complete legal/security review before processing real
contracts.

## License and third-party notices

Project code is MIT licensed. The offline fallback for `transitions` 0.9.3 retains its
upstream MIT license; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
