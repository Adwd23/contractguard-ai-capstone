"""Quality Reviewer Agent: independent Reflexion/self-critique specialist."""
from __future__ import annotations

from typing import Any

from .base import BaseAgent

class QualityReviewerAgent(BaseAgent):
    def run(self, state: dict[str, Any]) -> None:
        required_topics = {
            clause.get("topic", "general")
            for clause in state.get("clauses", [])
            if clause.get("topic", "general") != "general"
        }
        evidence_topics = {item.get("topic") for item in state.get("policy_evidence", [])}
        covered = required_topics.intersection(evidence_topics)
        score = len(covered) / max(len(required_topics), 1)

        if state.get("flags", {}).get("simulate_quality_retry") and int(state.get("quality_retry_count", 0)) == 0:
            score = min(score, 0.5)

        state["quality_score"] = round(score, 3)
        missing = sorted(required_topics - evidence_topics)
        can_retry = int(state.get("quality_retry_count", 0)) < int(state.get("max_quality_retries", 1))
        state["needs_more_research"] = score < 0.75 and can_retry
        state["additional_policy_queries"] = [
            {
                "topic": topic,
                "query": f"mandatory corporate contract policy requirements for {topic.replace('_', ' ')}",
            }
            for topic in missing
        ]
        if state["needs_more_research"] and not state["additional_policy_queries"]:
            state["additional_policy_queries"] = [
                {"topic": "general", "query": "mandatory vendor contract compliance clauses and exceptions"}
            ]

        self.send(
            state,
            recipient="Coordinator Agent",
            message_type="critique",
            content=(
                f"Evidence coverage score is {score:.0%}; "
                + ("re-planning targeted research." if state["needs_more_research"] else "quality gate passed.")
            ),
            payload={"missing_topics": missing, "quality_score": state["quality_score"]},
        )
