"""Текстовые примитивы: токенизация, лёгкий стемминг, сегментация, похожесть.

Работает одинаково для русского и французского текста без внешних зависимостей.
"""

from __future__ import annotations

import re

TOKEN_RE = re.compile(r"[0-9a-zA-Zа-яА-ЯёЁàâäéèêëîïôöùûüçœæñ]+")
SENT_RE = re.compile(r"(?<=[.!?])\s+|\n+|[•·]\s*")
NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
STEM_LEN = 6

STOP_FR = frozenset(
    "les des une pour dans avec sur par est sont que qui pas plus aux ses son sa leur etre avoir "
    "cette ces tout tous nous vous ils elles mais ou donc car afin lors apres avant entre sans chez "
    "the and for with that this from are was were will can not".split()
)
STOP_RU = frozenset(
    "что для при как это или быть если так его она они все эти тот том для без при над под про чем "
    "который которая которые чтобы когда также через после перед между нужно может должен".split()
)
STOP = STOP_FR | STOP_RU


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()


def tokenize(text: str) -> list[str]:
    return [m[0].lower() for m in TOKEN_RE.finditer(text) if len(m[0]) > 2 and m[0].lower() not in STOP]


def stem(token: str) -> str:
    return token[:STEM_LEN]


def stems(text_or_tokens: str | list[str]) -> list[str]:
    return [stem(t) for t in (tokenize(text_or_tokens) if isinstance(text_or_tokens, str) else text_or_tokens)]


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT_RE.split(normalize(text)) if len(s.strip()) > 2]


def numbers(text: str) -> list[float]:
    return [float(m[0].replace(",", ".")) for m in NUM_RE.finditer(text)]


def overlap(a: list[str] | set[str], b: list[str] | set[str]) -> float:
    left, right = set(a), set(b)
    return len(left & right) / len(left | right) if left | right else 0.0


def contains_terms(text: str, terms: list[str]) -> bool:
    return all(t.lower() in text.lower() for t in terms)


def best_sentences(query: str, text: str, limit: int = 3) -> list[str]:
    terms = set(stems(query))
    return sorted(sentences(text), key=lambda s: overlap(terms, stems(s)), reverse=True)[:limit]


def shorten(text: str, limit: int = 220) -> str:
    flat = normalize(text)
    return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "…"
