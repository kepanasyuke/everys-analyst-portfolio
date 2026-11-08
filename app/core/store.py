"""Доступ к данным портфолио: корпус документов, BM25-индекс, read-only SQLite."""

from __future__ import annotations

import re
import sqlite3
from functools import lru_cache
from pathlib import Path

from app.ai.retriever import Chunk, Retriever

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DOCS = DATA / "docs"
GLOSSARY = DATA / "glossaire.json"
DB = DATA / "officine.db"

FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.S)
SECTION_RE = re.compile(r"^##\s+(.*)$", re.M)


def split_front(raw: str) -> tuple[dict, str]:
    match = FRONT_RE.match(raw)
    return (meta_of(match[1]), match[2].strip()) if match else ({}, raw.strip())


def meta_of(block: str) -> dict:
    pairs = [line.split(":", 1) for line in block.strip().splitlines() if ":" in line]
    return {k.strip(): v.strip() for k, v in pairs}


def load_doc(path: Path) -> dict:
    meta, body = split_front(path.read_text(encoding="utf-8"))
    return {**meta, "body": body, "file": path.name, "tags": tuple(t.strip() for t in meta.get("tags", "").strip("[]").split(",") if t.strip())}


def section_titles(body: str) -> list[str]:
    return ["Introduction", *[m[1].strip() for m in SECTION_RE.finditer(body)]]


def section_starts(body: str) -> list[int]:
    return [0, *[m.end() for m in SECTION_RE.finditer(body)]]


def section_ends(body: str) -> list[int]:
    return [*[m.start() for m in SECTION_RE.finditer(body)], len(body)]


def sections(body: str) -> list[tuple[str, str]]:
    spans = list(zip(section_starts(body), section_ends(body)))
    return list(zip(section_titles(body), [body[a:b].strip() for a, b in spans]))


def chunk_doc(doc: dict) -> list[Chunk]:
    return [Chunk(doc.get("doc_id", doc["file"]), f"{doc.get('titre', doc['file'])} → {title}", i, text, doc["tags"]) for i, (title, text) in enumerate(sections(doc["body"]))]


@lru_cache(maxsize=1)
def documents() -> tuple[dict, ...]:
    return tuple(load_doc(p) for p in sorted(DOCS.glob("*.md")))


@lru_cache(maxsize=1)
def chunks() -> tuple[Chunk, ...]:
    return tuple(c for doc in documents() for c in chunk_doc(doc))


@lru_cache(maxsize=1)
def retriever() -> Retriever:
    return Retriever(list(chunks()))


def doc_by_id(doc_id: str) -> dict:
    return next((d for d in documents() if d.get("doc_id") == doc_id), {})


def corpus_stats() -> dict:
    return {"documents": len(documents()), "chunks": len(chunks()), "terms": len(retriever().doc_freq), "avg_chunk_len": round(retriever().avg_len, 1)}


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    return with_row_factory(connection)


def with_row_factory(connection: sqlite3.Connection) -> sqlite3.Connection:
    connection.row_factory = sqlite3.Row
    return connection


def tables() -> dict:
    with connect() as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return {r["name"]: [c["name"] for c in connect().execute(f"PRAGMA table_info({r['name']})")] for r in rows}
