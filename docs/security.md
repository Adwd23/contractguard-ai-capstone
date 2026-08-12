# Security Model and Penetration Evidence

## Threat model

ContractGuard processes untrusted user instructions and contract documents. Threats
include direct prompt injection, indirect instructions embedded in documents, sensitive
information leakage, secret leakage, dangerous/unknown tool calls, retry loops, oversized
files, and unauthorized continuation of high-risk work.

## Enforced controls

- Prompt-injection patterns are enforced before the tool registry is reachable.
- Uploaded TXT/Markdown/PDF content is previewed as untrusted input for the guardrail.
- Tool names are allow-listed in `ToolRegistry`; arguments must pass Pydantic validation.
- Contract files are limited to 10 MB and supported extensions only.
- Loop counters and a global graph-step ceiling prevent unbounded execution.
- Output is recursively PII-masked and then schema-validated.
- High-risk/value work pauses and can resume only with an explicit `approve` or `reject`
  decision and approver identity.
- API keys are environment variables and excluded by `.gitignore`.
- JSONL audit events and checkpoint history support investigation.

## Demonstrated attack

The file `data/samples/prompt_injection_contract.txt` contains an instruction to ignore
previous instructions, reveal the system prompt, and override policy. The executed demo
produces `evidence/01_prompt_injection_blocked.json` with:

- terminal status `blocked`;
- matched threat patterns and a block reason;
- zero tool calls;
- graph path `received -> guardrailed -> blocked`.

## Demonstrated data protection

The high-risk contract contains an email address, Saudi phone number, and Saudi national
ID. They can exist in internal analysis state but are recursively masked before the
validated report is created. `pii_redactions >= 3` is asserted, and the raw values are
asserted absent from final Markdown.
