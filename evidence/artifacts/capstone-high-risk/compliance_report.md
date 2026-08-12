# ContractGuard AI Compliance Report

**Report ID:** CGA-capstone-high-risk  
**Thread ID:** capstone-high-risk  
**Generated:** 2026-08-12T20:21:44.713989+00:00  
**Vendor:** Falcon Cloud International LLC  
**Contract value:** SAR 750,000.00  
**Risk:** CRITICAL (99/100)  
**Approval:** approved  

## Executive Summary

The multi-agent audit identified 7 compliance finding(s) and assigned a CRITICAL risk rating of 99/100. The result was produced from clause extraction, policy retrieval, specialist review, security routing, and output validation rather than a single prompt.

## Compliance Findings

| ID | Severity | Topic | Finding | Policy reference |
|---|---|---|---|---|
| F-01 | HIGH | data protection | Unrestricted cross-border data transfer | Data Protection Policy — Saudi Data Residency |
| F-02 | HIGH | data protection | Subprocessor changes lack customer consent | Data Protection Policy — Saudi Data Residency |
| F-03 | HIGH | data protection | Breach notification is missing or slower than policy | Data Protection Policy — Saudi Data Residency |
| F-04 | MEDIUM | payment | Accelerated payment terms | Procurement Policy — Payment Terms |
| F-05 | HIGH | liability | Liability cap is below corporate minimum | Legal Contracting Standard — Liability and Indemnity |
| F-06 | MEDIUM | termination | Termination and renewal terms are restrictive | Legal Contracting Standard — Termination |
| F-07 | HIGH | payment | High-value procurement requires human approval | Procurement Policy — Payment Terms |

## Recommendations

1. Require Saudi data residency or a documented transfer mechanism and prior written approval.
2. Add prior notification, objection rights, and flow-down security obligations for subprocessors.
3. Require notification within 24 hours of suspected or confirmed breach discovery.
4. Change payment terms to Net 30 or longer and condition payment on accepted deliverables.
5. Increase the vendor liability cap to at least twelve months of fees, with carve-outs for privacy and security.
6. Add termination for convenience on 30 days' notice and limit automatic renewal to one-year periods.
7. Route the contract to Procurement and Legal for explicit approval before signature.

## Human Approval Record

Approved conditionally after Legal confirmed remediation of all high-severity findings.

## Evidence and Data Protection

- Policy evidence records: 14
- PII items masked: 3

## Agent Handoff Trace

- Coordinator Agent → Document Analyst Agent: Plan-and-Execute plan created with seven bounded steps.
- Document Analyst Agent → Policy Research Agent: Extracted 9 clauses and contract metadata.
- Policy Research Agent → Coordinator Agent: Policy tool failed; requesting graph retry.
- Policy Research Agent → Compliance Analyst Agent: Retrieved 12 policy evidence records.
- Compliance Analyst Agent → Quality Reviewer Agent: Generated 7 compliance findings from contract clauses and policy evidence.
- Quality Reviewer Agent → Coordinator Agent: Evidence coverage score is 50%; re-planning targeted research.
- Policy Research Agent → Compliance Analyst Agent: Retrieved 14 policy evidence records.
- Compliance Analyst Agent → Quality Reviewer Agent: Generated 7 compliance findings from contract clauses and policy evidence.
- Quality Reviewer Agent → Coordinator Agent: Evidence coverage score is 100%; quality gate passed.
- Security Reviewer Agent → Coordinator Agent: Risk classified as CRITICAL (99/100). Human approval required.
- Report Writer Agent → Output Guardian Agent: Report draft revision 0 is ready for validation.
- Output Guardian Agent → Report Writer Agent: Output schema validation failed: [{'type': 'missing', 'loc': ('recommendations',), 'msg': 'Field required', 'input': {'report_id': 'CGA-capstone-high-risk', 'thread_id': 'capstone-high-risk', 'generated_at': '2026-08-12T20:21:44.705650+00:00', 'vendor_name': 'Falcon Cloud International LLC', 'contract_value_sar': 750000.0, 'executive_summary': 'The multi-agent audit identified 7 compliance finding(s) and assigned a CRITICAL risk rating of 99/100. The result was produced from clause extraction, policy retrieval, specialist review, security routing, and output validation rather than a single prompt.', 'risk_score': 99, 'risk_level': 'CRITICAL', 'findings': [{'finding_id': 'F-01', 'topic': 'data_protection', 'title': 'Unrestricted cross-border data transfer', 'severity': 'high', 'contract_excerpt': 'the vendor may store and process all customer data outside the kingdom of saudi arabia in any jurisdiction and in global locations selected at its discretion. the vendor may appoint or replace any subprocessor without notice and without customer consent. personal data may includ…', 'policy_reference': 'Data Protection Policy — Saudi Data Residency', 'recommendation': 'Require Saudi data residency or a documented transfer mechanism and prior written approval.', 'confidence': 0.92}, {'finding_id': 'F-02', 'topic': 'data_protection', 'title': 'Subprocessor changes lack customer consent', 'severity': 'high', 'contract_excerpt': 'the vendor may store and process all customer data outside the kingdom of saudi arabia in any jurisdiction and in global locations selected at its discretion. the vendor may appoint or replace any subprocessor without notice and without customer consent. personal data may includ…', 'policy_reference': 'Data Protection Policy — Saudi Data Residency', 'recommendation': 'Add prior notification, objection rights, and flow-down security obligations for subprocessors.', 'confidence': 0.92}, {'finding_id': 'F-03', 'topic': 'data_protection', 'title': 'Breach notification is missing or slower than policy', 'severity': 'high', 'contract_excerpt': 'the vendor may store and process all customer data outside the kingdom of saudi arabia in any jurisdiction and in global locations selected at its discretion. the vendor may appoint or replace any subprocessor without notice and without customer consent. personal data may includ…', 'policy_reference': 'Data Protection Policy — Saudi Data Residency', 'recommendation': 'Require notification within 24 hours of suspected or confirmed breach discovery.', 'confidence': 0.88}, {'finding_id': 'F-04', 'topic': 'payment', 'title': 'Accelerated payment terms', 'severity': 'medium', 'contract_excerpt': 'vendor cloud services agreement vendor: falcon cloud international llc contract value: sar 750,000 customer contact: [REDACTED_EMAIL], [REDACTED_PHONE], national id [REDACTED_NATIONAL_ID] invoices are payable within 15 days of issue, whether or not the relevant deliverables have been…', 'policy_reference': 'Procurement Policy — Payment Terms', 'recommendation': 'Change payment terms to Net 30 or longer and condition payment on accepted deliverables.', 'confidence': 0.92}, {'finding_id': 'F-05', 'topic': 'liability', 'title': 'Liability cap is below corporate minimum', 'severity': 'high', 'contract_excerpt': "the vendor's aggregate liability is capped at fees paid in the preceding one month. the cap applies to privacy, confidentiality, and security incidents.", 'policy_reference': 'Legal Contracting Standard — Liability and Indemnity', 'recommendation': 'Increase the vendor liability cap to at least twelve months of fees, with carve-outs for privacy and security.', 'confidence': 0.92}, {'finding_id': 'F-06', 'topic': 'termination', 'title': 'Termination and renewal terms are restrictive', 'severity': 'medium', 'contract_excerpt': 'the agreement renews automatically for three years. the customer may terminate only for uncured material breach after 90 days and has no termination-for-convenience right.', 'policy_reference': 'Legal Contracting Standard — Termination', 'recommendation': "Add termination for convenience on 30 days' notice and limit automatic renewal to one-year periods.", 'confidence': 0.9}, {'finding_id': 'F-07', 'topic': 'payment', 'title': 'High-value procurement requires human approval', 'severity': 'high', 'contract_excerpt': 'Contract Value: SAR 750,000.00', 'policy_reference': 'Procurement Policy — Payment Terms', 'recommendation': 'Route the contract to Procurement and Legal for explicit approval before signature.', 'confidence': 1.0}], 'approval_status': 'approved', 'approval_comment': 'Approved conditionally after Legal confirmed remediation of all high-severity findings.', 'evidence_count': 14, 'pii_redactions': 0, 'agent_trace_summary': ['Input Security Agent → Coordinator Agent: Input guardrail passed; execution may proceed.', 'Coordinator Agent → Document Analyst Agent: Plan-and-Execute plan created with seven bounded steps.', 'Document Analyst Agent → Policy Research Agent: Extracted 9 clauses and contract metadata.', 'Policy Research Agent → Coordinator Agent: Policy tool failed; requesting graph retry.', 'Policy Research Agent → Compliance Analyst Agent: Retrieved 12 policy evidence records.', 'Compliance Analyst Agent → Quality Reviewer Agent: Generated 7 compliance findings from contract clauses and policy evidence.', 'Quality Reviewer Agent → Coordinator Agent: Evidence coverage score is 50%; re-planning targeted research.', 'Policy Research Agent → Compliance Analyst Agent: Retrieved 14 policy evidence records.', 'Compliance Analyst Agent → Quality Reviewer Agent: Generated 7 compliance findings from contract clauses and policy evidence.', 'Quality Reviewer Agent → Coordinator Agent: Evidence coverage score is 100%; quality gate passed.', 'Security Reviewer Agent → Coordinator Agent: Risk classified as CRITICAL (99/100). Human approval required.']}}]
