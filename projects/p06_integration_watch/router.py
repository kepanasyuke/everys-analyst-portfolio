"""P06 — маршруты Integration Watch."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from projects.p06_integration_watch.logic import SOAP_SAMPLE, demo_targets, run, soap_check

router = APIRouter(prefix="/api/p06", tags=["P06 integration"])


class Target(BaseModel):
    url: str = Field(min_length=8, max_length=2000)
    label: str = Field(default="", max_length=120)


class ProbeRequest(BaseModel):
    targets: list[Target] = Field(default_factory=list)
    simulate: bool = True


class SoapEnvelope(BaseModel):
    xml: str = Field(min_length=10, max_length=20000)


@router.get("/targets")
def targets() -> dict:
    return {"targets": demo_targets(), "soap_sample": SOAP_SAMPLE}


@router.post("/probe")
def probe_targets(payload: ProbeRequest) -> dict:
    return run([t.model_dump() for t in payload.targets] or None, payload.simulate)


@router.post("/soap")
def soap(payload: SoapEnvelope) -> dict:
    return soap_check(payload.xml)
