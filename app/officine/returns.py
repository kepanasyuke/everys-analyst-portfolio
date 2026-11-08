"""Возвраты по продажам (частичные и полные) и история движений товара."""

from __future__ import annotations

import json

from app.officine import logic
from app.officine.errors import require
from app.officine.repo import log, now, one, read, rows_of, run_transaction

RETURN_LINES_SQL = "SELECT lr.*, p.nom FROM lignes_retour lr JOIN produits p ON p.cip = lr.cip WHERE lr.retour_id = ? ORDER BY lr.id"


def sold_of(connection, sale_id: int, cip: str) -> int:
    row = next(iter(rows_of(connection, "SELECT COALESCE(SUM(quantite), 0) AS q FROM lignes_vente WHERE vente_id = ? AND cip = ?", (sale_id, cip))), {})
    return int(row.get("q") or 0)


def returned_of(connection, sale_id: int, cip: str) -> int:
    row = next(iter(rows_of(connection, "SELECT COALESCE(SUM(lr.quantite), 0) AS q FROM lignes_retour lr JOIN retours r ON r.id = lr.retour_id WHERE r.vente_id = ? AND lr.cip = ?", (sale_id, cip))), {})
    return int(row.get("q") or 0)


def available_of(connection, sale_id: int, cip: str) -> int:
    return sold_of(connection, sale_id, cip) - returned_of(connection, sale_id, cip)


def unit_price(connection, sale_id: int, cip: str) -> float:
    row = next(iter(rows_of(connection, "SELECT prix_unitaire FROM lignes_vente WHERE vente_id = ? AND cip = ? ORDER BY id LIMIT 1", (sale_id, cip))), {})
    return float(row.get("prix_unitaire") or 0)


def return_message(cip: str, available: int) -> str:
    return f"Позиции {cip} нет в этой продаже" if available <= 0 else f"Вернуть можно не больше {available} шт. по позиции {cip}"


def checked_line(connection, sale_id: int, cip: str, quantite: int) -> dict:
    require(0 < quantite <= available_of(connection, sale_id, cip), return_message(cip, available_of(connection, sale_id, cip)), 409)
    return {"cip": cip, "quantite": quantite, "prix": unit_price(connection, sale_id, cip)}


def returnable(connection, sale: dict, item: dict) -> dict:
    return checked_line(connection, sale["id"], str(item.get("cip", "")), logic.integer(item.get("quantite")))


def return_total(lines: list[dict], remise) -> float:
    return round(sum(line["quantite"] * line["prix"] for line in lines) * (1 - float(remise or 0) / 100), 2)


def insert_return(connection, sale: dict, payload: dict, montant: float) -> int:
    cursor = connection.execute("INSERT INTO retours (vente_id, ts, acteur, role, montant) VALUES (?,?,?,?,?)", (sale["id"], now(), logic.actor(payload), logic.role_of(payload), montant))
    return int(cursor.lastrowid or 0)


def store_return_lines(connection, retour_id: int, lines: list[dict]) -> int:
    [connection.execute("INSERT INTO lignes_retour (retour_id, cip, quantite, prix_unitaire) VALUES (?,?,?,?)", (retour_id, line["cip"], line["quantite"], line["prix"])) for line in lines]
    return len(lines)


def retour_row(connection, retour_id: int) -> dict:
    return logic.existing(next(iter(rows_of(connection, "SELECT * FROM retours WHERE id = ?", (retour_id,))), {}), f"Возврат {retour_id} не найден")


def detail_live(connection, retour_id: int) -> dict:
    retour = retour_row(connection, retour_id)
    return {**retour, "lignes": rows_of(connection, RETURN_LINES_SQL, (retour_id,))}


def log_return(connection, retour_id: int, sale: dict, payload: dict) -> dict:
    log(connection, logic.actor(payload), "sale.return", str(sale["id"]), {"retour": retour_id, "role": logic.role_of(payload), "positions": len(payload["lignes"])})
    return detail_live(connection, retour_id)


def restore_and_log(connection, retour_id: int, sale: dict, lines: list[dict], payload: dict) -> dict:
    [logic.increment(connection, line["cip"], line["quantite"], logic.actor(payload)) for line in lines]
    return log_return(connection, retour_id, sale, payload)


def finish_return(connection, retour_id: int, sale: dict, lines: list[dict], payload: dict) -> dict:
    store_return_lines(connection, retour_id, lines)
    return restore_and_log(connection, retour_id, sale, lines, payload)


def persist_return(connection, sale: dict, payload: dict) -> dict:
    lines = [returnable(connection, sale, item) for item in logic.merge_lines(payload["lignes"])]
    return finish_return(connection, insert_return(connection, sale, payload, return_total(lines, sale["remise_pct"])), sale, lines, payload)


def build_return(connection, payload: dict) -> dict:
    sale = logic.sale_row(connection, logic.integer(payload.get("sale_id")))
    return returnable_sale(connection, sale, payload)


def returnable_sale(connection, sale: dict, payload: dict) -> dict:
    require(sale["statut"] == "validee", "Возврат возможен только по проведённой продаже", 409)
    return persist_return(connection, sale, payload)


def create_return(payload: dict) -> dict:
    require(bool(payload.get("lignes")), "Добавьте хотя бы одну позицию возврата", 422)
    return run_transaction(lambda connection: build_return(connection, payload))


def returns_of(sale_id: int) -> list[dict]:
    return [{**row, "lignes": read(RETURN_LINES_SQL, (row["id"],))} for row in read("SELECT * FROM retours WHERE vente_id = ? ORDER BY id", (sale_id,))]


def sale_moves(cip: str) -> list[dict]:
    rows = read("SELECT v.id, v.date, l.quantite FROM lignes_vente l JOIN ventes v ON v.id = l.vente_id WHERE l.cip = ? ORDER BY v.date DESC, v.id DESC LIMIT 40", (cip,))
    return [{"ts": row["date"], "kind": "sale", "quantite": -int(row["quantite"]), "ref": f"продажа №{row['id']}"} for row in rows]


def return_moves(cip: str) -> list[dict]:
    rows = read("SELECT r.vente_id, r.ts, lr.quantite FROM lignes_retour lr JOIN retours r ON r.id = lr.retour_id WHERE lr.cip = ? ORDER BY r.id DESC LIMIT 40", (cip,))
    return [{"ts": row["ts"], "kind": "return", "quantite": int(row["quantite"]), "ref": f"возврат по продаже №{row['vente_id']}"} for row in rows]


def restock_moves(cip: str) -> list[dict]:
    rows = read("SELECT ts, details, acteur FROM journal WHERE action = 'stock.restock' AND cible = ? ORDER BY id DESC LIMIT 40", (cip,))
    return [{"ts": row["ts"], "kind": "restock", "quantite": int(json.loads(row["details"]).get("quantite", 0)), "ref": f"пополнение · {row['acteur']}"} for row in rows]


def movements(cip: str, limit: int = 30) -> dict:
    product = logic.existing(one(logic.PRODUCT_SQL, (cip,)), f"Товар {cip} не найден")
    return {"product": logic.decorate(product), "items": sorted([*sale_moves(cip), *return_moves(cip), *restock_moves(cip)], key=lambda row: row["ts"], reverse=True)[:limit]}
