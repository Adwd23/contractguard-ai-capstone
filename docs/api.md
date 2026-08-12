# API Reference

Run locally:

```bash
uvicorn contractguard.api:app --host 0.0.0.0 --port 8000
```

## `POST /audits`

Starts a graph. Supply either `contract_path` or `contract_text`.

```json
{
  "thread_id": "vendor-2026-001",
  "request_text": "Audit this contract against corporate policy.",
  "contract_path": "/app/data/samples/vendor_contract_high_risk.txt",
  "flags": {}
}
```

Possible terminal/pause statuses: `blocked`, `awaiting_approval`, `completed`, `failed`.

## `GET /audits/{thread_id}`

Returns the latest durable checkpoint, current node, and complete shared state.

## `GET /audits/{thread_id}/history`

Returns ordered checkpoint metadata for replay/audit.

## `POST /audits/{thread_id}/resume`

Resumes only a thread paused at `awaiting_approval`.

```json
{
  "decision": "approve",
  "comment": "Approved after Legal review.",
  "approver": "legal.manager"
}
```

## Operational endpoints

- `GET /health`
- `GET /graph`
- `GET /metrics`
