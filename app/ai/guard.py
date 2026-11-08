"""Критическая валидация AI-вывода: покрытие вопроса, поддержка утверждений, уровень доверия.

Главный принцип из вакансии: любой результат LLM проходит обязательную проверку аналитиком,
поэтому каждый ответ возвращает собственные метрики достоверности.
"""

from __future__ import annotations

import re

from .text import normalize, sentences, stems

MIN_SUPPORT = 0.34
CLAIM_SPLIT = re.compile(r"(?:[.;]\s+|\n[-–•]\s*)")


def coverage(query: str, context: str) -> float:
    terms = set(stems(query))
    return round(len(terms & set(stems(context))) / max(len(terms), 1), 3)


def level(score: float) -> str:
    return "high" if score >= 4.0 else "medium" if score >= 1.5 else "low"


def confidence(hits: list[dict]) -> dict:
    top = hits[0]["score"] if hits else 0.0
    return {"top_score": round(top, 2), "label": level(top), "sources": len(hits)}


def claim_support(claim: str, context: str) -> dict:
    terms = set(stems(claim))
    return {"claim": normalize(claim), "support": share(terms, context), "evidence": sorted(terms & set(stems(context)))[:6]}


def share(terms: set[str], context: str) -> float:
    return round(len(terms & set(stems(context))) / max(len(terms), 1), 2)


def split_claims(text: str) -> list[str]:
    return [c.strip() for c in CLAIM_SPLIT.split(text) if len(c.strip()) > 12]


def audit(claims: list[str], context: str) -> dict:
    rows = [claim_support(c, context) for c in claims]
    return {"claims": rows, "unsupported": [r["claim"] for r in rows if r["support"] < MIN_SUPPORT], "score": round(sum(r["support"] for r in rows) / max(len(rows), 1), 2)}


def grounded_claims(text: str, context: str) -> list[str]:
    report = audit(split_claims(text), context)
    return [row["claim"] for row in report["claims"] if row["support"] >= MIN_SUPPORT]


def verify(text: str, context: str, hits: list[dict]) -> dict:
    report = audit(split_claims(text), context)
    return {"coverage": coverage(text, context), "confidence": confidence(hits), **report, "verdict": "принять" if report["score"] >= 0.5 else "перепроверить вручную"}


def evidence_lines(context: str, query: str, limit: int = 3) -> list[str]:
    ranked = sorted(sentences(context), key=lambda s: len(set(stems(s)) & set(stems(query))), reverse=True)
    return [normalize(s) for s in ranked[:limit] if len(s) > 15]
