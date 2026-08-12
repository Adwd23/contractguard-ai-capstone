#!/usr/bin/env python3
"""Verify the Docker Compose API stores a real artifact in the MinIO/S3 backend."""
from __future__ import annotations

import json
import os
from pathlib import Path
import time
from uuid import uuid4

import httpx
from minio import Minio

ROOT = Path(__file__).resolve().parents[1]
API_BASE = os.getenv("CONTRACTGUARD_SMOKE_API", "http://127.0.0.1:8000")
MINIO_ENDPOINT = os.getenv("CONTRACTGUARD_SMOKE_MINIO", "127.0.0.1:9000")
MINIO_USER = os.getenv("MINIO_ROOT_USER", "contractguard")
MINIO_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "contractguard-change-me")
API_KEY = os.getenv("CONTRACTGUARD_API_KEY", "")
BUCKET = os.getenv("MINIO_BUCKET", "contractguard-reports")


def wait_for_api() -> None:
    last_error = ""
    for _ in range(90):
        try:
            response = httpx.get(f"{API_BASE}/health", timeout=2.0)
            if response.status_code == 200:
                return
            last_error = f"HTTP {response.status_code}"
        except httpx.HTTPError as exc:
            last_error = str(exc)
        time.sleep(2)
    raise RuntimeError(f"ContractGuard API did not become healthy: {last_error}")


def main() -> int:
    wait_for_api()
    thread_id = f"docker-minio-{uuid4().hex[:10]}"
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    response = httpx.post(
        f"{API_BASE}/audits",
        headers=headers,
        json={
            "thread_id": thread_id,
            "request_text": "Audit this contract and persist the report in MinIO.",
            "contract_path": "/app/data/samples/vendor_contract_low_risk.txt",
            "flags": {},
        },
        timeout=120.0,
    )
    response.raise_for_status()
    state = response.json()
    if state.get("status") != "completed":
        raise RuntimeError(f"Audit did not complete: {state.get('errors')}")
    if state.get("storage_backend") != "minio-s3":
        raise RuntimeError(f"Expected minio-s3, received {state.get('storage_backend')!r}")

    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_USER,
        secret_key=MINIO_PASSWORD,
        secure=False,
    )
    object_name = f"{thread_id}/compliance_report.md"
    metadata_name = f"{thread_id}/run_metadata.json"
    report_stat = client.stat_object(BUCKET, object_name)
    metadata_stat = client.stat_object(BUCKET, metadata_name)

    evidence = {
        "project": "ContractGuard AI",
        "status": state["status"],
        "thread_id": thread_id,
        "storage_backend": state["storage_backend"],
        "artifact_uri": state["artifact_uri"],
        "bucket": BUCKET,
        "report_object": object_name,
        "report_bytes": report_stat.size,
        "metadata_object": metadata_name,
        "metadata_bytes": metadata_stat.size,
        "verified_via_s3_sdk": True,
    }
    output = ROOT / "evidence" / "07_minio_docker_smoke.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
