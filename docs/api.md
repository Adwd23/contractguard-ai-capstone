# API Reference

Run locally:

```bash
python -m contractguard.server
```

Open `/docs` for the generated OpenAPI interface.

## Authentication

Authentication is optional for local grading. Set:

```dotenv
CONTRACTGUARD_API_KEY=replace_with_a_long_random_value
```

Then every `/audits` endpoint requires:

```http
X-API-Key: replace_with_a_long_random_value
```

`/health`, `/graph`, `/docs`, and `/metrics` remain operational endpoints. Place them
behind network controls or an API gateway in a real deployment.

## `POST /audits`

Starts the state graph. Supply either `contract_path` or `contract_text`.

```json
{
  "thread_id": "vendor-2026-001",
  "request_text": "Audit this contract against corporate policy.",
  "contract_path": "/app/data/samples/vendor_contract_high_risk.txt",
  "flags": {}
}
```

Validation and safety constraints:

- `thread_id`: 3–128 characters; letters, numbers, `.`, `_`, and `-` only;
- `request_text`: 3–20,000 characters;
- `contract_text`: at most 1,000,000 characters;
- `contract_path`: at most 4,096 characters and must be beneath
  `CONTRACT_ALLOWED_ROOTS`;
- files: PDF, TXT, or Markdown, at most 10 MB.

Possible pause/terminal statuses are `blocked`, `awaiting_approval`, `completed`,
`rejected`, and `failed`.

## `GET /audits/{thread_id}`

Returns the latest durable checkpoint, current node, and complete shared state.

## `GET /audits/{thread_id}/history`

Returns ordered checkpoint metadata for replay and audit.

## `POST /audits/{thread_id}/resume`

Resumes only a thread paused at `awaiting_approval`.

```json
{
  "decision": "approve",
  "comment": "Approved after Legal review.",
  "approver": "legal.manager"
}
```

A non-paused or unknown thread returns a conflict/not-found response.

## Operational endpoints

- `GET /health` — liveness response
- `GET /graph` — framework package/version, nodes, edges, branches, and loops
- `GET /metrics` — Prometheus exposition format
