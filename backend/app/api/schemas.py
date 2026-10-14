"""Strict contracts for Phase 1 informational endpoints."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class CapabilityStatus(StrEnum):
    IMPLEMENTED = "implemented"
    PLANNED = "planned"
    MOCKED = "mocked"


class Capability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    phase: int
    status: CapabilityStatus
    description: str


class HealthResponse(BaseModel):
    service: str
    status: str
    version: str


class CapabilitiesResponse(BaseModel):
    project: str
    current_phase: int
    capabilities: list[Capability]


class ArchitectureLayer(BaseModel):
    name: str
    modules: list[str]
    status: CapabilityStatus


class ArchitectureResponse(BaseModel):
    version: str
    architecture: str
    layers: list[ArchitectureLayer]
