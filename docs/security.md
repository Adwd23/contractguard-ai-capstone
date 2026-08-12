# Security Design

## Input enforcement

The first graph node is backed by `InputGuardrail.enforce()`. It examines the user request and untrusted contract content before any tool-capable specialist can execute. If a prompt-injection, instruction-override, destructive-command, or jailbreak pattern is detected, it raises `GuardrailViolation`, records a structured security event, and the graph routes directly to `blocked`.

The required attack demonstration uses an uploaded contract containing an indirect prompt injection. The resulting evidence must show:

```text
status = blocked
guardrail_enforced = true
tool_calls = []
node_history = received -> input_guardrail -> blocked
```

## Output and privacy enforcement

`OutputGuardrail.enforce()` runs before artifact persistence. It masks email addresses, phone numbers, Saudi national IDs, Saudi IBANs, and payment-card-like values; blocks secret-like material; and validates the report against the strict `AuditReport` Pydantic schema. Invalid output is routed back to `report_writer` within a bounded revision budget.

## Tool isolation

Every specialist has an explicit tool allow-list. A call outside the role's permissions raises `AgentToolPermissionError`. Tool arguments are validated against strict Pydantic input schemas before execution.

## Filesystem and API boundaries

- Contract files must resolve under `CONTRACT_ALLOWED_ROOTS`.
- Thread identifiers use a restricted safe format.
- `/audits` routes support optional `X-API-Key` authentication.
- `.env` and runtime secret files are ignored by Git.
- Raw contract excerpts are excluded from optional external model summary calls; only minimized, redacted context is sent.

## Checkpoint integrity

The graph uses the LangGraph SQLite checkpointer with strict MessagePack deserialization enabled through `LANGGRAPH_STRICT_MSGPACK=true`. The checkpoint database is treated as integrity-sensitive runtime data and is not committed.

## Observability

Security and failure events are structured JSONL records, including guardrail blocks, denied tool permissions, failed tools, retries, human interrupts, and terminal outcomes. Prometheus counters/histograms capture tool, node, LLM, guardrail, retry, and latency signals.
