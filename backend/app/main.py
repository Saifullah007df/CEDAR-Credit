"""FastAPI ASGI entrypoint. Apply Alembic migrations before using protected routes."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as foundation_router
from app.api.auth import router as identity_router
from app.api.marketplace import router as marketplace_router
from app.core.config import get_settings

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.3.0",
                  description="CEDAR-Credit research prototype. All financial activity is synthetic.")
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.allowed_origins,
        allow_credentials=True, allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )
    app.include_router(foundation_router)
    app.include_router(identity_router)
    app.include_router(marketplace_router)
    return app

app = create_app()
