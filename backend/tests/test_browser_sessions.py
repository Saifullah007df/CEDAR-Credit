"""Browser sessions survive page reload and require CSRF on state-changing requests."""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.db import Base, get_db
from app.main import create_app
from app.models import User, Borrower
from app.security import hash_password
from app.core.config import get_settings

def test_cookie_session_and_csrf(monkeypatch):
    monkeypatch.setattr(get_settings(), "jwt_secret", "test-cookie-secret-at-least-thirty-two-characters")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="browser@example.test", password_hash=hash_password("mystrongpass123"),
                    role="borrower")
        db.add(user)
        db.flush()
        db.add(Borrower(user_id=user.id, legal_name="Demo Farm", borrower_type="fpo"))
        db.commit()
    app = create_app()
    def test_db():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = test_db
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={"email":"browser@example.test",
                                                       "password":"mystrongpass123"})
        assert login.status_code == 200
        assert "httponly" in login.headers["set-cookie"].lower()
        assert "samesite=strict" in login.headers["set-cookie"].lower()
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        csrf = me.json()["csrf_token"]
        assert csrf
        # Missing and incorrect CSRF are rejected.
        payload = {"requested_amount": 500000, "loan_purpose": "Seed purchase"}
        assert client.post("/api/v1/applications", json=payload).status_code == 403
        assert client.post("/api/v1/applications", json=payload,
                           headers={"X-CSRF-Token": "wrong"}).status_code == 403
        assert client.post("/api/v1/applications", json=payload,
                           headers={"X-CSRF-Token": csrf}).status_code == 201
        # Cookie remains available across independent requests and can be explicitly revoked.
        assert client.get("/api/v1/applications").status_code == 200
        assert client.post("/api/v1/auth/logout").status_code == 200
        assert client.get("/api/v1/auth/me").status_code == 401
    engine.dispose()
