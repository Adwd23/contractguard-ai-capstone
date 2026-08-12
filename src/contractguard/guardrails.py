"""Input, output, and data-protection guardrails."""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from .models import AuditReport


INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ignore previous instructions", re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I)),
    ("reveal system prompt", re.compile(r"reveal|show|print|leak", re.I)),
    ("system prompt extraction", re.compile(r"system\s+(prompt|message|configuration)", re.I)),
    ("instruction override", re.compile(r"override\s+(the\s+)?(policy|guardrail|rules|instructions)", re.I)),
    ("destructive command", re.compile(r"rm\s+-rf|drop\s+table|delete\s+all\s+records", re.I)),
    ("jailbreak token", re.compile(r"\b(jailbreak|developer\s+mode|DAN)\b", re.I)),
)

# The two broad patterns above are paired: a request is blocked only when a reveal verb
# and a system-prompt target both occur, reducing false positives for normal discussions.

PII_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "[REDACTED_EMAIL]"),
    ("saudi_iban", re.compile(r"\bSA\d{22}\b", re.I), "[REDACTED_IBAN]"),
    ("saudi_national_id", re.compile(r"\b[12]\d{9}\b"), "[REDACTED_NATIONAL_ID]"),
    ("phone", re.compile(r"(?<!\d)(?:\+?966|0)?5\d{8}(?!\d)"), "[REDACTED_PHONE]"),
    ("credit_card", re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "[REDACTED_CARD]"),
)

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:api[_-]?key|secret|password)\s*[:=]\s*[A-Za-z0-9_\-]{12,}", re.I),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def scan_prompt_injection(*texts: str) -> dict[str, Any]:
    combined = "\n".join(text for text in texts if text)
    matches: list[str] = []

    for label, pattern in INJECTION_PATTERNS:
        if pattern.search(combined):
            matches.append(label)

    # The word "reveal" alone is not enough; pair it with the system target.
    if "reveal system prompt" in matches and "system prompt extraction" not in matches:
        matches.remove("reveal system prompt")

    blocked = any(
        label in matches
        for label in (
            "ignore previous instructions",
            "instruction override",
            "destructive command",
            "jailbreak token",
        )
    ) or {"reveal system prompt", "system prompt extraction"}.issubset(set(matches))

    return {
        "blocked": blocked,
        "matches": sorted(set(matches)),
        "reason": "; ".join(sorted(set(matches))) if blocked else "",
    }


def mask_pii(text: str) -> tuple[str, int, list[str]]:
    masked = text
    total = 0
    categories: list[str] = []
    for category, pattern, replacement in PII_PATTERNS:
        masked, count = pattern.subn(replacement, masked)
        if count:
            total += count
            categories.extend([category] * count)
    return masked, total, categories


def mask_object(value: Any) -> tuple[Any, int, list[str]]:
    if isinstance(value, str):
        return mask_pii(value)
    if isinstance(value, list):
        result: list[Any] = []
        count = 0
        categories: list[str] = []
        for item in value:
            masked, item_count, item_categories = mask_object(item)
            result.append(masked)
            count += item_count
            categories.extend(item_categories)
        return result, count, categories
    if isinstance(value, dict):
        result_dict: dict[str, Any] = {}
        count = 0
        categories: list[str] = []
        for key, item in value.items():
            masked, item_count, item_categories = mask_object(item)
            result_dict[key] = masked
            count += item_count
            categories.extend(item_categories)
        return result_dict, count, categories
    return value, 0, []


def output_guardrail(report: dict[str, Any]) -> dict[str, Any]:
    masked, count, categories = mask_object(report)
    serialized = json.dumps(masked, ensure_ascii=False)

    secret_hits = [pattern.pattern for pattern in SECRET_PATTERNS if pattern.search(serialized)]
    if secret_hits:
        return {
            "valid": False,
            "report": None,
            "redactions": count,
            "categories": categories,
            "feedback": "Output contains a secret-like pattern and was blocked.",
        }

    try:
        validated = AuditReport.model_validate(masked)
    except ValidationError as exc:
        return {
            "valid": False,
            "report": None,
            "redactions": count,
            "categories": categories,
            "feedback": f"Output schema validation failed: {exc.errors(include_url=False)}",
        }

    validated.pii_redactions = count
    return {
        "valid": True,
        "report": validated.model_dump(mode="json"),
        "redactions": count,
        "categories": categories,
        "feedback": "",
    }
