from __future__ import annotations

from fastapi.testclient import TestClient

from contractguard.api import create_app


def test_fastapi_start_status_graph_metrics(isolated_settings) -> None:
    app = create_app(isolated_settings)
    path = isolated_settings.project_root / "data" / "samples" / "vendor_contract_low_risk.txt"
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200

        started = client.post(
            "/audits",
            json={
                "thread_id": "api-low",
                "request_text": "Audit this contract against all policies.",
                "contract_path": str(path),
                "flags": {},
            },
        )
        assert started.status_code == 201
        assert started.json()["status"] == "completed"

        status = client.get("/audits/api-low")
        assert status.status_code == 200
        assert status.json()["node"] == "completed"

        graph = client.get("/graph")
        assert graph.status_code == 200
        assert "policy_research -> policy_research (bounded tool retry)" in graph.json()["loops"]

        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert "contractguard_node_runs_total" in metrics.text


def test_optional_api_key_protects_audit_endpoints(isolated_settings) -> None:
    isolated_settings.api_key = "capstone-secret"
    app = create_app(isolated_settings)
    path = isolated_settings.project_root / "data" / "samples" / "vendor_contract_low_risk.txt"
    payload = {
        "thread_id": "api-auth",
        "request_text": "Audit this contract against all policies.",
        "contract_path": str(path),
        "flags": {},
    }
    with TestClient(app) as client:
        unauthorized = client.post("/audits", json=payload)
        assert unauthorized.status_code == 401

        authorized = client.post(
            "/audits",
            json=payload,
            headers={"X-API-Key": "capstone-secret"},
        )
        assert authorized.status_code == 201
        assert authorized.json()["status"] == "completed"


def test_api_rejects_path_traversal_thread_identifier(isolated_settings) -> None:
    app = create_app(isolated_settings)
    path = isolated_settings.project_root / "data" / "samples" / "vendor_contract_low_risk.txt"
    with TestClient(app) as client:
        response = client.post(
            "/audits",
            json={
                "thread_id": "../escape",
                "request_text": "Audit this contract against all policies.",
                "contract_path": str(path),
                "flags": {},
            },
        )
    assert response.status_code == 422
