"""BM25-ретривер: локальная замена векторному поиску для RAG-сценариев аналитика."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from functools import cached_property

from .text import normalize, shorten, stems, tokenize

K1 = 1.5
B = 0.75


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    title: str
    order: int
    text: str
    tags: tuple[str, ...] = ()


@dataclass
class Hit:
    chunk: Chunk
    score: float
    terms: list[str] = field(default_factory=list)


class Retriever:
    """Индекс по чанкам: документ разбивается на фрагменты, поиск идёт по вкладу терминов."""

    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = tuple(chunks)

    @classmethod
    def from_texts(cls, texts: list[str]) -> Retriever:
        return cls([Chunk(f"doc{index}", text, 0, text) for index, text in enumerate(texts)])

    def __len__(self) -> int:
        return len(self.chunks)

    @cached_property
    def tokens(self) -> list[list[str]]:
        return [[*stems(c.title), *stems(c.text)] for c in self.chunks]

    @cached_property
    def lengths(self) -> list[int]:
        return [len(t) for t in self.tokens]

    @cached_property
    def avg_len(self) -> float:
        return sum(self.lengths) / max(len(self.lengths), 1)

    @cached_property
    def doc_freq(self) -> Counter:
        return Counter(t for doc in self.tokens for t in set(doc))

    def idf(self, term: str) -> float:
        df = self.doc_freq.get(term, 0)
        return math.log(1 + (len(self) - df + 0.5) / (df + 0.5))

    def tf(self, index: int, term: str) -> float:
        freq = self.tokens[index].count(term)
        return freq * (K1 + 1) / (freq + K1 * (1 - B + B * self.lengths[index] / self.avg_len)) if freq else 0.0

    def bm25(self, index: int, terms: list[str]) -> float:
        return sum(self.idf(t) * self.tf(index, t) for t in set(terms))

    def score_all(self, query: str) -> list[Hit]:
        terms = stems(query)
        return [Hit(self.chunks[i], self.bm25(i, terms), terms) for i in range(len(self))]

    def search(self, query: str, limit: int = 5) -> list[Hit]:
        ranked = sorted(self.score_all(query), key=lambda h: h.score, reverse=True)
        return [h for h in ranked[:limit] if h.score > 0]

    def as_citations(self, query: str, limit: int = 5) -> list[dict]:
        return [citation(h, query) for h in self.search(query, limit)]

    def context(self, query: str, limit: int = 5) -> str:
        return "\n\n".join(f"[{c['id']}] {c['title']}\n{c['text']}" for c in self.as_citations(query, limit))


def citation(hit: Hit, query: str) -> dict:
    return {
        "id": f"{hit.chunk.doc_id}#{hit.chunk.order}",
        "doc_id": hit.chunk.doc_id,
        "title": hit.chunk.title,
        "order": hit.chunk.order,
        "score": round(hit.score, 3),
        "text": shorten(normalize(hit.chunk.text), 320),
        "tags": list(hit.chunk.tags),
        "matched": sorted({t for t in hit.terms if t in " ".join(hit.chunk.text.lower().split())})[:8],
    }


def index_of(chunks: list[Chunk]) -> Retriever:
    return Retriever(chunks)
