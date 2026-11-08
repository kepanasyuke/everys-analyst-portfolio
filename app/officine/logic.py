"""Сценарии приложения офисины: каталог, касса, склад, сеть, дашборд.

Каждая операция выполняется в транзакции BEGIN IMMEDIATE и пишет строку в журнал:
без этого продажа, списание остатка и отмена не были бы воспроизводимы при разборе.
"""

from __future__ import annotations

import re
from datetime import date

from app.officine.errors import require
from app.officine.repo import log, one, read, rows_of, run_transaction

CIP_RE = re.compile(r"^\d{13}$")
DEFAULT_ACTOR = "pharmacien"
ROLES = ("pharmacien", "titulaire")
ROLE_LIMITS = {"pharmacien": 30.0, "titulaire": 100.0}
EDITABLE = ("prix_public", "stock_actuel", "seuil", "taux_remboursement")
FIELDS = ("cip", "nom", "dci", "categorie", "prix_public", "taux_remboursement", "thermosensible", "stock_actuel", "seuil")
INSERT_SQL = f"INSERT INTO produits ({', '.join(FIELDS)}) VALUES ({', '.join('?' * len(FIELDS))})"
PRODUCT_SQL = "SELECT * FROM produits WHERE cip = ?"
SALE_BASE = "SELECT v.*, o.nom AS officine, o.ville FROM ventes v JOIN officines o ON o.id = v.officine_id"
SALE_SQL = f"{SALE_BASE} WHERE v.id = ?"
LINES_SQL = "SELECT l.*, p.nom FROM lignes_vente l JOIN produits p ON p.cip = l.cip WHERE l.vente_id = ? ORDER BY l.id"


def integer(value) -> int:
    return int(float(value or 0))


def money(value) -> float:
    return round(float(value or 0), 2)


def actor(payload: dict) -> str:
    return str(payload.get("acteur") or DEFAULT_ACTOR)[:60]


def decorate(product: dict) -> dict:
    stock = int(product["stock_actuel"])
    return {**product, "statut_stock": "rupture" if stock == 0 else "alerte" if stock <= int(product["seuil"]) else "ok", "valeur_stock": round(float(product["prix_public"]) * stock, 2)}


def product_row(connection, cip: str) -> dict:
    product = next(iter(rows_of(connection, PRODUCT_SQL, (cip,))), {})
    return existing(product, f"Товар {cip} не найден")


def existing(record: dict, message: str) -> dict:
    require(bool(record), message, 404)
    return record


def exists_product(connection, cip: str) -> bool:
    return bool(rows_of(connection, "SELECT 1 FROM produits WHERE cip = ?", (cip,)))


def used_in_sales(connection, cip: str) -> bool:
    return bool(rows_of(connection, "SELECT 1 FROM lignes_vente WHERE cip = ? LIMIT 1", (cip,)))


def categories() -> list[str]:
    return [row["categorie"] for row in read("SELECT DISTINCT categorie FROM produits ORDER BY categorie")]


def search_clause(query: str) -> list[tuple[str, list]]:
    return [("(nom LIKE ? OR dci LIKE ? OR cip LIKE ?)", [f"%{query}%"] * 3)] if query else []


def category_clause(category: str) -> list[tuple[str, list]]:
    return [("categorie = ?", [category])] if category else []


def product_filter(query: str, category: str) -> tuple[str, list]:
    clauses = [*search_clause(query), *category_clause(category)]
    return " AND ".join(clause for clause, _ in clauses) or "1=1", [value for _, params in clauses for value in params]


def list_products(query: str = "", category: str = "", limit: int = 80) -> dict:
    where, params = product_filter(query, category)
    return {"items": [decorate(row) for row in read(f"SELECT * FROM produits WHERE {where} ORDER BY nom LIMIT ?", (*params, limit))], "categories": categories(), "total": one(f"SELECT COUNT(*) AS n FROM produits WHERE {where}", tuple(params))}


def validated_product(payload: dict) -> dict:
    require(bool(CIP_RE.match(str(payload.get("cip", "")))), "Код CIP13 должен состоять из 13 цифр", 422)
    return {**payload, "cip": str(payload["cip"]), "nom": str(payload.get("nom", "")).strip(), "dci": str(payload.get("dci", "")).strip(), "categorie": str(payload.get("categorie", "autre")).strip() or "autre", "prix_public": money(payload.get("prix_public")), "taux_remboursement": integer(payload.get("taux_remboursement")), "thermosensible": 1 if payload.get("thermosensible") else 0, "stock_actuel": integer(payload.get("stock_actuel")), "seuil": integer(payload.get("seuil") or 10)}


def create_product(payload: dict) -> dict:
    record = validated_product(payload)
    return run_transaction(lambda connection: insert_new(connection, record))


def insert_new(connection, record: dict) -> dict:
    require(bool(record["nom"]) and record["prix_public"] > 0, "Нужны название и положительная цена", 422)
    return insert_product(connection, record)


def insert_product(connection, record: dict) -> dict:
    require(not exists_product(connection, record["cip"]), f"Товар с кодом {record['cip']} уже есть в справочнике", 409)
    return write_product(connection, record)


def write_product(connection, record: dict) -> dict:
    insert_row(connection, record)
    return product_row(connection, record["cip"])


def insert_row(connection, record: dict) -> int:
    connection.execute(INSERT_SQL, tuple(record.get(field) for field in FIELDS))
    return log(connection, actor(record), "product.create", record["cip"], {field: record.get(field) for field in FIELDS})


def normalized(payload: dict) -> dict:
    return {field: money(payload[field]) if field == "prix_public" else integer(payload[field]) for field in EDITABLE if field in payload}


def update_product(cip: str, payload: dict) -> dict:
    return run_transaction(lambda connection: patch_product(connection, cip, payload))


def patch_product(connection, cip: str, payload: dict) -> dict:
    product = product_row(connection, cip)
    return write_changes(connection, product, normalized(payload), actor(payload))


def write_changes(connection, product: dict, changes: dict, acteur: str) -> dict:
    require(bool(changes), "Нет полей для изменения", 422)
    return apply_change(connection, product, changes, acteur)


def apply_change(connection, product: dict, changes: dict, acteur: str) -> dict:
    update_row(connection, product["cip"], changes, acteur)
    return product_row(connection, product["cip"])


def update_row(connection, cip: str, changes: dict, acteur: str) -> int:
    require(all(value >= 0 for value in changes.values()), "Значения не могут быть отрицательными", 422)
    return execute_change(connection, cip, changes, acteur)


def execute_change(connection, cip: str, changes: dict, acteur: str) -> int:
    connection.execute(f"UPDATE produits SET {', '.join(f'{field} = ?' for field in changes)} WHERE cip = ?", (*changes.values(), cip))
    return log(connection, acteur, "product.update", cip, changes)


def restock(cip: str, quantite, acteur: str = DEFAULT_ACTOR) -> dict:
    return run_transaction(lambda connection: apply_restock(connection, cip, integer(quantite), acteur))


def apply_restock(connection, cip: str, quantite: int, acteur: str) -> dict:
    product = product_row(connection, cip)
    return restocking(connection, product, quantite, acteur)


def restocking(connection, product: dict, quantite: int, acteur: str) -> dict:
    require(quantite > 0, "Количество должно быть положительным", 422)
    return write_restock(connection, product, quantite, acteur)


def write_restock(connection, product: dict, quantite: int, acteur: str) -> dict:
    increment(connection, product["cip"], quantite, acteur)
    return product_row(connection, product["cip"])


def increment(connection, cip: str, quantite: int, acteur: str) -> int:
    connection.execute("UPDATE produits SET stock_actuel = stock_actuel + ? WHERE cip = ?", (quantite, cip))
    return log(connection, acteur, "stock.restock", cip, {"quantite": quantite})


def delete_product(cip: str, acteur: str = DEFAULT_ACTOR) -> dict:
    return run_transaction(lambda connection: remove_product(connection, cip, acteur))


def remove_product(connection, cip: str, acteur: str) -> dict:
    product = product_row(connection, cip)
    return removable(connection, product, acteur)


def removable(connection, product: dict, acteur: str) -> dict:
    require(not used_in_sales(connection, product["cip"]), "Товар уже продавался: удаление запрещено, оставьте его с нулевым остатком", 409)
    return drop_row(connection, product, acteur)


def drop_row(connection, product: dict, acteur: str) -> dict:
    connection.execute("DELETE FROM produits WHERE cip = ?", (product["cip"],))
    return log_and_confirm(connection, product, acteur)


def log_and_confirm(connection, product: dict, acteur: str) -> dict:
    log(connection, acteur, "product.delete", product["cip"], {"nom": product["nom"]})
    return {"ok": True, "cip": product["cip"], "nom": product["nom"]}


def merge_lines(lignes: list) -> list[dict]:
    totals = folded(lignes)
    return [{"cip": cip, "quantite": quantite} for cip, quantite in totals.items()]


def folded(lignes: list) -> dict:
    totals: dict[str, int] = {}
    return accumulate(totals, lignes)


def accumulate(totals: dict, lignes: list) -> dict:
    [totals.__setitem__(str(item.get("cip", "")), totals.get(str(item.get("cip", "")), 0) + integer(item.get("quantite"))) for item in lignes]
    return totals


def line_of(product: dict, item: dict) -> dict:
    quantite = integer(item.get("quantite"))
    return line_checked(product, quantite)


def line_checked(product: dict, quantite: int) -> dict:
    require(0 < quantite <= int(product["stock_actuel"]), stock_message(product, quantite), 409)
    return {"cip": product["cip"], "nom": product["nom"], "quantite": quantite, "prix": float(product["prix_public"])}


def stock_message(product: dict, quantite: int) -> str:
    return "Количество должно быть положительным" if quantite <= 0 else f"Недостаточно «{product['nom']}»: остаток {product['stock_actuel']}, запрошено {quantite}"


def resolve_line(connection, item: dict) -> dict:
    product = product_row(connection, str(item.get("cip", "")))
    return line_of(product, item)


def resolve_lines(connection, lignes: list) -> list[dict]:
    return [resolve_line(connection, item) for item in merge_lines(lignes)]


def role_of(payload: dict) -> str:
    role = str(payload.get("role") or DEFAULT_ACTOR)
    return role if role in ROLES else DEFAULT_ACTOR


def remise_of(value, role: str = DEFAULT_ACTOR) -> float:
    remise = max(0.0, float(value or 0))
    return checked_remise(remise, role)


def checked_remise(remise: float, role: str) -> float:
    require(remise <= ROLE_LIMITS.get(role, 30.0), remise_message(role), 409)
    return remise


def remise_message(role: str) -> str:
    return "Скидка не может превышать 100 %" if role == "titulaire" else "Скидка выше 30 % требует подтверждения титуляра"


def total_of(lines: list[dict], remise, role: str = DEFAULT_ACTOR) -> float:
    return round(sum(line["prix"] * line["quantite"] for line in lines) * (1 - remise_of(remise, role) / 100), 2)


def officine_id(payload: dict) -> int:
    value = integer(payload.get("officine_id") or 1)
    return known_officine(value)


def known_officine(value: int) -> int:
    require(bool(one("SELECT id FROM officines WHERE id = ?", (value,))), f"Аптека {value} не найдена", 404)
    return value


def insert_sale(connection, payload: dict, montant: float) -> int:
    cursor = connection.execute("INSERT INTO ventes (officine_id, date, canal, statut, remise_pct, montant_ttc) VALUES (?,?,?,?,?,?)", (officine_id(payload), date.today().isoformat(), str(payload.get("canal") or "comptoir"), "validee", int(remise_of(payload.get("remise_pct"), role_of(payload))), montant))
    return int(cursor.lastrowid or 0)


def store_lines(connection, sale_id: int, lines: list[dict]) -> int:
    [connection.execute("INSERT INTO lignes_vente (vente_id, cip, quantite, prix_unitaire) VALUES (?,?,?,?)", (sale_id, line["cip"], line["quantite"], line["prix"])) for line in lines]
    return len(lines)


def lines_of(connection, sale_id: int) -> list[dict]:
    return rows_of(connection, LINES_SQL, (sale_id,))


def decrement_line(connection, line: dict) -> int:
    connection.execute("UPDATE produits SET stock_actuel = stock_actuel - ? WHERE cip = ?", (line["quantite"], line["cip"]))
    return int(line["quantite"])


def decrement_stock(connection, sale_id: int) -> int:
    return sum(decrement_line(connection, line) for line in lines_of(connection, sale_id))


def restore_line(connection, line: dict) -> int:
    connection.execute("UPDATE produits SET stock_actuel = stock_actuel + ? WHERE cip = ?", (line["quantite"], line["cip"]))
    return int(line["quantite"])


def return_stock(connection, sale_id: int) -> int:
    return sum(restore_line(connection, line) for line in lines_of(connection, sale_id))


def sale_row(connection, sale_id: int) -> dict:
    return existing(next(iter(rows_of(connection, SALE_SQL, (sale_id,))), {}), f"Продажа {sale_id} не найдена")


def detailed(sale: dict) -> dict:
    return {**sale, "lignes": read(LINES_SQL, (sale["id"],))}


def detailed_live(connection, sale: dict) -> dict:
    return {**sale, "lignes": rows_of(connection, LINES_SQL, (sale["id"],))}


def sale_detail(sale_id: int) -> dict:
    return detailed(read_sale(sale_id))


def read_sale(sale_id: int) -> dict:
    return existing(one(SALE_SQL, (sale_id,)), f"Продажа {sale_id} не найдена")


def build_sale(connection, payload: dict) -> dict:
    lines = resolve_lines(connection, payload["lignes"])
    return persist_sale(connection, payload, lines)


def persist_sale(connection, payload: dict, lines: list[dict]) -> dict:
    sale_id = insert_sale(connection, payload, total_of(lines, payload.get("remise_pct"), role_of(payload)))
    return apply_sale(connection, sale_id, lines, payload)


def apply_sale(connection, sale_id: int, lines: list[dict], payload: dict) -> dict:
    store_lines(connection, sale_id, lines)
    return finish_sale(connection, sale_id, payload)


def finish_sale(connection, sale_id: int, payload: dict) -> dict:
    decrement_stock(connection, sale_id)
    return log_sale(connection, sale_id, payload)


def log_sale(connection, sale_id: int, payload: dict) -> dict:
    log(connection, actor(payload), "sale.create", str(sale_id), {"remise": payload.get("remise_pct", 0), "role": role_of(payload), "canal": payload.get("canal", "comptoir")})
    return detailed_live(connection, sale_row(connection, sale_id))


def create_sale(payload: dict) -> dict:
    require(bool(payload.get("lignes")), "Добавьте хотя бы одну позицию", 422)
    return run_transaction(lambda connection: build_sale(connection, payload))


def reverse_sale(connection, sale_id: int, acteur: str) -> dict:
    sale = sale_row(connection, sale_id)
    return cancellable(connection, sale, acteur)


def cancellable(connection, sale: dict, acteur: str) -> dict:
    require(sale["statut"] == "validee", "Отменить можно только проведённую продажу", 409)
    return mark_cancelled(connection, sale, acteur)


def mark_cancelled(connection, sale: dict, acteur: str) -> dict:
    connection.execute("UPDATE ventes SET statut = 'annulee' WHERE id = ?", (sale["id"],))
    return after_cancel(connection, sale, acteur)


def after_cancel(connection, sale: dict, acteur: str) -> dict:
    return_stock(connection, sale["id"])
    return confirm_cancel(connection, sale, acteur)


def confirm_cancel(connection, sale: dict, acteur: str) -> dict:
    log(connection, acteur, "sale.cancel", str(sale["id"]), {"montant": sale["montant_ttc"]})
    return detailed_live(connection, sale_row(connection, sale["id"]))


def cancel_sale(sale_id: int, acteur: str = DEFAULT_ACTOR) -> dict:
    return run_transaction(lambda connection: reverse_sale(connection, sale_id, acteur))


def statut_clause(statut: str) -> list[tuple[str, list]]:
    return [("v.statut = ?", [statut])] if statut else []


def from_clause(date_from: str) -> list[tuple[str, list]]:
    return [("v.date >= ?", [date_from])] if date_from else []


def to_clause(date_to: str) -> list[tuple[str, list]]:
    return [("v.date <= ?", [date_to])] if date_to else []


def sale_filter(statut: str, date_from: str, date_to: str) -> tuple[str, list]:
    clauses = [*statut_clause(statut), *from_clause(date_from), *to_clause(date_to)]
    return " AND ".join(clause for clause, _ in clauses) or "1=1", [value for _, params in clauses for value in params]


def list_sales(statut: str = "", limit: int = 25, date_from: str = "", date_to: str = "", offset: int = 0) -> list[dict]:
    where, params = sale_filter(statut, date_from, date_to)
    return read(f"{SALE_BASE} WHERE {where} ORDER BY v.date DESC, v.id DESC LIMIT ? OFFSET ?", (*params, limit, offset))


def sales_page(statut: str = "", limit: int = 25, date_from: str = "", date_to: str = "", offset: int = 0) -> dict:
    where, params = sale_filter(statut, date_from, date_to)
    return {"items": list_sales(statut, limit, date_from, date_to, offset), "total": int(one(f"SELECT COUNT(*) AS n FROM ventes v WHERE {where}", tuple(params))["n"]), "limit": limit, "offset": offset}


def reference_date() -> str:
    return str(one("SELECT MAX(date) AS d FROM ventes").get("d") or date.today().isoformat())


def kpi(days: int = 30) -> dict:
    period = one(f"SELECT COUNT(*) AS ventes, COALESCE(SUM(montant_ttc),0) AS ca, COALESCE(AVG(montant_ttc),0) AS panier FROM ventes WHERE statut = 'validee' AND date >= date(?, '-{int(days)} day')", (reference_date(),))
    return {"ca": money(period["ca"]), "ventes": int(period["ventes"]), "panier": money(period["panier"]), "days": int(days), "aujourdhui": int(one("SELECT COUNT(*) AS n FROM ventes WHERE date = ?", (date.today().isoformat(),))["n"]), "reference": reference_date(), "ruptures": int(one("SELECT COUNT(*) AS n FROM produits WHERE stock_actuel <= seuil")["n"]), "valeur_stock": money(one("SELECT SUM(prix_public * stock_actuel) AS v FROM produits")["v"] or 0)}


def alerts(limit: int = 12) -> list[dict]:
    return [decorate(row) for row in read("SELECT * FROM produits WHERE stock_actuel <= seuil ORDER BY stock_actuel - seuil, nom LIMIT ?", (limit,))]


def top_products(limit: int = 5) -> list[dict]:
    return read("SELECT p.nom, SUM(l.quantite) AS quantite, ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS ca FROM lignes_vente l JOIN produits p ON p.cip = l.cip JOIN ventes v ON v.id = l.vente_id WHERE v.statut = 'validee' GROUP BY p.nom ORDER BY ca DESC LIMIT ?", (limit,))


def pharmacies() -> list[dict]:
    return read("SELECT o.id, o.nom, o.ville, o.region, o.surface_m2, COUNT(v.id) AS ventes, COALESCE(ROUND(SUM(CASE WHEN v.statut = 'validee' THEN v.montant_ttc ELSE 0 END), 2), 0) AS ca, COALESCE(ROUND(AVG(CASE WHEN v.statut = 'validee' THEN v.montant_ttc END), 2), 0) AS panier FROM officines o LEFT JOIN ventes v ON v.officine_id = o.id GROUP BY o.id ORDER BY ca DESC")


def journal(limit: int = 20) -> list[dict]:
    return read("SELECT id, ts, acteur, action, cible, details FROM journal ORDER BY id DESC LIMIT ?", (limit,))


def overview(days: int = 30) -> dict:
    return {"kpi": kpi(days), "alerts": alerts(6), "top": top_products(5), "recent": list_sales("", 8), "journal": journal(6), "categories": categories()}
