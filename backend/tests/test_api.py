"""Run with: cd backend && pytest -q"""

from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def test_health_is_live_and_versioned():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "service": "cedar-credit-api",
        "status": "ok",
        "version": "0.1.0",
    }


def test_capabilities_distinguish_implemented_from_planned():
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["current_phase"] == 1
    assert len(body["capabilities"]) == 10
    assert [c["status"] for c in body["capabilities"]].count("implemented") == 1
    assert [c["status"] for c in body["capabilities"]].count("planned") == 9
    assert body["capabilities"][0]["id"] == "foundation"
    assert body["capabilities"][3]["id"] == "rg03"


def test_architecture_declares_planned_services():
    response = client.get("/api/v1/architecture")
    assert response.status_code == 200
    body = response.json()
    assert body["architecture"] == "modular monolith"
    assert len(body["layers"]) == 4
    assert body["layers"][2]["status"] == "planned"
    assert "Counterfactual Analyzer" in body["layers"][2]["modules"]


def test_openapi_contract_published():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/health" in paths
    assert "/api/v1/architecture" in paths


def test_unknown_api_route_returns_404():
    assert client.get("/api/v1/loans").status_code == 404
