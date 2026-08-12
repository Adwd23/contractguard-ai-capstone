# ContractGuard AI Compliance Report

**Report ID:** CGA-capstone-high-risk  
**Thread ID:** capstone-high-risk  
**Generated:** 2026-08-12T21:37:21.667020+00:00  
**Vendor:** Falcon Cloud International LLC  
**Contract value:** SAR 750,000.00  
**Risk:** CRITICAL (100/100)  
**Approval:** approved  

## Executive Summary

The multi-agent audit identified 10 compliance finding(s) and assigned a CRITICAL risk rating of 100/100. The result was produced from clause extraction, policy retrieval, specialist review, security routing, and output validation rather than a single prompt.

## Compliance Findings

| ID | Severity | Topic | Finding | Policy reference |
|---|---|---|---|---|
| F-01 | HIGH | data protection | Unrestricted cross-border data transfer | Data Protection Policy — Saudi Data Residency |
| F-02 | HIGH | data protection | Subprocessor changes lack customer consent | Data Protection Policy — Saudi Data Residency |
| F-03 | HIGH | data protection | Breach notification is missing or slower than policy | Data Protection Policy — Saudi Data Residency |
| F-04 | HIGH | security | Security baseline is incomplete | Information Security Policy — Access Control |
| F-05 | MEDIUM | payment | Accelerated payment terms | Procurement Policy — Payment Terms |
| F-06 | HIGH | liability | Liability cap is below corporate minimum | Legal Contracting Standard — Liability and Indemnity |
| F-07 | MEDIUM | termination | Termination and renewal terms are restrictive | Legal Contracting Standard — Termination |
| F-08 | HIGH | governing law | Non-KSA governing law | Legal Contracting Standard — Governing Law |
| F-09 | MEDIUM | service levels | Service levels are below the enterprise standard | Service Level Standard — Service Credits |
| F-10 | HIGH | payment | High-value procurement requires human approval | Procurement Policy — Payment Terms |

## Detailed Findings and Masked Evidence

### F-01 — Unrestricted cross-border data transfer

- **Severity:** HIGH
- **Topic:** data protection
- **Masked contract excerpt:** the vendor may store and process all customer data outside the kingdom of saudi arabia in any jurisdiction and in global locations selected at its discretion. the vendor may appoint or replace any subprocessor without notice and without customer consent. personal data may includ…
- **Policy reference:** Data Protection Policy — Saudi Data Residency
- **Recommendation:** Require Saudi data residency or a documented transfer mechanism and prior written approval.

### F-02 — Subprocessor changes lack customer consent

- **Severity:** HIGH
- **Topic:** data protection
- **Masked contract excerpt:** the vendor may store and process all customer data outside the kingdom of saudi arabia in any jurisdiction and in global locations selected at its discretion. the vendor may appoint or replace any subprocessor without notice and without customer consent. personal data may includ…
- **Policy reference:** Data Protection Policy — Saudi Data Residency
- **Recommendation:** Add prior notification, objection rights, and flow-down security obligations for subprocessors.

### F-03 — Breach notification is missing or slower than policy

- **Severity:** HIGH
- **Topic:** data protection
- **Masked contract excerpt:** the vendor may store and process all customer data outside the kingdom of saudi arabia in any jurisdiction and in global locations selected at its discretion. the vendor may appoint or replace any subprocessor without notice and without customer consent. personal data may includ…
- **Policy reference:** Data Protection Policy — Saudi Data Residency
- **Recommendation:** Require notification within 24 hours of suspected or confirmed breach discovery.

### F-04 — Security baseline is incomplete

- **Severity:** HIGH
- **Topic:** security
- **Masked contract excerpt:** the vendor will use commercially reasonable security. no iso 27001 certification, encryption commitment, penetration-test report, or customer audit right is guaranteed.
- **Policy reference:** Information Security Policy — Access Control
- **Recommendation:** Require ISO 27001-equivalent controls, encryption in transit/at rest, audit rights, and annual testing.

### F-05 — Accelerated payment terms

- **Severity:** MEDIUM
- **Topic:** payment
- **Masked contract excerpt:** vendor cloud services agreement vendor: falcon cloud international llc contract value: sar 750,000 customer contact: [REDACTED_EMAIL], [REDACTED_PHONE], national id [REDACTED_NATIONAL_ID] invoices are payable within 15 days of issue, whether or not the relevant deliverables have been…
- **Policy reference:** Procurement Policy — Payment Terms
- **Recommendation:** Change payment terms to Net 30 or longer and condition payment on accepted deliverables.

### F-06 — Liability cap is below corporate minimum

- **Severity:** HIGH
- **Topic:** liability
- **Masked contract excerpt:** the vendor's aggregate liability is capped at fees paid in the preceding one month. the cap applies to privacy, confidentiality, and security incidents.
- **Policy reference:** Legal Contracting Standard — Liability and Indemnity
- **Recommendation:** Increase the vendor liability cap to at least twelve months of fees, with carve-outs for privacy and security.

### F-07 — Termination and renewal terms are restrictive

- **Severity:** MEDIUM
- **Topic:** termination
- **Masked contract excerpt:** the agreement renews automatically for three years. the customer may terminate only for uncured material breach after 90 days and has no termination-for-convenience right.
- **Policy reference:** Legal Contracting Standard — Termination
- **Recommendation:** Add termination for convenience on 30 days' notice and limit automatic renewal to one-year periods.

### F-08 — Non-KSA governing law

- **Severity:** HIGH
- **Topic:** governing law
- **Masked contract excerpt:** this agreement is governed by the laws of the state of delaware and disputes are subject to courts outside saudi arabia.
- **Policy reference:** Legal Contracting Standard — Governing Law
- **Recommendation:** Use the laws and courts of the Kingdom of Saudi Arabia unless Legal approves an exception.

### F-09 — Service levels are below the enterprise standard

- **Severity:** MEDIUM
- **Topic:** service levels
- **Masked contract excerpt:** the vendor targets 98.0 percent availability and provides no service credits.
- **Policy reference:** Service Level Standard — Service Credits
- **Recommendation:** Require at least 99.9% monthly availability, service credits, and chronic-failure termination rights.

### F-10 — High-value procurement requires human approval

- **Severity:** HIGH
- **Topic:** payment
- **Masked contract excerpt:** Contract Value: SAR 750,000.00
- **Policy reference:** Procurement Policy — Payment Terms
- **Recommendation:** Route the contract to Procurement and Legal for explicit approval before signature.

## Recommendations

1. Require Saudi data residency or a documented transfer mechanism and prior written approval.
2. Add prior notification, objection rights, and flow-down security obligations for subprocessors.
3. Require notification within 24 hours of suspected or confirmed breach discovery.
4. Require ISO 27001-equivalent controls, encryption in transit/at rest, audit rights, and annual testing.
5. Change payment terms to Net 30 or longer and condition payment on accepted deliverables.
6. Increase the vendor liability cap to at least twelve months of fees, with carve-outs for privacy and security.
7. Add termination for convenience on 30 days' notice and limit automatic renewal to one-year periods.
8. Use the laws and courts of the Kingdom of Saudi Arabia unless Legal approves an exception.
9. Require at least 99.9% monthly availability, service credits, and chronic-failure termination rights.
10. Route the contract to Procurement and Legal for explicit approval before signature.

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
- Compliance Analyst Agent → Quality Reviewer Agent: Generated 10 compliance findings from contract clauses and policy evidence.
- Quality Reviewer Agent → Coordinator Agent: Evidence coverage score is 50%; re-planning targeted research.
- Policy Research Agent → Compliance Analyst Agent: Retrieved 14 policy evidence records.
- Compliance Analyst Agent → Quality Reviewer Agent: Generated 10 compliance findings from contract clauses and policy evidence.
- Quality Reviewer Agent → Coordinator Agent: Evidence coverage score is 100%; quality gate passed.
- Security Reviewer Agent → Coordinator Agent: Risk classified as CRITICAL (100/100). Human approval required.
- Report Writer Agent → Output Guardian Agent: Report draft revision 0 is ready for validation.
- Output Guardian Agent → Report Writer Agent: Output schema validation failed: [{'location': 'recommendations', 'message': 'Field required', 'type': 'missing'}]
