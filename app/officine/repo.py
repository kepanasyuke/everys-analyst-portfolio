"""Слой доступа к SQLite офисины: чтение, транзакции, журнал действий."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from typing import Callable

from app.core.store import DB

SCHEMA = """
CREATE TABLE IF NOT EXISTS journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    acteur TEXT NOT NULL,
    action TEXT NOT NULL,
    cible TEXT NOT NULL,
    details TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_journal_ts ON journal (ts DESC);
CREATE INDEX IF NOT EXISTS idx_ventes_date ON ventes (date);
"""


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB, timeout=10, isolation_level=None)
    return configured(connection)


def configured(connection: sqlite3.Connection) -> sqlite3.Connection:
    connection.row_factory = sqlite3.Row
    return prepared(connection)


def prepared(connection: sqlite3.Connection) -> sqlite3.Connection:
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def rows_of(connection: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(row) for row in connection.execute(sql, params).fetchall()]


def read(sql: str, params: tuple = ()) -> list[dict]:
    with closing(connect()) as connection:
        return rows_of(connection, sql, params)


def one(sql: str, params: tuple = ()) -> dict:
    return next(iter(read(sql, params)), {})


def run_transaction(worker: Callable[[sqlite3.Connection], dict]) -> dict:
    with closing(connect()) as connection:
        return committed(connection, worker)


def committed(connection: sqlite3.Connection, worker: Callable[[sqlite3.Connection], dict]) -> dict:
    connection.execute("BEGIN IMMEDIATE")
    try:
        result = worker(connection)
        connection.execute("COMMIT")
        return result
    except BaseException:
        connection.execute("ROLLBACK")
        raise


def log(connection: sqlite3.Connection, acteur: str, action: str, cible: str, details: dict) -> int:
    cursor = connection.execute(
        "INSERT INTO journal (ts, acteur, action, cible, details) VALUES (?,?,?,?,?)",
        (now(), acteur, action, cible, json.dumps(details, ensure_ascii=False)),
    )
    return int(cursor.lastrowid or 0)


def ensure_schema() -> None:
    with closing(connect()) as connection:
        connection.executescript(SCHEMA)
    return None
