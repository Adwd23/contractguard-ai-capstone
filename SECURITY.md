# Security Policy

ContractGuard AI is an educational capstone and must not be used for real legal or
confidential contract processing without an independent production security review.

## Reporting a vulnerability

Do not open a public issue containing credentials, personal data, or exploit details.
Contact **Adwd23**, the repository owner and project implementer, privately through the
security-reporting method configured on the GitHub repository. Include the affected component, reproduction steps, impact, and a
minimal sanitized proof of concept.

## Supported version

The maintained capstone version is `1.2.x` on the `main` branch.

## Secret policy

Never commit `.env`, API keys, private keys, real contracts, or mutable checkpoint
databases. Run `python scripts/prepublish_check.py` before every public push.

For implementation details and residual risks, see [`docs/security.md`](docs/security.md).
