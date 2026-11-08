"""P02 — маршруты SQL Lab."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from projects.p02_sql_lab.logic import INTENTS, query, safe_run, schema

router = APIRouter(prefix="/api/p02", tags=["P02 sql"])

EXAMPLES = [
    "Топ-10 препаратов по выручке",
    "Средний чек по городам",
    "Влияние скидки на чек: что даёт remise 20%",
    "Позиции ниже порога пополнения",
    "Доля отмен по статусам продаж",
    "Выручка по месяцам",
]


class Question(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class RawSql(BaseModel):
    sql: str = Field(min_length=6, max_length=2000)


@router.get("/examples")
def examples() -> dict:
    return {"examples": EXAMPLES, "intents": [{"name": k, "label": v["label"]} for k, v in INTENTS.items()], "schema": schema()}


@router.post("/query")
def ask(payload: Question) -> dict:
    return query(payload.question)


@router.post("/raw")
def raw(payload: RawSql) -> dict:
    return safe_run(payload.sql)
