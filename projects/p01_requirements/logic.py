"""P01 — из user story в критерии приёмки (Given/When/Then) с проверкой по источникам."""

from __future__ import annotations

import re

from app.ai import llm
from app.ai.guard import audit
from app.ai.text import normalize, numbers, sentences, shorten
from app.core.store import chunks, retriever

ACTOR_RE = re.compile(r"(?:en tant que|как)\s+([^,\n.;]+?)(?=\s+(?:je|я|nous|мы|хочу|нужно|необходимо)|[,;.]|$)", re.I)
GOAL_RE = re.compile(r"(?:je veux|je souhaite|хочу|нужно|необходимо)\s+([^,\n.;]+)", re.I)
CYRILLIC = re.compile(r"[а-яА-Я]")
RULE_WORDS = (
    "obligatoire", "interdit", "refus", "doit", "délai", "delai", "seuil", "maximum",
    "minimum", "obligator", "обязательн", "запрещ", "нельзя", "отказ", "срок", "порог",
    "максимум", "минимум", "должен",
)
MUST = ("obligatoire", "doit", "impose", "обязательн", "должен", "требуется")
MUST_NOT = ("interdit", "refus", "aucune", "jamais", "запрещ", "нельзя", "отказ", "невозможно")
TEMPLATES = {
    "ru": {
        "given": "дано: {doc}",
        "when": "когда {goal}",
        "then": "тогда {statement}",
        "base_questions": [
            "Кто именно инициирует сценарий и какие у него права?",
            "Что происходит при повторной отправке того же действия?",
            "Какое состояние считается конечным и как оно проверяется?",
        ],
        "risk": {
            "numeric": "Числовой порог без источника в актуальной версии документа — риск расхождения с продом.",
            "modal": "Модальность (обязательно/запрещено) без явной формулировки проверки — риск разной трактовки.",
        },
    },
    "fr": {
        "given": "étant donné : {doc}",
        "when": "quand {goal}",
        "then": "alors {statement}",
        "base_questions": [
            "Qui déclenche le scénario et avec quels droits ?",
            "Que se passe-t-il en cas de rejeu de la même action ?",
            "Quel état est considéré comme final et comment est-il vérifié ?",
        ],
        "risk": {
            "numeric": "Seuil numérique sans source dans la version en vigueur — risque d'écart avec la production.",
            "modal": "Modalité (obligatoire/interdit) non testable en l'état — risque d'interprétation divergente.",
        },
    },
}


def language(text: str) -> str:
    return "ru" if CYRILLIC.search(text) else "fr"


def actor(text: str) -> str:
    found = ACTOR_RE.search(text)
    return normalize(found[1]) if found else ("фармацевт" if language(text) == "ru" else "pharmacien")


def goal(text: str) -> str:
    found = GOAL_RE.search(text)
    return normalize(found[1]) if found else shorten(text, 120)


def context_of(story: str) -> dict:
    lang = language(story)
    return {"lang": lang, "actor": actor(story), "goal": goal(story)}


def is_rule(sentence: str) -> bool:
    low = sentence.lower().strip()
    return not low.startswith(("étant donné", "etant donne", "дано", "alors")) and (bool(numbers(sentence)) or any(w in low for w in RULE_WORDS))


def modality(sentence: str) -> str:
    low = sentence.lower()
    return "must_not" if any(m in low for m in MUST_NOT) else "must" if any(m in low for m in MUST) else "info"


def kind(sentence: str) -> str:
    return "numeric" if numbers(sentence) else "modal" if modality(sentence) != "info" else "rule"


def value(sentence: str) -> str:
    found = numbers(sentence)
    return f"{found[0]:g}" if found else modality(sentence)


def hits(query: str, limit: int) -> list:
    return retriever().search(query, limit)


def statements(hit) -> list[str]:
    return [s for s in sentences(hit.chunk.text) if is_rule(s)]


def rule(sentence: str, hit) -> dict:
    return {"statement": normalize(sentence), "source": f"{hit.chunk.doc_id}#{hit.chunk.order}", "doc": hit.chunk.title, "kind": kind(sentence), "value": value(sentence), "modality": modality(sentence)}


def constraints(query: str, limit: int) -> list[dict]:
    return [rule(s, h) for h in hits(query, limit) for s in statements(h)]


def unique(items: list[dict], key: str) -> list[dict]:
    seen: dict[str, dict] = {}
    return [seen.setdefault(i[key], i) for i in items if i[key] not in seen]


def source_text(ref: str) -> str:
    doc_id, _, order = ref.partition("#")
    return next((c.text for c in chunks() if c.doc_id == doc_id and str(c.order) == order), "")


def criterion(item: dict, ctx: dict) -> dict:
    tpl = TEMPLATES[ctx["lang"]]
    return {"given": tpl["given"].format(doc=shorten(item["doc"], 70)), "when": tpl["when"].format(goal=ctx["goal"]), "then": tpl["then"].format(statement=shorten(item["statement"], 210)), "source": item["source"], "kind": item["kind"], "value": item["value"]}


def questions(items: list[dict], lang: str) -> list[str]:
    found = [i["statement"] for i in items if i["statement"].endswith("?")]
    return [*found, *TEMPLATES[lang]["base_questions"]][:4]


def risks(items: list[dict], lang: str) -> list[dict]:
    table = TEMPLATES[lang]["risk"]
    return [{"risk": table[i["kind"]], "source": i["source"]} for i in items if i["kind"] in table][:3]


def cite(hit) -> dict:
    return {"id": f"{hit.chunk.doc_id}#{hit.chunk.order}", "title": hit.chunk.title, "score": round(hit.score, 2), "text": shorten(hit.chunk.text, 220)}


def verification(items: list[dict]) -> dict:
    context = " ".join(source_text(i["source"]) for i in items)
    return audit([i["statement"] for i in items], context)


def report(story: str, limit: int, ctx: dict) -> dict:
    items = unique(constraints(story, limit), "statement")
    return {"language": ctx["lang"], "actor": ctx["actor"], "goal": ctx["goal"], "criteria": [criterion(i, ctx) for i in items[:6]], "questions": questions(items, ctx["lang"]), "risks": risks(items, ctx["lang"]), "context": [cite(h) for h in hits(story, limit)], "verification": verification(items), "ai": llm.status()}


def build(story: str, limit: int = 5) -> dict:
    ctx = context_of(story)
    return {"story": story, **report(story, limit, ctx)}
