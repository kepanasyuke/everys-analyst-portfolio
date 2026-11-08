"""P05 — маршруты A/B Lab."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from projects.p05_ab_lab.logic import compute, plan, scenarios

router = APIRouter(prefix="/api/p05", tags=["P05 ab-test"])


class AbRequest(BaseModel):
    visitors_a: int = Field(ge=1, le=10_000_000)
    conversions_a: int = Field(ge=0, le=10_000_000)
    visitors_b: int = Field(ge=1, le=10_000_000)
    conversions_b: int = Field(ge=0, le=10_000_000)
    alpha: float = 0.05
    power: float = 0.8
    mde: float = Field(default=0.1, gt=0, le=5)
    days: int = Field(default=14, ge=1, le=365)


class PlanRequest(BaseModel):
    baseline: float = Field(gt=0, lt=1)
    mde: float = Field(gt=0, le=5)
    alpha: float = 0.05
    power: float = 0.8


@router.get("/scenarios")
def list_scenarios() -> dict:
    return {"scenarios": scenarios()}


@router.post("/test")
def test(payload: AbRequest) -> dict:
    return compute(payload.visitors_a, payload.conversions_a, payload.visitors_b, payload.conversions_b, payload.alpha, payload.power, payload.mde, payload.days)


@router.post("/plan")
def planning(payload: PlanRequest) -> dict:
    return plan(payload.baseline, payload.mde, payload.alpha, payload.power)
