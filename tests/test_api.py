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
        assert "researching -> researching (tool retry)" in graph.json()["loops"]

        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert "contractguard_node_runs_total" in metrics.text
