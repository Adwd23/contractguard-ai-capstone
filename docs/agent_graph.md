# Agent Graph

**Framework:** LangGraph `StateGraph`
**Shared state:** `AuditState`
**Checkpointer:** `langgraph.checkpoint.sqlite.SqliteSaver`

```mermaid
flowchart TD
    START([START]) --> input[input_guardrail: Input Security Agent]
    input -->|blocked| blocked([blocked])
    input -->|safe| coord[coordinator: Coordinator Agent]
    coord --> doc[document_analyst: Document Analyst Agent]
    doc --> research[policy_research: Policy Research Agent]
    research -->|tool failure and retries remain| research
    research -->|success| compliance[compliance_analyst: Compliance Analyst Agent]
    research -->|retry exhausted| failed([failed])
    compliance --> quality[quality_reviewer: Quality Reviewer Agent]
    quality -->|insufficient evidence| research
    quality -->|pass| security[security_reviewer: Security Reviewer Agent]
    security -->|human required| gate[approval_gate]
    security -->|automatic| writer[report_writer: Report Writer Agent]
    gate --> human[human_approval: interrupt]
    human -->|Command approve| writer
    human -->|Command reject| rejected([rejected])
    writer --> output[output_guardian: Output Guardian Agent]
    output -->|revise| writer
    output -->|valid| storage[artifact_storage: Artifact Storage Agent]
    output -->|revision exhausted| failed
    storage --> completed([completed])
```

The graph source contains five explicit `add_conditional_edges(...)` calls. The human node has no hardcoded outgoing edge: its post-resume destination is selected by `Command(goto=...)` after the external `Command(resume=...)` supplies the human decision.
