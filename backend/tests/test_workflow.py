"""End-to-end authorization and CEDAR multi-lender decisions on isolated SQLite DB."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.db import Base, get_db
from app.main import create_app
from app import models
from app.security import hash_password

@pytest.fixture
def env(monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "jwt_secret", "test-secret-for-cedar-integration-at-least-32-chars")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin = models.User(email="admin@example.test", password_hash=hash_password("testpassword123"),
                            role="platform_admin")
        reviewer = models.User(email="reviewer@example.test", password_hash=hash_password("testpassword123"),
                               role="reviewer")
        db.add_all([admin, reviewer])
        db.commit()
    app = create_app()
    def test_db():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = test_db
    with TestClient(app) as client:
        yield client
    engine.dispose()

def login(client, email, password="testpassword123"):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": "Bearer " + resp.json()["access_token"]}

def post(client, path, payload, headers):
    resp = client.post(path, json=payload, headers=headers)
    assert resp.status_code in (200, 201), f"{path}: {resp.status_code} {resp.text}"
    return resp.json()

def test_workflow_and_incremental_recompute(env):
    c = env
    admin = login(c, "admin@example.test")
    borrower = post(c, "/api/v1/auth/register",
                    {"email": "borrower@example.test", "password": "testpassword123",
                     "legal_name": "Green Farmers FPO", "borrower_type": "fpo"}, {})
    user = login(c, "borrower@example.test")
    assert borrower["role"] == "borrower"
    assert c.get("/api/v1/applications", headers=admin).status_code == 200
    assert c.post("/api/v1/admin/lenders", json={"name": "Illegal"}, headers=user).status_code == 403

    a = post(c, "/api/v1/admin/lenders", {"name": "Synthetic Lender A"}, admin)
    b = post(c, "/api/v1/admin/lenders", {"name": "Synthetic Lender B"}, admin)
    product = post(c, f"/api/v1/admin/lenders/{a['id']}/products",
                   {"name": "Demo Crop Loan", "min_amount": 100000, "max_amount": 1000000, "apr": 11}, admin)
    pa = post(c, f"/api/v1/admin/lenders/{a['id']}/policies",
              {"rules": [{"field_key": "turnover", "operator": "gte", "target": 1500000}]}, admin)
    pb = post(c, f"/api/v1/admin/lenders/{b['id']}/policies",
              {"rules": [{"field_key": "turnover", "operator": "gte", "target": 1000000}]}, admin)
    app = post(c, "/api/v1/applications",
               {"requested_amount": 500000, "loan_purpose": "seeds and fertilizer"}, user)
    f = post(c, f"/api/v1/applications/{app['id']}/evidence",
             {"key": "turnover", "value": 1300000, "candidates": [1800000]}, user)
    initial = post(c, f"/api/v1/applications/{app['id']}/evaluate", {}, admin)["decisions"]
    a_initial = next(x for x in initial if x["lender_id"] == a["id"])
    b_initial = next(x for x in initial if x["lender_id"] == b["id"])
    assert (a_initial["decision"], a_initial["stable"]) == ("FAIL", False)
    assert (b_initial["decision"], b_initial["stable"]) == ("PASS", True)
    assert c.post(f"/api/v1/applications/{app['id']}/offers",
                  json={"evaluation_id": b_initial["id"], "product_id": product["id"]},
                  headers=admin).status_code == 422  # product belongs to different lender
    assert c.post(f"/api/v1/applications/{app['id']}/offers",
                  json={"evaluation_id": a_initial["id"], "product_id": product["id"]},
                  headers=admin).status_code == 409

    review = post(c, f"/api/v1/applications/{app['id']}/schedule-review", {}, admin)
    assert review["created_task_ids"]
    reviewer = login(c, "reviewer@example.test")
    revised = post(c, f"/api/v1/review/tasks/{review['created_task_ids'][0]}/verify",
                   {"value": 1800000}, reviewer)
    assert revised["verified_version"] == 2
    assert any(x["decision"] == "PASS" for x in revised["recomputed"])
    history = c.get(f"/api/v1/applications/{app['id']}/evidence/{f['id']}/history", headers=user).json()
    assert len(history) == 2 and history[-1]["verified"] is True
    all_evals = c.get(f"/api/v1/applications/{app['id']}/evaluations", headers=user).json()
    assert len(all_evals) == 4 and sum(x["current"] for x in all_evals) == 2
    assert next(x for x in all_evals if x["policy_id"] == pa["id"] and x["current"])["decision"] == "PASS"
    assert next(x for x in all_evals if x["policy_id"] == pb["id"] and x["current"])["decision"] == "PASS"
    eligible = next(x for x in all_evals if x["policy_id"] == pa["id"] and x["current"])
    offer = post(c, f"/api/v1/applications/{app['id']}/offers",
                 {"evaluation_id": eligible["id"], "product_id": product["id"]}, admin)
    assert offer["simulation"] is True
    agreement = c.get(f"/api/v1/offers/{offer['id']}/agreement", headers=user).json()
    assert agreement["legally_binding"] is False
    loan = post(c, f"/api/v1/offers/{offer['id']}/accept", {}, user)
    disb = post(c, f"/api/v1/loans/{loan['loan_id']}/mock-disburse", {}, admin)
    assert disb["money_transferred"] is False
    payment = post(c, f"/api/v1/loans/{loan['loan_id']}/mock-repayments", {"amount": 10000}, admin)
    assert payment["money_moved"] is False
    util = post(c, f"/api/v1/loans/{loan['loan_id']}/utilization",
                {"category": "seeds", "amount": 12000, "note": "Demo invoice pending"}, user)
    assert util["fraud_determination"] is None
    assert c.get(f"/api/v1/loans/{loan['loan_id']}/utilization", headers=user).status_code == 200

def test_anonymous_and_borrower_separation(env):
    c = env
    assert c.get("/api/v1/applications").status_code in (401,403)
    post(c, "/api/v1/auth/register", {"email": "alice@example.test", "password": "testpassword123",
         "legal_name": "Alice Farmers"}, {})
    post(c, "/api/v1/auth/register", {"email": "bob@example.test", "password": "testpassword123",
         "legal_name": "Bob Farmers"}, {})
    alice = login(c, "alice@example.test")
    bob = login(c, "bob@example.test")
    app = post(c, "/api/v1/applications", {"requested_amount": 500000, "loan_purpose": "seed purchase"}, alice)
    assert c.get(f"/api/v1/applications/{app['id']}", headers=bob).status_code == 403
    assert c.post(f"/api/v1/applications/{app['id']}/evidence",
                  headers=bob, json={"key": "turnover", "value": 1000000}).status_code == 403
