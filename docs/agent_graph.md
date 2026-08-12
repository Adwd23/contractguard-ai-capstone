# ContractGuard AI State Graph

GitHub renders the Mermaid diagram below directly. Every box is an executable graph node;
labels on arrows are framework-managed conditions or human commands.

**Framework:** `transitions.Machine` 0.9.3. The machine configuration is serialized to
`evidence/graph_spec.json` with package/version, nodes, edges, conditions, and loops.

```mermaid
flowchart TD
    START([received]) --> guardrailed[guardrailed: Input Security Agent]
    guardrailed -->|input_blocked| blocked([blocked])
    guardrailed -->|safe| planned[planned: Coordinator Agent]
    planned --> ingested[ingested: Document Analyst Agent]
    ingested --> researching[researching: Policy Research Agent]
    researching -->|tool error and retries remain| researching
    researching -->|tool error exhausted| failed([failed])
    researching -->|evidence retrieved| analyzed[analyzed: Compliance Analyst Agent]
    analyzed --> quality[quality_reviewed: Quality Reviewer Agent]
    quality -->|evidence insufficient| researching
    quality -->|quality gate passed| security[security_reviewed: Security Reviewer Agent]
    security -->|high risk or value| approval[awaiting_approval: Human interrupt]
    security -->|approval not required| reporting[reporting: Report Writer Agent]
    approval -->|approve| reporting
    approval -->|reject| rejected([rejected])
    reporting --> validation[output_validated: Output Guardian Agent]
    validation -->|schema/PII gate fails and revisions remain| reporting
    validation -->|revisions exhausted| failed
    validation -->|valid| persisting[persisting: Artifact Storage Agent]
    persisting --> completed([completed])
```

## Bounded-cycle controls

| Loop | Exit condition |
|---|---|
| Policy tool retry | Success or `MAX_POLICY_RETRIES` exhausted |
| Reflexion/re-search | Evidence coverage passes or `MAX_QUALITY_RETRIES` exhausted |
| Report revision | Pydantic output schema passes or `MAX_REPORT_REVISIONS` exhausted |
| Whole workflow | Terminal/pause node or `MAX_GRAPH_STEPS` safety stop |

The serializable shared state is checkpointed to SQLite after every framework transition.
