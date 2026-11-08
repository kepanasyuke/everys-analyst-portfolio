"""P02 — SQL Lab: вопрос на бизнес-языке превращается в безопасный SELECT."""

from __future__ import annotations

import re
import sqlite3

from app.ai.text import normalize
from app.core.store import connect

MAX_ROWS = 50
FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|pragma|vacuum)\b", re.I)

INTENTS = {
    "top_produits": {
        "keywords": ("топ", "лидер", "выручк", "оборот", "meilleur", "chiffre", "ca ", "top"),
        "label": "Топ-10 препаратов по выручке",
        "sql": "SELECT p.nom AS produit, p.categorie, ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS ca FROM lignes_vente l JOIN produits p ON p.cip = l.cip JOIN ventes v ON v.id = l.vente_id WHERE v.statut = 'validee' GROUP BY p.nom, p.categorie ORDER BY ca DESC LIMIT 10",
        "chart": "bar",
        "insight": "Концентрация выручки в топ-10 показывает зависимость аптечной сети от узкого ассортимента.",
    },
    "panier_ville": {
        "keywords": ("чек", "панель", "panier", "город", "ville", "средн"),
        "label": "Средний чек по городам",
        "sql": "SELECT o.ville, COUNT(*) AS ventes, ROUND(AVG(v.montant_ttc), 2) AS panier_moyen FROM ventes v JOIN officines o ON o.id = v.officine_id WHERE v.statut = 'validee' GROUP BY o.ville ORDER BY panier_moyen DESC",
        "chart": "bar",
        "insight": "Разброс среднего чека по городам задаёт приоритет для локальных акций.",
    },
    "remise": {
        "keywords": ("скидк", "remise", "дисконт", "промо"),
        "label": "Влияние скидки на чек",
        "sql": "SELECT v.remise_pct AS remise, COUNT(*) AS ventes, ROUND(AVG(v.montant_ttc), 2) AS panier FROM ventes v WHERE v.statut = 'validee' GROUP BY v.remise_pct ORDER BY v.remise_pct",
        "chart": "bar",
        "insight": "Рост чека при скидке не означает рост маржи — нужен A/B тест (проект P05).",
    },
    "stock": {
        "keywords": ("остат", "склад", "stock", "дефицит", "порог", "seuil", "пополн"),
        "label": "Позиции ниже порога пополнения",
        "sql": "SELECT p.nom AS produit, p.stock_actuel AS stock, p.seuil, p.stock_actuel - p.seuil AS ecart FROM produits p WHERE p.stock_actuel <= p.seuil ORDER BY ecart ASC, p.nom LIMIT 15",
        "chart": "table",
        "insight": "Отрицательный ecart — прямой кандидат на срочный дозаказ до открытия смены.",
    },
    "canal": {
        "keywords": ("канал", "canal", "drive", "доставк", "livraison", "comptoir"),
        "label": "Распределение продаж по каналам",
        "sql": "SELECT canal, COUNT(*) AS ventes, ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM ventes), 1) AS доля FROM ventes GROUP BY canal ORDER BY ventes DESC",
        "chart": "bar",
        "insight": "Доля drive и livraison определяет требования к упаковке и логистике заказа.",
    },
    "remboursement": {
        "keywords": ("возмещ", "страхов", "rembours", "taux", "tiers", "касс"),
        "label": "Структура продаж по ставке возмещения",
        "sql": "SELECT p.taux_remboursement AS taux, COUNT(*) AS lignes, ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS montant FROM lignes_vente l JOIN produits p ON p.cip = l.cip GROUP BY p.taux_remboursement ORDER BY montant DESC",
        "chart": "bar",
        "insight": "Доля строк с taux = 0 показывает зависимость от парафармацевтики и наценки.",
    },
    "mois": {
        "keywords": ("месяц", "динамик", "тренд", "mois", "evolution", "динамика"),
        "label": "Выручка по месяцам",
        "sql": "SELECT substr(v.date, 1, 7) AS месяц, COUNT(*) AS ventes, ROUND(SUM(v.montant_ttc), 2) AS выручка FROM ventes v WHERE v.statut = 'validee' GROUP BY substr(v.date, 1, 7) ORDER BY месяц",
        "chart": "line",
        "insight": "Сезонность важнее среднего: планирование промо привязано к пику месяца.",
    },
    "statuts": {
        "keywords": ("статус", "отмен", "statut", "annul", "незаверш"),
        "label": "Статусы продаж",
        "sql": "SELECT statut, COUNT(*) AS ventes, ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM ventes), 1) AS доля FROM ventes GROUP BY statut ORDER BY ventes DESC",
        "chart": "bar",
        "insight": "Доля annulee — индикатор проблем на кассе, а не поведения покупателей.",
    },
    "thermo": {
        "keywords": ("холод", "температур", "froid", "thermo", "вакцин"),
        "label": "Термолабильные позиции",
        "sql": "SELECT p.nom AS produit, p.stock_actuel AS stock, p.seuil, p.taux_remboursement AS taux FROM produits p WHERE p.thermosensible = 1 ORDER BY p.stock_actuel ASC",
        "chart": "table",
        "insight": "Остаток ниже порога у термолабильных позиций — риск нарушения холодовой цепи.",
    },
}


def detect(question: str) -> str:
    name, score = best_match(normalize(question).lower())
    return name if score else ""


def best_match(low: str) -> tuple[str, int]:
    scored = [(name, sum(1 for k in spec["keywords"] if k in low)) for name, spec in INTENTS.items()]
    return max(scored, key=lambda pair: pair[1])


def guard(sql: str) -> dict:
    return {"ok": not FORBIDDEN.search(sql), "read_only": True, "limit": MAX_ROWS}


def run(sql: str) -> tuple[list[str], list[list]]:
    with connect() as connection:
        cursor = connection.execute(sql)
        rows = cursor.fetchmany(MAX_ROWS)
    return [d[0] for d in cursor.description], [list(r) for r in rows]


def chart_for(intent: str, columns: list[str], rows: list[list]) -> dict:
    return {"type": INTENTS[intent]["chart"], "x": [str(r[0]) for r in rows], "y": [float(r[1]) if isinstance(r[1], (int, float)) else 0.0 for r in rows], "label": INTENTS[intent]["label"]}


def explain(intent: str, rows: list[list]) -> list[str]:
    return [INTENTS[intent]["insight"], f"Строк в результате: {len(rows)}", f"Запрос ограничен {MAX_ROWS} строками и работает в режиме read-only."]


def query(question: str) -> dict:
    intent = detect(question)
    return result(question, intent) if intent else unknown(question)


def result(question: str, intent: str) -> dict:
    columns, rows = run(INTENTS[intent]["sql"])
    return {"question": question, "intent": intent, "label": INTENTS[intent]["label"], "sql": INTENTS[intent]["sql"], "columns": columns, "rows": rows, "chart": chart_for(intent, columns, rows), "explanation": explain(intent, rows), "safety": guard(INTENTS[intent]["sql"])}


def unknown(question: str) -> dict:
    return {"question": question, "intent": "", "label": "Интент не распознан", "sql": "", "columns": [], "rows": [], "chart": {"type": "table", "x": [], "y": [], "label": ""}, "explanation": ["Уточните вопрос: препарат, город, скидка, остаток, канал, возмещение, месяц, статус или холодовая цепь."], "safety": guard(""), "suggestions": [INTENTS[k]["label"] for k in INTENTS]}


def safe_error(question: str, error: Exception) -> dict:
    return {"question": question, "intent": "", "label": "Ошибка выполнения", "sql": "", "rows": [], "columns": [], "error": str(error)[:200]}


def schema() -> list[dict]:
    with connect() as connection:
        names = [r["name"] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return [{"table": n, "columns": [c["name"] for c in connect().execute(f"PRAGMA table_info({n})")]} for n in names]


def safe_run(sql: str) -> dict:
    return execute(sql) if guard(sql)["ok"] else {"ok": False, "error": "Разрешены только SELECT-запросы", "columns": [], "rows": []}


def execute(sql: str) -> dict:
    columns, rows, error = probe(sql)
    return {"ok": not error, "error": error, "columns": columns, "rows": rows}


def probe(sql: str) -> tuple[list, list, str]:
    try:
        columns, rows = run(sql)
        error = ""
    except sqlite3.Error as exc:
        columns, rows, error = [], [], str(exc)[:200]
    return columns, rows, error
