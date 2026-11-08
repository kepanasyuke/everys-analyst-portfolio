"""P07 — маршруты Release Gate."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from projects.p07_release_gate.logic import DEFAULT_STATUS, assess, catalog

router = APIRouter(prefix="/api/p07", tags=["P07 release"])


class GateStatus(BaseModel):
    id: str
    status: str = Field(pattern="^(done|warn|fail)$")


class Assessment(BaseModel):
    version: str = Field(default="2026.1", max_length=32)
    gates: list[GateStatus] = Field(default_factory=list)


@router.get("/catalog")
def gates() -> dict:
    return {"gates": catalog(), "default_status": DEFAULT_STATUS}


@router.post("/assess")
def assess_release(payload: Assessment) -> dict:
    statuses = {g.id: g.status for g in payload.gates} or DEFAULT_STATUS
    return assess(statuses, payload.version)
