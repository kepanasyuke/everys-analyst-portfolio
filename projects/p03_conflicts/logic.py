"""P03 — радар противоречий: находит расхождения между спецификациями до разработки."""

from __future__ import annotations

import re

from app.ai.text import normalize, numbers, sentences, shorten, stems
from app.core.store import chunks, documents

TLS_RE = re.compile(r"tls\s*(\d\.\d)", re.I)

TOPICS = [
    {"id": "remise", "unit": "percent", "keys": ("remise", "скидк")},
    {"id": "conservation", "unit": "temp", "keys": ("°c", "température", "temperature", "conserv")},
    {"id": "tva", "unit": "percent", "keys": ("tva",)},
    {"id": "tls", "unit": "version", "keys": ("tls",)},
    {"id": "creance", "unit": "hours", "keys": ("créance", "creance", "retransmis")},
    {"id": "rupture", "unit": "percent", "keys": ("rupture",)},
    {"id": "controle", "unit": "modal", "keys": ("double contrôle", "contrôle pharmacien", "stupéfiant")},
    {"id": "ordonnance", "unit": "months", "keys": ("ordonnance",)},
    {"id": "sonde", "unit": "minutes", "keys": ("sonde",)},
    {"id": "flux", "unit": "hours", "keys": ("flux", "idflux")},
]

LABELS = {
    "remise": "Максимальная коммерческая скидка",
    "conservation": "Температурный режим хранения",
    "tva": "Ставка НДС на возмещаемые препараты",
    "tls": "Минимальная версия TLS",
    "creance": "Срок повторной передачи отклонённого требования",
    "rupture": "Допустимый уровень дефектуры",
    "controle": "Контроль наркотических средств",
    "ordonnance": "Срок действия рецепта",
    "sonde": "Интервал опроса температурного датчика",
    "flux": "Срок реакции на поток",
}

MUST = ("obligatoire", "doit", "impose", "обязательн", "должен")
MUST_NOT = ("interdit", "recommand", "conseill", "possible", "запрещ", "рекоменд", "допускается")
RECOMMENDATION = "Согласовать единое значение, назначить владельца правила и обновить оба документа одной задачей."


def fr(num: float) -> str:
    return f"{num:g}".replace(".", ",")


def modality(text: str) -> str:
    low = text.lower()
    return "must_not" if any(m in low for m in MUST_NOT) else "must" if any(m in low for m in MUST) else "info"


def pct(text: str) -> str:
    found = numbers(text)
    return f"{fr(found[0])} %" if found else ""


def temp(text: str) -> str:
    found = numbers(text)
    return f"{fr(found[0])}–{fr(found[1])} °C" if len(found) > 1 else ""


def version(text: str) -> str:
    found = TLS_RE.search(text)
    return f"TLS {found[1]}" if found else ""


def timed(text: str, unit: str) -> str:
    found = numbers(text)
    return f"{fr(found[0])} {unit}" if found else ""


def hours(text: str) -> str:
    return timed(text, "ч")


def months(text: str) -> str:
    return timed(text, "мес")


def minutes(text: str) -> str:
    return timed(text, "мин")


EXTRACTORS = {"percent": pct, "temp": temp, "version": version, "hours": hours, "months": months, "minutes": minutes, "modal": modality}


def value_of(text: str, unit: str) -> str:
    return EXTRACTORS[unit](text)


def topic_of(text: str) -> dict:
    match = match_topic(text.lower())
    return {"topic": match["id"], "unit": match["unit"], "value": value_of(text, match["unit"])} if match else {}


def match_topic(low: str) -> dict:
    return next((t for t in TOPICS if any(k in low for k in t["keys"])), {})


def statement(text: str, chunk) -> dict:
    topic = topic_of(text)
    return {"doc": chunk.doc_id, "title": chunk.title, "text": normalize(text), **topic} if topic.get("value") else {}


def statements_of(chunk) -> list[dict]:
    found = [statement(t, chunk) for t in sentences(chunk.text)]
    return [f for f in found if f]


def all_statements() -> list[dict]:
    return [s for chunk in chunks() for s in statements_of(chunk)]


def by_topic(items: list[dict]) -> dict:
    keys = sorted({i["topic"] for i in items})
    return {k: [i for i in items if i["topic"] == k] for k in keys}


def pairs(group: list[dict]) -> list[tuple[dict, dict]]:
    return [(a, b) for i, a in enumerate(group) for b in group[i + 1:] if a["doc"] != b["doc"] and a["value"] != b["value"]]


def severity(a: dict, b: dict) -> str:
    return "high" if a["unit"] != "modal" else "medium"


def conflict(a: dict, b: dict) -> dict:
    return {"topic": LABELS[a["topic"]], "kind": "числовое" if a["unit"] != "modal" else "модальное", "severity": severity(a, b), "left": {"doc": a["doc"], "title": a["title"], "value": a["value"], "text": shorten(a["text"], 260)}, "right": {"doc": b["doc"], "title": b["title"], "value": b["value"], "text": shorten(b["text"], 260)}, "recommendation": RECOMMENDATION}


def findings() -> list[dict]:
    groups = by_topic(all_statements())
    return dedupe([conflict(a, b) for group in groups.values() for a, b in pairs(group)])


def dedupe(items: list[dict]) -> list[dict]:
    seen: dict[tuple, dict] = {}
    return [seen.setdefault(key_of(i), i) for i in items if key_of(i) not in seen]


def key_of(item: dict) -> tuple:
    return (item["topic"], *sorted([item["left"]["value"], item["right"]["value"]]))


def rank(items: list[dict]) -> list[dict]:
    order = {"high": 0, "medium": 1}
    return sorted(items, key=lambda c: (order[c["severity"]], c["topic"]))


def versions() -> list[dict]:
    return [{"doc": d.get("doc_id"), "title": d.get("titre"), "version": d.get("version", "—"), "status": "в силе" if "draft" not in d.get("version", "") else "черновик"} for d in documents()]


def summary(items: list[dict]) -> dict:
    return {"total": len(items), "high": sum(1 for c in items if c["severity"] == "high"), "medium": sum(1 for c in items if c["severity"] == "medium"), "topics": sorted({c["topic"] for c in items}), "statements": len(all_statements()), "docs": len(documents())}


def scan(min_severity: str = "medium") -> dict:
    kept = filter_severity(rank(findings()), min_severity)
    return {"conflicts": kept, "summary": summary(kept), "documents": versions(), "ai": "эвристики нормализации утверждений + модальный анализ"}


def filter_severity(items: list[dict], min_severity: str) -> list[dict]:
    return [c for c in items if c["severity"] == "high" or min_severity == "medium"]


def related(text: str, limit: int = 4) -> list[dict]:
    terms = set(stems(text))
    return sorted(({"doc": s["doc"], "text": shorten(s["text"], 200), "score": len(terms & set(stems(s["text"])))} for s in all_statements()), key=lambda r: r["score"], reverse=True)[:limit]
