"""Пополнение по порогам (réassort): расчёт потребности и массовый заказ одной транзакцией."""

from __future__ import annotations

import json

from app.officine import logic
from app.officine.errors import require
from app.officine.repo import log, now, read, rows_of, run_transaction

MIN_ORDER = 5
TARGET_FACTOR = 2
PROPOSAL_SQL = "SELECT * FROM produits WHERE stock_actuel <= seuil ORDER BY stock_actuel - seuil, nom"


def besoin(product: dict) -> int:
    return max(MIN_ORDER, int(product["seuil"]) * TARGET_FACTOR - int(product["stock_actuel"]))


def proposal(product: dict) -> dict:
    return {**logic.decorate(product), "besoin": besoin(product), "thermosensible": int(product.get("thermosensible") or 0)}


def by_category(items: list[dict]) -> list[dict]:
    names = sorted({item["categorie"] for item in items})
    return [{"categorie": name, "positions": sum(1 for item in items if item["categorie"] == name), "units": sum(item["besoin"] for item in items if item["categorie"] == name)} for name in names]


def summary(items: list[dict]) -> dict:
    return {"positions": len(items), "units": sum(item["besoin"] for item in items), "ruptures": sum(1 for item in items if int(item["stock_actuel"]) == 0), "categories": by_category(items)}


def plan(limit: int = 60) -> dict:
    items = [proposal(row) for row in read(PROPOSAL_SQL)][:limit]
    return {"items": items, "summary": summary(items), "generated_at": now(), "rule": f"цель = порог × {TARGET_FACTOR}, минимум {MIN_ORDER} шт."}


def line_of(connection, item: dict) -> dict:
    product = logic.product_row(connection, str(item.get("cip", "")))
    return checked(product, logic.integer(item.get("quantite")))


def checked(product: dict, quantite: int) -> dict:
    require(quantite > 0, f"Количество по «{product['nom']}» должно быть положительным", 422)
    return {"cip": product["cip"], "nom": product["nom"], "quantite": quantite}


def insert_order(connection, payload: dict, lines: list[dict]) -> int:
    cursor = connection.execute("INSERT INTO journal (ts, acteur, action, cible, details) VALUES (?,?,?,?,?)", (now(), logic.actor(payload), "stock.reorder", "batch", json.dumps({"positions": len(lines), "units": sum(line["quantite"] for line in lines)}, ensure_ascii=False)))
    return int(cursor.lastrowid or 0)


def apply_lines(connection, batch_id: int, lines: list[dict], payload: dict) -> dict:
    [logic.increment(connection, line["cip"], line["quantite"], logic.actor(payload)) for line in lines]
    return {"ok": True, "batch": batch_id, "positions": len(lines), "units": sum(line["quantite"] for line in lines)}


def persist_order(connection, payload: dict) -> dict:
    lines = [line_of(connection, item) for item in logic.merge_lines(payload["lignes"])]
    return apply_lines(connection, insert_order(connection, payload, lines), lines, payload)


def create_order(payload: dict) -> dict:
    require(bool(payload.get("lignes")), "Добавьте хотя бы одну позицию заказа", 422)
    return run_transaction(lambda connection: persist_order(connection, payload))


def recent_orders(limit: int = 8) -> list[dict]:
    rows = read("SELECT id, ts, acteur, details FROM journal WHERE action = 'stock.reorder' ORDER BY id DESC LIMIT ?", (limit,))
    return [{"id": row["id"], "ts": row["ts"], "acteur": row["acteur"], **json.loads(row["details"])} for row in rows]


def stock_after(connection, cip: str) -> int:
    return int(rows_of(connection, "SELECT stock_actuel FROM produits WHERE cip = ?", (cip,))[0]["stock_actuel"])
