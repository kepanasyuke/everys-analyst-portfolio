"""P08 — маршруты глоссария FR↔RU."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from projects.p08_glossary.logic import annotate, lookup, overview

router = APIRouter(prefix="/api/p08", tags=["P08 glossary"])


class AnnotateRequest(BaseModel):
    text: str = Field(min_length=3, max_length=4000)


@router.get("/overview")
def overview_terms() -> dict:
    return overview()


@router.get("/search")
def search(q: str = "", limit: int = 8) -> dict:
    return lookup(q, min(max(limit, 1), 30))


@router.post("/annotate")
def annotate_text(payload: AnnotateRequest) -> dict:
    return annotate(payload.text)
