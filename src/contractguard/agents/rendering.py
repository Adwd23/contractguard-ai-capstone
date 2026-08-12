"""Rendering helper kept separate from specialist agent classes."""
from __future__ import annotations

from typing import Any

def render_report_markdown(report: dict[str, Any]) -> str:
    findings = report.get("findings", [])
    rows = [
        "| ID | Severity | Topic | Finding | Policy reference |",
        "|---|---|---|---|---|",
    ]
    for finding in findings:
        rows.append(
            "| {id} | {severity} | {topic} | {title} | {policy} |".format(
                id=finding["finding_id"],
                severity=finding["severity"].upper(),
                topic=finding["topic"].replace("_", " "),
                title=finding["title"].replace("|", "/"),
                policy=finding["policy_reference"].replace("|", "/"),
            )
        )
    recommendations = "\n".join(f"{index}. {item}" for index, item in enumerate(report["recommendations"], 1))
    trace = "\n".join(f"- {item}" for item in report.get("agent_trace_summary", []))
    findings_table = "\n".join(rows) if findings else "No policy deviations were detected."
    finding_details = "\n\n".join(
        (
            f"### {item['finding_id']} — {item['title']}\n\n"
            f"- **Severity:** {item['severity'].upper()}\n"
            f"- **Topic:** {item['topic'].replace('_', ' ')}\n"
            f"- **Masked contract excerpt:** {item['contract_excerpt']}\n"
            f"- **Policy reference:** {item['policy_reference']}\n"
            f"- **Recommendation:** {item['recommendation']}"
        )
        for item in findings
    )
    return f"""# ContractGuard AI Compliance Report

**Report ID:** {report['report_id']}  
**Thread ID:** {report['thread_id']}  
**Generated:** {report['generated_at']}  
**Vendor:** {report['vendor_name']}  
**Contract value:** SAR {report['contract_value_sar']:,.2f}  
**Risk:** {report['risk_level']} ({report['risk_score']}/100)  
**Approval:** {report['approval_status']}  

## Executive Summary

{report['executive_summary']}

## Compliance Findings

{findings_table}

## Detailed Findings and Masked Evidence

{finding_details or 'No detailed findings.'}

## Recommendations

{recommendations}

## Human Approval Record

{report.get('approval_comment') or 'No human comment was supplied.'}

## Evidence and Data Protection

- Policy evidence records: {report['evidence_count']}
- PII items masked: {report['pii_redactions']}

## Agent Handoff Trace

{trace or '- No messages recorded.'}
"""
