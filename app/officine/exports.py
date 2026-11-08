"""Выгрузки CSV: продажи за период и справочник товаров (разделитель «;», BOM для Excel)."""

from __future__ import annotations

import csv
import io

from app.officine import logic
from app.officine.repo import read

SALES_HEADER = ("id", "date", "officine", "ville", "canal", "statut", "remise_pct", "montant_ttc")
PRODUCT_HEADER = ("cip", "nom", "dci", "categorie", "prix_public", "taux_remboursement", "stock_actuel", "seuil", "thermosensible")
ROW_LIMIT = 5000


def rendered(buffer, header: tuple, rows: list[dict]) -> str:
    return filled(buffer, csv.writer(buffer, delimiter=";", lineterminator="\r\n"), header, rows)


def filled(buffer, writer, header: tuple, rows: list[dict]) -> str:
    [writer.writerow(header), *[writer.writerow([row.get(key, "") for key in header]) for row in rows]]
    return "\ufeff" + buffer.getvalue()


def to_csv(header: tuple, rows: list[dict]) -> str:
    return rendered(io.StringIO(), header, rows)


def sales_csv(date_from: str = "", date_to: str = "") -> str:
    where, params = logic.sale_filter("", date_from, date_to)
    return to_csv(SALES_HEADER, read(f"{logic.SALE_BASE} WHERE {where} ORDER BY v.date DESC, v.id DESC LIMIT {ROW_LIMIT}", tuple(params)))


def products_csv() -> str:
    return to_csv(PRODUCT_HEADER, read("SELECT * FROM produits ORDER BY nom"))
