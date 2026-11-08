"""Слой доступа к SQLite офисины: чтение, транзакции, журнал действий."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from typing import Callable

from app.core.store import DB
from app.officine.errors import require

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
CREATE TABLE IF NOT EXISTS retours (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vente_id INTEGER NOT NULL,
    ts TEXT NOT NULL,
    acteur TEXT NOT NULL,
    role TEXT NOT NULL,
    montant REAL NOT NULL CHECK (montant >= 0),
    FOREIGN KEY (vente_id) REFERENCES ventes (id)
);
CREATE TABLE IF NOT EXISTS lignes_retour (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    retour_id INTEGER NOT NULL,
    cip TEXT NOT NULL,
    quantite INTEGER NOT NULL CHECK (quantite > 0),
    prix_unitaire REAL NOT NULL CHECK (prix_unitaire >= 0),
    FOREIGN KEY (retour_id) REFERENCES retours (id),
    FOREIGN KEY (cip) REFERENCES produits (cip)
);
CREATE INDEX IF NOT EXISTS idx_retours_vente ON retours (vente_id);
CREATE INDEX IF NOT EXISTS idx_lignes_retour_cip ON lignes_retour (cip);
CREATE INDEX IF NOT EXISTS idx_lignes_vente_cip ON lignes_vente (cip);
"""

ATTEMPTS = 5


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
    return retried(worker, ATTEMPTS)


def retried(worker: Callable[[sqlite3.Connection], dict], attempts: int) -> dict:
    with closing(connect()) as connection:
        return attempt(connection, worker, attempts)


def attempt(connection: sqlite3.Connection, worker: Callable[[sqlite3.Connection], dict], attempts: int) -> dict:
    try:
        result, error = committed(connection, worker), None
    except sqlite3.OperationalError as failure:
        result, error = None, failure
    return retry_result(result, error, worker, attempts)


def retry_result(result, error, worker: Callable[[sqlite3.Connection], dict], attempts: int) -> dict:
    return result if error is None else retry_or_fail(worker, attempts, error)


def retry_or_fail(worker: Callable[[sqlite3.Connection], dict], attempts: int, error: sqlite3.OperationalError) -> dict:
    require(is_lock(error) and attempts > 1, f"База занята: {error}", 503)
    return retried(worker, attempts - 1)


def is_lock(error: sqlite3.OperationalError) -> bool:
    text = str(error).lower()
    return "locked" in text or "busy" in text


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
