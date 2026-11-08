"""P03 — маршруты радара противоречий."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from projects.p03_conflicts.logic import related, scan

router = APIRouter(prefix="/api/p03", tags=["P03 conflicts"])


class ScanRequest(BaseModel):
    min_severity: Literal["high", "medium"] = "medium"


class Text(BaseModel):
    text: str = Field(min_length=3, max_length=2000)


@router.get("/scan")
def scan_default() -> dict:
    return scan()


@router.post("/scan")
def scan_filtered(payload: ScanRequest) -> dict:
    return scan(payload.min_severity)


@router.post("/related")
def related_items(payload: Text) -> dict:
    return {"related": related(payload.text)}
