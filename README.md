# ContractGuard AI

**Secure Multi-Agent Vendor Contract Audit Platform**

ContractGuard AI is a deployable, graph-orchestrated agentic system that audits vendor
contracts against enterprise policies. It reads real PDF/TXT/Markdown inputs, retrieves
policy evidence, produces clause-level findings, calculates contract risk, blocks prompt
injection, masks PII, pauses high-risk decisions for human approval, resumes from a
persistent checkpoint after restart, and stores a validated report.

This repository was completed for the **SDAIA Academy — Advanced Agentic AI Systems
Engineering** five-day capstone, **June 2026 cohort/session (30 training hours)**. Program
reference: [SDAIA Academy on GitHub](https://github.com/SDAIAAcademy).

## Why this is agentic rather than a single prompt

The system implements four course patterns: **Plan-and-Execute**, **ReAct**,
**Reflexion/self-critique**, and **Hierarchical Delegation**. Ten independently
instantiated specialist agents communicate with typed messages through one shared state.
A real state-machine framework controls nodes, conditional edges, loops, retries, durable
pauses, and terminal outcomes.

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

The full node/edge graph, role table, tool interface, security model, and persistence
story are in [`docs/architecture.md`](docs/architecture.md).

## Capstone features

- **Real tools:** contract reading, clause extraction, BM25 policy search, risk
  calculation, PII masking, and MinIO/filesystem artifact storage.
- **Graph orchestration:** 16 named nodes, conditional branches, three bounded loops,
  and shared serializable state using the `transitions` state-machine framework.
- **Multi-agent team:** Input Security, Coordinator, Document Analyst, Policy Research,
  Compliance Analyst, Quality Reviewer, Security Reviewer, Report Writer, Output
  Guardian, and Artifact Storage agents.
- **Guardrails:** direct/indirect prompt-injection blocking, tool allow-list and schema
  validation, secret-pattern rejection, strict output schema, and PII masking.
- **Observability:** structured JSONL logs plus Prometheus counters/histograms for nodes,
  tools, latency, failures, retries, guardrails, interrupts, and outcomes.
- **Production readiness:** SQLite WAL checkpoints, real HITL pause/resume, FastAPI,
  Docker, Compose, MinIO/S3-compatible storage, and Prometheus.

## Repository structure

```text
src/contractguard/       Core agents, graph, tools, guardrails, persistence, API
src/contractguard/_vendor/transitions/
                         Offline fallback of the MIT-licensed graph dependency
data/policies/           Corporate policy knowledge base
data/samples/            Safe, high-risk, and attack contracts
scripts/                 End-to-end capstone evidence runner
tests/                   Security, graph, persistence, and API tests
notebooks/               Executed evaluator notebook
evidence/                Captured outputs, logs, metrics, reports, test results
docs/                    Architecture, rubric mapping, security, and API docs
deploy/                  Prometheus configuration
```

## Local setup

Prerequisites: Python 3.11+, Git, and optionally Docker Desktop.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .
```

The default `LLM_PROVIDER=offline` mode is intentionally reproducible and requires no
secret. It still executes the complete graph, reasoning traces, tools, guardrails,
checkpointing, HITL, and reports. To enable optional Groq executive-summary generation:

```bash
cp .env.example .env
# Set LLM_PROVIDER=groq and GROQ_API_KEY in .env; never commit the key.
```

## Run the complete scored evidence suite

```bash
python scripts/run_capstone_demo.py
pytest
```

The demo deliberately executes all important paths:

1. a malicious uploaded prompt is blocked before any tool runs;
2. a low-risk contract completes autonomously;
3. a policy-search timeout fires a retry edge;
4. a Reflexion score fires a re-search edge;
5. a high-risk contract pauses for human approval;
6. the service is closed and recreated, proving SQLite restart persistence;
7. approval resumes the graph;
8. a malformed first draft fires the output-validation revision loop;
9. PII is masked and the final report is stored.

Open `notebooks/ContractGuard_Capstone_Executed.ipynb` for captured outputs and
`evidence/run_summary.json` for an evaluator-friendly assertion summary.

## CLI examples

Start a low-risk audit:

```bash
contractguard start \
  --thread-id demo-low \
  --request "Audit this contract against all corporate policies" \
  --contract data/samples/vendor_contract_low_risk.txt
```

Start a high-risk audit and demonstrate retries:

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

Then use `/docs` for the generated OpenAPI interface. Endpoints include start, status,
history, resume, graph, health, and Prometheus metrics. See [`docs/api.md`](docs/api.md).

## Docker Compose simulated cloud environment

```bash
cp .env.example .env
# Replace the sample MinIO password in .env.
docker compose up --build
```

Services:

- API: port 8000
- MinIO S3 API: port 9000; console: 9001
- Prometheus: port 9090

The application uses a non-root container user, health check, persistent volumes,
environment-only secrets, and MinIO as the simulated cloud object store.

## Evidence index

| Evidence | What it proves |
|---|---|
| `01_prompt_injection_blocked.json` | Real attack blocked; zero tool calls |
| `02_low_risk_completed.json` | Complete autonomous happy path |
| `03_high_risk_paused_for_human.json` | Retry/re-plan loops and actual HITL pause |
| `04_checkpoint_loaded_after_restart.json` | State survived service restart |
| `05_high_risk_resumed_and_completed.json` | Human resume, output revision, PII masking, artifact |
| `execution_log.jsonl` | Structured logs for nodes, tools, failures, latency, security |
| `metrics_*.prom` | Prometheus monitoring data |
| `graph_spec.json` | Framework nodes, edges, conditions, and loops |
| `pytest_results.txt` | Automated regression tests |
| executed notebook | Captured narrative and outputs for all rubric items |

The exact rubric-to-evidence map is in
[`docs/rubric_traceability.md`](docs/rubric_traceability.md).
Course-file concepts and the supplied lab progression are mapped in
[`docs/course_alignment.md`](docs/course_alignment.md).

## Git workflow

The repository includes a `.gitignore` that excludes secrets and generated runtime
artifacts. A recommended incremental history is:

```text
feat: scaffold typed contract audit domain and tool interface
feat: add state graph, specialist agents, retries, and checkpointing
feat: enforce guardrails, observability, and human approval resume
feat: add FastAPI, Docker Compose, MinIO, and Prometheus deployment
 test/docs: add executed evidence, tests, and capstone documentation
```

## Limitations and safe extension points

The bundled policy rules are an educational corporate-policy simulation, not legal
advice. Replace them with organization-approved policies and legal review before real
use. Authentication/RBAC and managed secret storage should be added before exposing the
API beyond a controlled environment. The optional cloud LLM is isolated behind
`GroqReasoner`, so another OpenAI-compatible provider can be substituted without changing
the graph.

## License and third-party notices

Project code is MIT licensed. The offline fallback for `transitions` 0.9.3 retains its
upstream MIT license; see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
