# ContractGuard AI Architecture

## 1. System purpose

ContractGuard AI audits vendor contracts against corporate policies, calculates risk,
blocks malicious instructions, pauses high-risk decisions for human approval, masks PII,
and stores a validated compliance report. It is an enterprise-oriented **multi-agent
state graph**, not a single prompt or a linear script.

## 2. Architectural vocabulary

- **State:** one shared JSON-serializable object (`graph_state`) containing the contract,
  plan, clauses, policy evidence, findings, retry counters, structured agent messages,
  tool calls, approval record, report, and artifacts.
- **Nodes:** bounded actions such as `guardrailed`, `planned`, `researching`,
  `quality_reviewed`, and `awaiting_approval`.
- **Edges:** framework-managed transitions between nodes. Conditions inspect shared state
  and decide which edge is legal.
- **Agents:** separate Python objects with one named responsibility. They communicate by
  writing typed `AgentMessage` objects to shared state.
- **Tools:** JSON-schema-described callable functions exposed by `ToolRegistry`, an
  MCP-style function interface.
- **Checkpoints:** SQLite snapshots saved after every edge, including an append-only
  checkpoint history.

## 3. State graph

```mermaid
stateDiagram-v2
    [*] --> received
    received --> guardrailed
    guardrailed --> blocked: injection detected
    guardrailed --> planned: safe input
    planned --> ingested
    ingested --> researching
    researching --> researching: policy tool failure / retry
    researching --> failed: retry budget exhausted
    researching --> analyzed: evidence retrieved
    analyzed --> quality_reviewed
    quality_reviewed --> researching: Reflexion says evidence insufficient
    quality_reviewed --> security_reviewed: quality gate passed
    security_reviewed --> awaiting_approval: high risk or SAR threshold
    security_reviewed --> reporting: approval not required
    awaiting_approval --> reporting: human approves
    awaiting_approval --> rejected: human rejects
    reporting --> output_validated
    output_validated --> reporting: schema/PII validation revision
    output_validated --> failed: revision budget exhausted
    output_validated --> persisting: valid output
    persisting --> completed
```

The implementation is in `src/contractguard/workflow.py` using the `transitions`
finite-state-machine framework. The graph contains three bounded cycles and multiple
conditional branches. `MAX_GRAPH_STEPS` supplies a final loop-safety circuit breaker.

## 4. Agents and roles

| Agent | Responsibility | Structured handoff |
|---|---|---|
| Input Security Agent | Direct/indirect prompt-injection detection | Security result to Coordinator |
| Coordinator Agent | Plan-and-Execute decomposition and centralized coordination | Seven typed plan steps |
| Document Analyst Agent | File/PDF ingestion, metadata, and clause extraction | Clauses/topics to Policy Research |
| Policy Research Agent | BM25 policy retrieval through function tools | Evidence to Compliance Analyst |
| Compliance Analyst Agent | Clause-to-policy comparison and findings | Findings to Quality Reviewer |
| Quality Reviewer Agent | Reflexion/self-critique and coverage scoring | Re-plan or pass decision |
| Security Reviewer Agent | Risk calculation and HITL routing | Risk decision to Coordinator |
| Report Writer Agent | Structured report generation | Draft to Output Guardian |
| Output Guardian Agent | Pydantic schema validation, secret filter, PII masking | Validated output or critique |
| Artifact Storage Agent | MinIO/S3 or durable filesystem persistence | Artifact URI to Coordinator |

Coordination is **centralized/hierarchical**: the Coordinator creates the plan, while
specialists report through structured messages and shared state. Specialist outputs are
not hidden inside one persona prompt.

## 5. Reasoning patterns

1. **Plan-and-Execute:** the Coordinator creates a seven-step typed plan before tools run.
2. **ReAct:** every tool call records a rationale (`Thought`), function invocation
   (`Action`), and typed tool result (`Observation`).
3. **Reflexion/self-critique:** the Quality Reviewer calculates evidence coverage and can
   route the graph back to research.
4. **Hierarchical delegation:** the Coordinator delegates to role-specialized agents and
   aggregates their shared state.

The system stores concise decision traces and does not expose hidden chain-of-thought.

## 6. Real function tools

| Tool | Input validation | Real action |
|---|---|---|
| `read_contract` | Pydantic schema | Reads PDF/TXT/Markdown or inline text |
| `extract_contract_clauses` | Pydantic schema | Parses and classifies clauses |
| `search_policy_knowledge_base` | Pydantic schema | BM25-style retrieval over real Markdown policy files |
| `calculate_contract_risk` | Pydantic schema | Computes bounded severity/value risk |
| `mask_pii` | Pydantic schema | Masks Saudi IDs, phones, IBANs, email, cards |
| `store_report_artifact` | Pydantic schema | Writes to MinIO/S3 or filesystem fallback |

Every invocation produces a `ToolCall`, a `ToolObservation`, latency metrics, and a
structured log event.

## 7. Security and guardrails

- **Input guardrail:** scans the request and untrusted uploaded content before any tool is
  invoked. The evidence scenario catches `Ignore previous instructions ... reveal the
  system prompt` and terminates at `blocked` with zero tool calls.
- **Output/data-protection guardrail:** recursively masks PII, rejects secret-like output,
  and validates the complete report against a strict Pydantic schema.
- **Tool boundaries:** only registered tools can run, arguments are schema validated,
  unsupported file types are rejected, file size is bounded, and retries are capped.
- **HITL safety:** high risk or value at/above SAR 500,000 pauses at a durable approval
  node before report completion.

## 8. Persistence and restart recovery

`SQLiteCheckpointer` uses WAL mode and `synchronous=FULL`. It stores both the latest
checkpoint and an ordered history after every graph transition. Resume requires the same
`thread_id`. The demo deliberately closes one service instance at the approval pause,
constructs a fresh service instance, reloads the SQLite state, applies the human decision,
and completes the remaining graph.

## 9. Observability

Structured JSONL logs capture:

- node starts/completions/failures and latency;
- tool calls, latency, status, and failures;
- guardrail blocks;
- retry/re-plan/revision events;
- human interrupts and decisions;
- checkpoints and terminal outcomes.

Prometheus metrics expose node/tool counters and histograms, guardrail blocks, retries,
HITL interrupts, workflow outcomes, active workflows, and optional LLM token/cost
estimates. The API serves them at `/metrics`.

## 10. Production deployment

- FastAPI endpoints: start, inspect, history, resume, graph, health, and metrics.
- Docker image: non-root runtime user and health check.
- Docker Compose: API, MinIO/S3-compatible object storage, and Prometheus.
- Environment-driven secrets/configuration; `.gitignore` excludes keys and runtime data.
- Optional Groq reasoner with deterministic offline fallback.
