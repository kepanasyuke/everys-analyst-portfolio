"""P08 — двуязычный глоссарий аптечного домена: поиск, аннотирование текста, пробелы терминологии."""

from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache

from app.ai.text import overlap, sentences, shorten, stem, stems, tokenize
from app.core.store import GLOSSARY, chunks

DOMAIN_LABELS = {
    "structure": "Структура и роли",
    "dispensation": "Выдача и рецепты",
    "remboursement": "Возмещение",
    "integration": "Интеграции",
    "stock": "Склад",
    "referentiel": "Справочник",
    "reglementation": "Регулирование",
    "qualite": "Качество",
    "caisse": "Касса",
    "pilotage": "Пилотирование",
    "analyse": "Анализ",
}


@lru_cache(maxsize=1)
def entries() -> tuple[dict, ...]:
    return tuple(json.loads(GLOSSARY.read_text(encoding="utf-8")))


def haystack(entry: dict) -> str:
    return " ".join([entry["fr"], entry["ru"], entry["def_fr"], entry["def_ru"], *entry.get("synonyms", [])])


def score(query: str, entry: dict) -> float:
    return round(min(1.0, overlap(stems(query), stems(haystack(entry))) + boost(query, entry)), 3)


def boost(query: str, entry: dict) -> float:
    names = {entry["fr"].lower(), entry["ru"].lower(), *[s.lower() for s in entry.get("synonyms", [])]}
    return 0.6 if query.strip().lower() in names else 0.0


def card(entry: dict) -> dict:
    return {"fr": entry["fr"], "ru": entry["ru"], "domain": entry["domain"], "domain_label": DOMAIN_LABELS.get(entry["domain"], entry["domain"]), "def_fr": entry["def_fr"], "def_ru": entry["def_ru"], "synonyms": entry.get("synonyms", []), "examples": entry.get("examples", []), "uses": occurrences(entry["fr"])}


def occurrences(term: str) -> int:
    return sum(1 for c in chunks() if term.lower() in c.text.lower())


def lookup(query: str, limit: int = 8) -> dict:
    ranked = sorted(({"score": score(query, e), **card(e)} for e in entries()), key=lambda r: r["score"], reverse=True)
    return {"query": query, "matches": [r for r in ranked[:limit] if r["score"] > 0], "total": len(entries()), "missing": not any(r["score"] > 0 for r in ranked[:limit])}


def annotate(text: str) -> dict:
    found = [card(e) for e in entries() if e["fr"].lower() in text.lower() or e["ru"].lower() in text.lower()]
    return {"text": shorten(text, 300), "terms": found[:10], "coverage": round(len(found) / max(len(tokenize(text)), 1), 2)}


def uncovered(limit: int = 12) -> list[dict]:
    counts = unknown_counts()
    return [{"term": term, "count": count} for term, count in counts.most_common(limit) if count >= 4]


def unknown_counts() -> Counter:
    known = {s for e in entries() for s in stems(haystack(e))}
    return Counter(t for c in chunks() for t in tokenize(c.text) if stem(t) not in known)


def by_domain() -> list[dict]:
    return [{"domain": key, "label": label, "count": sum(1 for e in entries() if e["domain"] == key)} for key, label in DOMAIN_LABELS.items() if any(e["domain"] == key for e in entries())]


def context_for(term: str, limit: int = 2) -> list[str]:
    hits = [s for c in chunks() if term.lower() in c.text.lower() for s in sentences(c.text) if term.lower() in s.lower()]
    return [shorten(s, 220) for s in hits[:limit]]


def overview() -> dict:
    used = sum(1 for e in entries() if occurrences(e["fr"]) > 0)
    return {"terms": len(entries()), "used_in_corpus": used, "coverage": round(used / max(len(entries()), 1), 2), "domains": by_domain(), "uncovered": uncovered(), "sample": [card(e) for e in entries()[:6]]}


def related_terms(domain: str, limit: int = 6) -> list[dict]:
    return [{"fr": e["fr"], "ru": e["ru"]} for e in entries() if e["domain"] == domain][:limit]
