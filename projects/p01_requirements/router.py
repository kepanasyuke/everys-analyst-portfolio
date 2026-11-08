"""P01 — маршруты генерации критериев приёмки."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from projects.p01_requirements.logic import build

router = APIRouter(prefix="/api/p01", tags=["P01 requirements"])

EXAMPLES = [
    "En tant que pharmacien je veux délivrer une ordonnance partiellement afin de ne pas bloquer le patient",
    "Как фармацевт я хочу видеть остаток препарата при продаже, чтобы не обещать пациенту отсутствующий товар",
    "En tant que titulaire je veux valider les remises au-delà du seuil afin de protéger la marge",
]


class Story(BaseModel):
    story: str = Field(min_length=3, max_length=4000)
    limit: int = Field(default=5, ge=1, le=10)


@router.get("/examples")
def examples() -> dict:
    return {"examples": EXAMPLES}


@router.post("/generate")
def generate(payload: Story) -> dict:
    return build(payload.story, payload.limit)
