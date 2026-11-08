"""P04 — маршруты генератора граничных сценариев."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from projects.p04_edge_cases.logic import generate, presets_all, sample_specs

router = APIRouter(prefix="/api/p04", tags=["P04 edge cases"])


class Spec(BaseModel):
    spec: str = Field(min_length=10, max_length=6000)


@router.get("/examples")
def examples() -> dict:
    return {"samples": sample_specs(), "presets": presets_all()}


@router.post("/generate")
def generate_cases(payload: Spec) -> dict:
    return generate(payload.spec)
