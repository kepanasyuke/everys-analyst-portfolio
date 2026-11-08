"""Генерация демонстрационной базы аптечной сети (SQLite) для проекта 02 — SQL Lab.

Данные детерминированы: seed=20261108, поэтому цифры в README воспроизводимы.
Запуск: python tools/seed.py
"""

from __future__ import annotations

import datetime as dt
import random
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "officine.db"
START = dt.date(2026, 1, 1)
SALES = 1400
SEED = 20261108

VILLES = [
    ("Rennes", "Bretagne"),
    ("Brest", "Bretagne"),
    ("Quimper", "Bretagne"),
    ("Nantes", "Pays de la Loire"),
    ("Angers", "Pays de la Loire"),
    ("Le Mans", "Pays de la Loire"),
    ("Bordeaux", "Nouvelle-Aquitaine"),
    ("Paris 11", "Ile-de-France"),
    ("Lyon", "Auvergne-Rhone-Alpes"),
    ("Marseille", "PACA"),
    ("Fort-de-France", "Martinique"),
    ("Papeete", "Polynesie"),
]

PRODUITS = [
    ("Doliprane 1000 mg", "paracetamol", "antalgique", 2.18, 65, False),
    ("Efferalgan 500 mg", "paracetamol", "antalgique", 1.94, 65, False),
    ("Ibuprofene 400 mg", "ibuprofene", "antalgique", 2.45, 65, False),
    ("Amoxicilline 1 g", "amoxicilline", "antibiotique", 4.80, 65, False),
    ("Augmentin 1 g", "amoxicilline", "antibiotique", 6.35, 65, False),
    ("Clamoxyl 500 mg", "amoxicilline", "antibiotique", 3.90, 65, False),
    ("Kardegic 75 mg", "acetylsalicylate", "cardiologie", 2.60, 65, False),
    ("Amlodipine 5 mg", "amlodipine", "cardiologie", 3.15, 65, False),
    ("Bisoprolol 5 mg", "bisoprolol", "cardiologie", 3.05, 65, False),
    ("Levothyrox 75", "levothyroxine", "endocrinologie", 4.10, 100, False),
    ("Metformine 850 mg", "metformine", "diabete", 3.55, 65, False),
    ("Insuline Lantus", "insuline glargine", "diabete", 38.90, 65, True),
    ("Ventoline 100", "salbutamol", "pneumologie", 5.20, 65, False),
    ("Seretide 250", "fluticasone", "pneumologie", 29.40, 65, False),
    ("Omeprazole 20 mg", "omeprazole", "gastro", 3.30, 65, False),
    ("Smecta 3 g", "diosmectite", "gastro", 4.15, 30, False),
    ("Imodium 2 mg", "loperamide", "gastro", 3.85, 0, False),
    ("Doliprane pediatrique", "paracetamol", "pediatrie", 2.05, 65, False),
    ("Toplexil", "oxomemazine", "ORL", 4.60, 30, False),
    ("Rhinofluimucil", "tuaminoheptane", "ORL", 5.10, 30, False),
    ("Coversyl 5 mg", "perindopril", "cardiologie", 4.95, 65, False),
    ("Xanax 0,25 mg", "alprazolam", "psychiatrie", 3.70, 65, False),
    ("Zolpidem 10 mg", "zolpidem", "psychiatrie", 3.40, 65, False),
    ("Skintest dermocosmetique", "cosmetique", "parapharmacie", 12.90, 0, False),
    ("Biafine 185 g", "trolamine", "dermatologie", 8.40, 0, False),
    ("Sérum physiologique 5 ml", "chlorure de sodium", "soin", 2.30, 0, False),
    ("Vitascorbol 500", "acide ascorbique", "vitamines", 3.20, 0, False),
    ("Magnesium B6", "magnesium", "vitamines", 6.75, 0, False),
    ("Vaccin grippe saisonniere", "vaccin grippe", "vaccin", 9.80, 65, True),
    ("Vaccin ROR", "vaccin rougeole", "vaccin", 24.50, 65, True),
]

CANAUX = ["comptoir", "comptoir", "comptoir", "drive", "livraison"]
REMISES = [0, 0, 0, 0, 5, 10, 20]
STATUTS = ["validee", "validee", "validee", "validee", "validee", "annulee", "en_attente"]
SCHEMA = """
DROP TABLE IF EXISTS lignes_retour;
DROP TABLE IF EXISTS retours;
DROP TABLE IF EXISTS journal;
DROP TABLE IF EXISTS lignes_vente;
DROP TABLE IF EXISTS ventes;
DROP TABLE IF EXISTS produits;
DROP TABLE IF EXISTS officines;

CREATE TABLE officines (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    ville TEXT NOT NULL,
    region TEXT NOT NULL,
    surface_m2 INTEGER NOT NULL CHECK (surface_m2 > 0)
);

CREATE TABLE produits (
    cip TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    dci TEXT NOT NULL,
    categorie TEXT NOT NULL,
    prix_public REAL NOT NULL CHECK (prix_public > 0),
    taux_remboursement INTEGER NOT NULL CHECK (taux_remboursement BETWEEN 0 AND 100),
    thermosensible INTEGER NOT NULL CHECK (thermosensible IN (0, 1)),
    stock_actuel INTEGER NOT NULL CHECK (stock_actuel >= 0),
    seuil INTEGER NOT NULL CHECK (seuil >= 0)
);

CREATE TABLE ventes (
    id INTEGER PRIMARY KEY,
    officine_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    canal TEXT NOT NULL,
    statut TEXT NOT NULL CHECK (statut IN ('validee', 'annulee', 'en_attente')),
    remise_pct INTEGER NOT NULL CHECK (remise_pct BETWEEN 0 AND 100),
    montant_ttc REAL NOT NULL CHECK (montant_ttc >= 0),
    FOREIGN KEY (officine_id) REFERENCES officines (id)
);

CREATE TABLE lignes_vente (
    id INTEGER PRIMARY KEY,
    vente_id INTEGER NOT NULL,
    cip TEXT NOT NULL,
    quantite INTEGER NOT NULL CHECK (quantite > 0),
    prix_unitaire REAL NOT NULL CHECK (prix_unitaire >= 0),
    FOREIGN KEY (vente_id) REFERENCES ventes (id),
    FOREIGN KEY (cip) REFERENCES produits (cip)
);
"""


def rng():
    return random.Random(SEED)


RANDOM = rng()


def officines() -> list[tuple]:
    return [(i + 1, f"Officine {v[0]}", v[0], v[1], 95 + i * 7) for i, v in enumerate(VILLES)]


def produits() -> list[tuple]:
    return [
        (f"340093{i:07d}", nom, dci, cat, prix, taux, int(thermo), RANDOM.randint(0, 320), RANDOM.choice([10, 15, 20, 25]))
        for i, (nom, dci, cat, prix, taux, thermo) in enumerate(PRODUITS, start=1)
    ]


def date_of(index: int) -> str:
    return (START + dt.timedelta(days=int(index * 300 / SALES))).isoformat()


def sale(index: int) -> dict:
    head = {
        "id": index + 1,
        "officine_id": RANDOM.randint(1, len(VILLES)),
        "date": date_of(index),
        "canal": RANDOM.choice(CANAUX),
        "statut": RANDOM.choice(STATUTS),
        "remise_pct": RANDOM.choice(REMISES),
    }
    return {**head, "lignes": lines(head)}


def lines(head: dict) -> list[dict]:
    chosen = [RANDOM.choice(PRODUITS) for _ in range(RANDOM.randint(1, 4))]
    return [{"cip": f"340093{PRODUITS.index(p) + 1:07d}", "quantite": RANDOM.choice([1, 1, 1, 2, 3]), "prix": p[3]} for p in chosen]


def montant(head: dict) -> float:
    return round(sum(l["prix"] * l["quantite"] for l in head["lignes"]) * (1 - head["remise_pct"] / 100), 2)


def vente_rows(sales: list[dict]) -> list[tuple]:
    return [(s["id"], s["officine_id"], s["date"], s["canal"], s["statut"], s["remise_pct"], montant(s)) for s in sales]


def ligne_rows(sales: list[dict]) -> list[tuple]:
    flat = [(s["id"], l) for s in sales for l in s["lignes"]]
    return [(i + 1, vente_id, l["cip"], l["quantite"], l["prix"]) for i, (vente_id, l) in enumerate(flat)]


if __name__ == "__main__":
    ROWS = [sale(i) for i in range(SALES)]
    with sqlite3.connect(DB) as connection:
        connection.executescript(SCHEMA)
        connection.executemany("INSERT INTO officines VALUES (?,?,?,?,?)", officines())
        connection.executemany("INSERT INTO produits VALUES (?,?,?,?,?,?,?,?,?)", produits())
        connection.executemany("INSERT INTO ventes VALUES (?,?,?,?,?,?,?)", vente_rows(ROWS))
        connection.executemany("INSERT INTO lignes_vente VALUES (?,?,?,?,?)", ligne_rows(ROWS))
    print(f"OK {DB} | ventes={len(ROWS)} | lignes={sum(len(s['lignes']) for s in ROWS)}")
