# Security Model and Penetration Evidence

## Threat model

ContractGuard processes untrusted user instructions and contract documents. Threats
include direct or indirect prompt injection, sensitive-data leakage, secret leakage,
unauthorized tools, model-generated argument injection, path traversal, oversized input,
unbounded loops, and unauthorized continuation of high-risk work.

## Enforced controls

- Prompt-injection patterns are enforced before the function registry is reachable.
- Uploaded TXT/Markdown/PDF content is previewed as untrusted input for the guardrail.
- Contract paths are checked at both the service and tool layers against
  `CONTRACT_ALLOWED_ROOTS`; the default local root is `data/`.
- Request text, inline contracts, file paths, files, thread IDs, approval comments, and
  function arguments have explicit bounds.
- Thread IDs accept only safe characters, preventing artifact-directory traversal.
- Tool names are registered and each specialist has a separate runtime allow-list.
- Pydantic tool schemas use `extra="forbid"`, rejecting undeclared model-generated fields.
- Retry counters and a global graph-step ceiling prevent unbounded execution.
- Before optional external summary generation, raw contract excerpts are removed and PII
  is masked from the minimal context.
- Final output is recursively PII-masked, checked for secret-like patterns, and validated
  against a strict report schema.
- High-risk/value work pauses and can resume only with an explicit approve/reject decision
  and approver identity.
- Setting `CONTRACTGUARD_API_KEY` protects all `/audits` endpoints with `X-API-Key`.
- API keys are environment variables or an untracked `.env`; `.gitignore` excludes them.
- JSONL audit events, Prometheus metrics, and checkpoint history support investigation.
- The Docker API runs non-root with a read-only root filesystem, all Linux capabilities
  dropped, and `no-new-privileges` enabled.

## Demonstrated attack

`data/samples/prompt_injection_contract.txt` contains an instruction to ignore previous
instructions, reveal the system prompt, and override policy. The executed demonstration
produces `evidence/01_prompt_injection_blocked.json` with:

- terminal status `blocked`;
- matched threat patterns and a block reason;
- zero tool calls;
- graph path `received -> guardrailed -> blocked`.

## Demonstrated data protection

The synthetic high-risk contract contains an email address, Saudi phone number, and Saudi
national ID. They may exist in the internal educational checkpoint state, but they are
recursively masked before report validation and storage. The demonstration asserts at
least three redactions and verifies that raw values are absent from final Markdown.

A separate regression test proves that optional external summary generation receives no
`contract_excerpt` field and receives `[REDACTED_EMAIL]` rather than the raw address.

## Additional negative tests

The automated suite also proves:

- a specialist cannot call a function outside its allow-list;
- `/etc/hosts` cannot be read as a contract;
- unknown function arguments fail strict schema validation;
- `../escape` is rejected as a thread identifier;
- API-key-protected audit endpoints reject missing credentials;
- benign discussion of prompt-injection defenses is not falsely blocked.

The sample contracts and identities are fictional training data, not production records.
