"""Versioned informational endpoints for the Phase 1 scaffold."""

from fastapi import APIRouter

from app.api.schemas import ArchitectureResponse, CapabilitiesResponse, HealthResponse
from app.modules.catalog import ARCHITECTURE_LAYERS, CAPABILITIES

router = APIRouter(prefix="/api/v1", tags=["foundation"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(service="cedar-credit-api", status="ok", version="0.1.0")


@router.get("/capabilities", response_model=CapabilitiesResponse)
def capabilities() -> CapabilitiesResponse:
    return CapabilitiesResponse(
        project="CEDAR-Credit", current_phase=1, capabilities=list(CAPABILITIES)
    )


@router.get("/architecture", response_model=ArchitectureResponse)
def architecture() -> ArchitectureResponse:
    return ArchitectureResponse(
        version="phase-1", architecture="modular monolith", layers=list(ARCHITECTURE_LAYERS)
    )
