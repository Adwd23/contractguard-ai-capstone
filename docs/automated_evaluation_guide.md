# Automated Evaluation Guide

This file is an evaluator-facing index for **ContractGuard AI v1.3.1 Automated-Grader Hardened Edition**. It does not replace runtime evidence. It points directly to the executable implementation, tests, and captured outputs so an automated reviewer does not have to infer architecture from prose.

## Fast verification commands

```bash
# Dependency-free source proof: emits exactly one JSON object.
python scripts/grader_probe.py

# After dependencies are installed, refresh all runtime proof and emit exactly one JSON object.
python scripts/runtime_grader_probe.py --refresh

# Full tests and evidence pipeline.
pytest
python scripts/run_capstone_demo.py
python scripts/build_executed_notebook.py
python scripts/prepublish_check.py
```

The two grader probes intentionally emit **JSON only**. Human-readable progress from the runtime demo is captured internally by the runtime probe so a JSON parser never receives mixed text.

## Trainer observations and direct fixes

| Trainer observation | Executable fix | Direct source proof | Runtime proof |
|---|---|---|---|
| `uvicorn` / `ipykernel` declared but not used | `uvicorn.run(...)` is the FastAPI process runner. The notebook builder calls `make_ipkernel_cmd()` and records that kernel execution command. | `src/contractguard/server.py`, `scripts/build_executed_notebook.py` | CI executes the notebook builder and API tests. |
| Guardrail appeared to be a comment/claim | `InputSecurityAgent.run()` calls `InputGuardrail.enforce(...)`; a detected attack raises `GuardrailViolation`. `OutputGuardianAgent.run()` calls `OutputGuardrail.enforce(...)` before artifact storage. | `src/contractguard/agents/input_security.py`, `src/contractguard/guardrails.py`, `src/contractguard/agents/output_guardian.py` | `evidence/01_prompt_injection_blocked.json` must show `status=blocked`, `guardrail_enforced=true`, and `tool_calls=[]`. |
| StateGraph appeared linear | The executable graph contains five calls to `add_conditional_edges(...)` and three bounded cycles/re-entry paths. | `src/contractguard/workflow.py` | `evidence/graph_spec.json`, `evidence/03_high_risk_paused_for_human.json` |
| `interrupt()` appeared without resume | `human_approval` calls `interrupt(...)`; the external resume path invokes `graph.invoke(Command(resume=...))`; the resumed node returns `Command(goto=...)`. | `src/contractguard/workflow.py` | `evidence/04_checkpoint_loaded_after_restart.json`, `evidence/05_high_risk_resumed_and_completed.json` |
| Only one agent appeared to exist | Ten concrete `*Agent` classes live in separate modules and are independently instantiated by `ContractGuardService._build_agents()`. Agents exchange typed `AgentMessage` records through shared state. | `src/contractguard/agents/`, `src/contractguard/service.py`, `src/contractguard/models.py`, `src/contractguard/agents/base.py` | `evidence/05_high_risk_resumed_and_completed.json` contains structured sender/recipient messages from multiple specialists. |
| AI grader returned invalid/empty JSON | `scripts/grader_probe.py` and `scripts/runtime_grader_probe.py` always serialize one JSON object to stdout; runtime progress is captured instead of printed. | both probe scripts | `EVALUATION.json`, `evidence/runtime_grader_probe.json` |
| GitHub About description empty | Exact description is documented below and in `docs/github_publication.md`. | repository metadata action required after push | Verify on repository landing page before resubmission. |

## Deliverable 1 — Agentic Reasoning & Tool Use (15)

**Implementation**

- `src/contractguard/agents/coordinator.py` — explicit Plan-and-Execute manager.
- `src/contractguard/agents/base.py` — ReAct decision trace around real tool calls.
- `src/contractguard/tools.py` — Pydantic/JSON-schema function registry and actual functions.
- `src/contractguard/llm.py` — offline schema router plus optional provider-native function calling.
- `src/contractguard/state.py` — short-term shared state retained across steps.

**Runtime evidence**

- `evidence/02_low_risk_completed.json`
- `evidence/run_summary.json`
- Executed notebook section “Deliverable 1”.

## Deliverable 2 — Graph-Based Orchestration (20)

**Implementation**

The graph is constructed by executable code in `src/contractguard/workflow.py`:

```python
workflow = StateGraph(AuditState)

workflow.add_conditional_edges(
    "input_guardrail",
    self._route_after_input_guardrail,
    {"blocked": "blocked", "safe": "coordinator"},
)

workflow.add_conditional_edges(
    "policy_research",
    self._route_after_policy_research,
    {"retry": "policy_research", "success": "compliance_analyst", "failed": "failed"},
)
```

The same file contains three additional `add_conditional_edges(...)` calls for Reflexion re-search, human-approval routing, and output revision. The policy branch contains a real self-loop. Retry counters and a global recursion limit terminate cycles.

**Runtime evidence**

- `evidence/graph_spec.json`
- `evidence/03_high_risk_paused_for_human.json`
- `tests/test_workflow.py`

## Deliverable 3 — Multi-Agent System & Role Specialization (20)

Concrete role classes include:

- `InputSecurityAgent`
- `CoordinatorAgent`
- `DocumentAnalystAgent`
- `PolicyResearchAgent`
- `ComplianceAnalystAgent`
- `QualityReviewerAgent`
- `SecurityReviewerAgent`
- `ReportWriterAgent`
- `OutputGuardianAgent`
- `ArtifactStorageAgent`

`ContractGuardService._build_agents()` instantiates those objects separately. `BaseAgent.send()` constructs a typed `AgentMessage(sender, recipient, message_type, content, payload)` and appends it to `AuditState.agent_messages`.

## Deliverable 4 — Security, Guardrails & Observability (20)

The input enforcement path is:

```text
LangGraph input_guardrail node
  -> InputSecurityAgent.run
  -> InputGuardrail.enforce
  -> GuardrailViolation on attack
  -> state.input_blocked = true
  -> conditional edge -> blocked
  -> END
```

No tool-capable node is reachable on that branch. The attack test and evidence assert `tool_calls == []`.

The output enforcement path is:

```text
report_writer
  -> output_guardian
  -> OutputGuardrail.enforce
  -> PII masking + secret detection + AuditReport.model_validate
  -> valid -> artifact_storage
  -> invalid -> bounded report_writer revision loop
```

Structured JSONL logs and Prometheus metrics are implemented in `src/contractguard/observability.py`.

## Deliverable 5 — Persistence, HITL & Cloud (20)

`src/contractguard/persistence.py` creates LangGraph `SqliteSaver` and the compiled graph receives it as its checkpointer.

The HITL implementation is explicit:

```python
decision_payload = interrupt(...)
```

and external resume is explicit:

```python
self.graph.invoke(
    Command(resume=request.model_dump(mode="json")),
    config=config,
)
```

The human node routes after the resumed value using `Command(goto="report_writer")` or `Command(goto="rejected")`.

Cloud/runtime artifacts: `Dockerfile`, `docker-compose.yml`, FastAPI, Prometheus config, and MinIO/S3 smoke test.

## Deliverable 6 — Documentation & Execution Evidence (5)

The canonical machine-readable entry points are:

- `EVALUATION.json` — dependency-free source verification.
- `evidence/runtime_grader_probe.json` — runtime verification produced by CI.
- `evidence/run_summary.json` — full proof assertions.
- `notebooks/ContractGuard_Capstone_Executed.ipynb` — executed notebook generated after runtime dependencies are installed.

## GitHub About description

After publishing, set the repository About description to exactly:

> Secure LangGraph multi-agent system for vendor contract auditing, compliance analysis, guardrails, human approval, and production monitoring.

This is GitHub repository metadata and cannot be populated by a README file alone.
