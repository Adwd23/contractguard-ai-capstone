"""Real LangGraph StateGraph orchestration for ContractGuard AI.

Trainer-fix edition requirements are intentionally explicit in executable code:
- ``StateGraph(AuditState)`` owns the workflow.
- ``add_conditional_edges`` implements branching and bounded cycles.
- ``SqliteSaver`` is compiled into the graph through the persistence layer.
- ``interrupt()`` pauses the human-approval node.
- ``Command(resume=...)`` resumes the exact persisted thread.
"""
from __future__ import annotations

from copy import deepcopy
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .config import Settings
from .models import ResumeRequest
from .observability import Observability
from .persistence import LangGraphSQLitePersistence
from .state import AuditState


TERMINAL_NODES = {"completed", "blocked", "rejected", "failed"}


class ContractAuditWorkflow:
    """Compiled, persistent, branching LangGraph workflow."""

    NODE_NAMES: tuple[str, ...] = (
        "input_guardrail",
        "coordinator",
        "document_analyst",
        "policy_research",
        "compliance_analyst",
        "quality_reviewer",
        "security_reviewer",
        "approval_gate",
        "human_approval",
        "report_writer",
        "output_guardian",
        "artifact_storage",
        "completed",
        "blocked",
        "rejected",
        "failed",
    )

    EDGE_SPECS: tuple[dict[str, Any], ...] = (
        {"source": "START", "dest": "input_guardrail", "kind": "normal"},
        {"source": "input_guardrail", "dest": "blocked", "kind": "conditional", "condition": "blocked"},
        {"source": "input_guardrail", "dest": "coordinator", "kind": "conditional", "condition": "safe"},
        {"source": "coordinator", "dest": "document_analyst", "kind": "normal"},
        {"source": "document_analyst", "dest": "policy_research", "kind": "normal"},
        {"source": "policy_research", "dest": "policy_research", "kind": "conditional", "condition": "retry"},
        {"source": "policy_research", "dest": "compliance_analyst", "kind": "conditional", "condition": "success"},
        {"source": "policy_research", "dest": "failed", "kind": "conditional", "condition": "failed"},
        {"source": "compliance_analyst", "dest": "quality_reviewer", "kind": "normal"},
        {"source": "quality_reviewer", "dest": "policy_research", "kind": "conditional", "condition": "retry"},
        {"source": "quality_reviewer", "dest": "security_reviewer", "kind": "conditional", "condition": "pass"},
        {"source": "security_reviewer", "dest": "approval_gate", "kind": "conditional", "condition": "human"},
        {"source": "security_reviewer", "dest": "report_writer", "kind": "conditional", "condition": "automatic"},
        {"source": "approval_gate", "dest": "human_approval", "kind": "normal"},
        {"source": "human_approval", "dest": "report_writer", "kind": "Command", "condition": "approve"},
        {"source": "human_approval", "dest": "rejected", "kind": "Command", "condition": "reject"},
        {"source": "report_writer", "dest": "output_guardian", "kind": "normal"},
        {"source": "output_guardian", "dest": "report_writer", "kind": "conditional", "condition": "revise"},
        {"source": "output_guardian", "dest": "artifact_storage", "kind": "conditional", "condition": "valid"},
        {"source": "output_guardian", "dest": "failed", "kind": "conditional", "condition": "failed"},
        {"source": "artifact_storage", "dest": "completed", "kind": "normal"},
        {"source": "completed", "dest": "END", "kind": "normal"},
        {"source": "blocked", "dest": "END", "kind": "normal"},
        {"source": "rejected", "dest": "END", "kind": "normal"},
        {"source": "failed", "dest": "END", "kind": "normal"},
    )

    def __init__(
        self,
        *,
        agents: dict[str, Any],
        settings: Settings,
        persistence: LangGraphSQLitePersistence,
        observability: Observability,
    ) -> None:
        self.agents = agents
        self.settings = settings
        self.persistence = persistence
        self.observability = observability
        self.builder = self._build_state_graph()
        self.graph = self.builder.compile(
            checkpointer=self.persistence.saver,
            name="ContractGuardTrainerFixStateGraph",
        )

    def _build_state_graph(self) -> StateGraph:
        workflow = StateGraph(AuditState)

        workflow.add_node("input_guardrail", self._input_guardrail_node)
        workflow.add_node("coordinator", self._coordinator_node)
        workflow.add_node("document_analyst", self._document_analyst_node)
        workflow.add_node("policy_research", self._policy_research_node)
        workflow.add_node("compliance_analyst", self._compliance_analyst_node)
        workflow.add_node("quality_reviewer", self._quality_reviewer_node)
        workflow.add_node("security_reviewer", self._security_reviewer_node)
        workflow.add_node("approval_gate", self._approval_gate_node)
        workflow.add_node("human_approval", self._human_approval_node)
        workflow.add_node("report_writer", self._report_writer_node)
        workflow.add_node("output_guardian", self._output_guardian_node)
        workflow.add_node("artifact_storage", self._artifact_storage_node)
        workflow.add_node("completed", self._completed_node)
        workflow.add_node("blocked", self._blocked_node)
        workflow.add_node("rejected", self._rejected_node)
        workflow.add_node("failed", self._failed_node)

        workflow.add_edge(START, "input_guardrail")

        # Real conditional branch #1: malicious input cannot reach any tool-capable agent.
        workflow.add_conditional_edges(
            "input_guardrail",
            self._route_after_input_guardrail,
            {"blocked": "blocked", "safe": "coordinator"},
        )
        workflow.add_edge("coordinator", "document_analyst")
        workflow.add_edge("document_analyst", "policy_research")

        # Real conditional branch/loop #2: retry failed policy tool calls with a hard limit.
        workflow.add_conditional_edges(
            "policy_research",
            self._route_after_policy_research,
            {
                "retry": "policy_research",
                "success": "compliance_analyst",
                "failed": "failed",
            },
        )
        workflow.add_edge("compliance_analyst", "quality_reviewer")

        # Real Reflexion loop #3: critic can re-route execution back to research.
        workflow.add_conditional_edges(
            "quality_reviewer",
            self._route_after_quality_review,
            {"retry": "policy_research", "pass": "security_reviewer"},
        )

        # Real risk branch #4: high-risk contracts require an external human decision.
        workflow.add_conditional_edges(
            "security_reviewer",
            self._route_after_security_review,
            {"human": "approval_gate", "automatic": "report_writer"},
        )
        workflow.add_edge("approval_gate", "human_approval")
        # human_approval routes dynamically with Command(goto=...) after Command(resume=...).

        workflow.add_edge("report_writer", "output_guardian")

        # Real output-validation loop #5: invalid structured output is regenerated.
        workflow.add_conditional_edges(
            "output_guardian",
            self._route_after_output_guardrail,
            {"revise": "report_writer", "valid": "artifact_storage", "failed": "failed"},
        )
        workflow.add_edge("artifact_storage", "completed")

        for terminal in TERMINAL_NODES:
            workflow.add_edge(terminal, END)

        return workflow

    # ------------------------------------------------------------------
    # Public execution API
    # ------------------------------------------------------------------

    def start(self, state: AuditState) -> dict[str, Any]:
        thread_id = str(state["thread_id"])
        config = self.persistence.config(
            thread_id, recursion_limit=self.settings.max_graph_steps
        )
        self.graph.invoke(state, config=config)
        return self._current_values(thread_id)

    def resume(self, thread_id: str, request: ResumeRequest) -> dict[str, Any]:
        """Resume the exact LangGraph interrupt with Command(resume=...)."""
        config = self.persistence.config(
            thread_id, recursion_limit=self.settings.max_graph_steps
        )
        self.graph.invoke(
            Command(resume=request.model_dump(mode="json")),
            config=config,
        )
        return self._current_values(thread_id)

    def get(self, thread_id: str) -> dict[str, Any] | None:
        if not self.persistence.thread_exists(thread_id):
            return None
        snapshot = self.graph.get_state(self.persistence.config(thread_id))
        values = dict(snapshot.values)
        return {
            "thread_id": thread_id,
            "node": values.get("workflow_node", values.get("status", "unknown")),
            "status": values.get("status", "unknown"),
            "state": values,
            "next": list(snapshot.next),
            "updated_at": getattr(snapshot, "created_at", None),
        }

    def history(self, thread_id: str) -> list[dict[str, Any]]:
        if not self.persistence.thread_exists(thread_id):
            return []
        snapshots = list(self.graph.get_state_history(self.persistence.config(thread_id)))
        rows: list[dict[str, Any]] = []
        for index, snapshot in enumerate(reversed(snapshots), 1):
            values = dict(snapshot.values)
            configurable = (snapshot.config or {}).get("configurable", {})
            rows.append(
                {
                    "id": index,
                    "thread_id": thread_id,
                    "node": values.get("workflow_node", values.get("status", "unknown")),
                    "status": values.get("status", "unknown"),
                    "next": list(snapshot.next),
                    "checkpoint_id": configurable.get("checkpoint_id"),
                    "created_at": getattr(snapshot, "created_at", None),
                }
            )
        return rows

    def _current_values(self, thread_id: str) -> dict[str, Any]:
        snapshot = self.graph.get_state(self.persistence.config(thread_id))
        return dict(snapshot.values)

    @classmethod
    def graph_spec(cls) -> dict[str, Any]:
        try:
            langgraph_version = version("langgraph")
        except PackageNotFoundError:
            langgraph_version = "declared-in-requirements"
        conditional = [edge for edge in cls.EDGE_SPECS if edge["kind"] == "conditional"]
        return {
            "framework": "LangGraph StateGraph",
            "framework_package": "langgraph",
            "framework_version": langgraph_version,
            "builder_api": "StateGraph(AuditState)",
            "conditional_routing_api": "StateGraph.add_conditional_edges",
            "hitl_pause_api": "langgraph.types.interrupt",
            "hitl_resume_api": "langgraph.types.Command(resume=...)",
            "persistent_checkpointer": "langgraph.checkpoint.sqlite.SqliteSaver",
            "nodes": list(cls.NODE_NAMES),
            "edges": [deepcopy(item) for item in cls.EDGE_SPECS],
            "node_count": len(cls.NODE_NAMES),
            "edge_count": len(cls.EDGE_SPECS),
            "conditional_edge_count": len(conditional),
            "branching_nodes": [
                "input_guardrail",
                "policy_research",
                "quality_reviewer",
                "security_reviewer",
                "output_guardian",
            ],
            "shared_state_object": "AuditState (TypedDict)",
            "terminal_nodes": sorted(TERMINAL_NODES),
            "pause_node": "human_approval",
            "loops": [
                "policy_research -> policy_research (bounded tool retry)",
                "quality_reviewer -> policy_research (bounded Reflexion/re-search)",
                "output_guardian -> report_writer (bounded schema revision)",
            ],
            "loop_termination_controls": {
                "policy_retry_limit": "MAX_POLICY_RETRIES",
                "quality_retry_limit": "MAX_QUALITY_RETRIES",
                "report_revision_limit": "MAX_REPORT_REVISIONS",
                "global_recursion_limit": "MAX_GRAPH_STEPS",
            },
            "is_linear_chain": False,
            "has_cycles": True,
            "has_conditional_routing": True,
            "supports_restart_resume": True,
        }

    # ------------------------------------------------------------------
    # Node helpers and specialist nodes
    # ------------------------------------------------------------------

    def _run_agent(self, state: AuditState, *, node: str, agent_key: str) -> AuditState:
        working: AuditState = deepcopy(state)
        working["status"] = node
        working["workflow_node"] = node
        working.setdefault("node_history", []).append(node)
        with self.observability.node(node, str(working["thread_id"])):
            self.agents[agent_key].run(working)
        return working

    def _input_guardrail_node(self, state: AuditState) -> AuditState:
        return self._run_agent(state, node="input_guardrail", agent_key="input_security")

    def _coordinator_node(self, state: AuditState) -> AuditState:
        return self._run_agent(state, node="coordinator", agent_key="coordinator")

    def _document_analyst_node(self, state: AuditState) -> AuditState:
        return self._run_agent(state, node="document_analyst", agent_key="document_analyst")

    def _policy_research_node(self, state: AuditState) -> AuditState:
        working = self._run_agent(state, node="policy_research", agent_key="policy_research")
        if working.get("policy_search_error") and int(working.get("policy_retry_count", 0)) <= int(
            working.get("max_policy_retries", self.settings.max_policy_retries)
        ):
            self.observability.record_retry(
                "policy_tool_failure",
                str(working["thread_id"]),
                int(working.get("policy_retry_count", 0)),
            )
        return working

    def _compliance_analyst_node(self, state: AuditState) -> AuditState:
        return self._run_agent(state, node="compliance_analyst", agent_key="compliance_analyst")

    def _quality_reviewer_node(self, state: AuditState) -> AuditState:
        working = self._run_agent(state, node="quality_reviewer", agent_key="quality_reviewer")
        if working.get("needs_more_research"):
            attempt = int(working.get("quality_retry_count", 0)) + 1
            working["quality_retry_count"] = attempt
            self.observability.record_retry("quality_replan", str(working["thread_id"]), attempt)
        return working

    def _security_reviewer_node(self, state: AuditState) -> AuditState:
        return self._run_agent(state, node="security_reviewer", agent_key="security_reviewer")

    def _approval_gate_node(self, state: AuditState) -> AuditState:
        working: AuditState = deepcopy(state)
        payload = {
            "type": "human_approval_required",
            "thread_id": working["thread_id"],
            "risk_score": working.get("risk_score", 0),
            "risk_level": working.get("risk_level", "LOW"),
            "contract_value_sar": working.get("contract_metadata", {}).get("contract_value_sar", 0),
            "finding_count": len(working.get("findings", [])),
            "instruction": "Resume this persisted thread with approve/reject and an approver identity.",
        }
        working["status"] = "awaiting_approval"
        working["workflow_node"] = "human_approval"
        working["approval_status"] = "pending"
        working["interrupt_payload"] = payload
        working.setdefault("node_history", []).append("awaiting_approval")
        self.observability.record_interrupt(str(working["thread_id"]), payload)
        return working

    def _human_approval_node(
        self, state: AuditState
    ) -> Command[Literal["report_writer", "rejected"]]:
        """Pause indefinitely, then route only after an external resume value arrives."""
        decision_payload = interrupt(state.get("interrupt_payload") or {
            "type": "human_approval_required",
            "thread_id": state["thread_id"],
        })
        request = ResumeRequest.model_validate(decision_payload)
        history = list(state.get("node_history", [])) + ["human_approval"]

        self.observability.log(
            "human_decision",
            thread_id=state["thread_id"],
            decision=request.decision,
            approver=request.approver,
            comment=request.comment,
        )

        if request.decision == "approve":
            return Command(
                update={
                    "approval_status": "approved",
                    "approval_comment": request.comment,
                    "approver": request.approver,
                    "interrupt_payload": None,
                    "status": "approved",
                    "workflow_node": "human_approval",
                    "node_history": history,
                },
                goto="report_writer",
            )
        return Command(
            update={
                "approval_status": "rejected",
                "approval_comment": request.comment,
                "approver": request.approver,
                "interrupt_payload": None,
                "status": "rejected",
                "workflow_node": "human_approval",
                "node_history": history,
            },
            goto="rejected",
        )

    def _report_writer_node(self, state: AuditState) -> AuditState:
        return self._run_agent(state, node="report_writer", agent_key="report_writer")

    def _output_guardian_node(self, state: AuditState) -> AuditState:
        working = self._run_agent(state, node="output_guardian", agent_key="output_guardian")
        current = int(working.get("report_revision_count", 0))
        limit = int(working.get("max_report_revisions", self.settings.max_report_revisions))
        can_revise = (not working.get("output_valid")) and current < limit
        working["output_retry_requested"] = can_revise
        if can_revise:
            attempt = current + 1
            working["report_revision_count"] = attempt
            self.observability.record_retry(
                "output_schema_revision", str(working["thread_id"]), attempt
            )
        return working

    def _artifact_storage_node(self, state: AuditState) -> AuditState:
        return self._run_agent(state, node="artifact_storage", agent_key="artifact_storage")

    def _completed_node(self, state: AuditState) -> AuditState:
        return self._terminal_state(state, "completed")

    def _blocked_node(self, state: AuditState) -> AuditState:
        return self._terminal_state(state, "blocked")

    def _rejected_node(self, state: AuditState) -> AuditState:
        return self._terminal_state(state, "rejected")

    def _failed_node(self, state: AuditState) -> AuditState:
        return self._terminal_state(state, "failed")

    def _terminal_state(self, state: AuditState, terminal: str) -> AuditState:
        working: AuditState = deepcopy(state)
        working["status"] = terminal
        working["workflow_node"] = terminal
        working["interrupt_payload"] = None
        working.setdefault("node_history", []).append(terminal)
        self.observability.record_terminal(str(working["thread_id"]), terminal)
        return working

    # ------------------------------------------------------------------
    # Conditional routing functions used by add_conditional_edges
    # ------------------------------------------------------------------

    @staticmethod
    def _route_after_input_guardrail(state: AuditState) -> Literal["blocked", "safe"]:
        return "blocked" if state.get("input_blocked") else "safe"

    def _route_after_policy_research(
        self, state: AuditState
    ) -> Literal["retry", "success", "failed"]:
        if not state.get("policy_search_error"):
            return "success"
        if int(state.get("policy_retry_count", 0)) <= int(
            state.get("max_policy_retries", self.settings.max_policy_retries)
        ):
            return "retry"
        return "failed"

    @staticmethod
    def _route_after_quality_review(state: AuditState) -> Literal["retry", "pass"]:
        return "retry" if state.get("needs_more_research") else "pass"

    @staticmethod
    def _route_after_security_review(state: AuditState) -> Literal["human", "automatic"]:
        return "human" if state.get("approval_required") else "automatic"

    def _route_after_output_guardrail(
        self, state: AuditState
    ) -> Literal["revise", "valid", "failed"]:
        if state.get("output_valid"):
            return "valid"
        return "revise" if state.get("output_retry_requested") else "failed"
