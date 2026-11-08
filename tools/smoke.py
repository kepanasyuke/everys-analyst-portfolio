"""Дымовой прогон всех 8 API-проектов без поднятия сервера (FastAPI TestClient)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from projects.p06_integration_watch.logic import SOAP_SAMPLE

client = TestClient(app)

CHECKS: list[tuple[str, str, str | None, dict | None]] = [
    ("health", "get", "/api/health", None),
    ("catalog", "get", "/api/catalog", None),
    ("p01 requirements", "post", "/api/p01/generate", {"story": "En tant que pharmacien je veux délivrer une ordonnance partiellement"}),
    ("p02 sql query", "post", "/api/p02/query", {"question": "Топ-10 препаратов по выручке"}),
    ("p02 sql guard", "post", "/api/p02/raw", {"sql": "DELETE FROM ventes"}),
    ("p03 conflicts", "post", "/api/p03/scan", {"min_severity": "high"}),
    ("p04 edge cases", "post", "/api/p04/generate", {"spec": "La remise maximale autorisée est de 30 % du prix public."}),
    ("p05 ab test", "post", "/api/p05/test", {"visitors_a": 2400, "conversions_a": 480, "visitors_b": 2400, "conversions_b": 528}),
    ("p06 probe demo", "post", "/api/p06/probe", {"targets": [], "simulate": True}),
    ("p06 soap", "post", "/api/p06/soap", {"xml": SOAP_SAMPLE}),
    ("p07 release gate", "post", "/api/p07/assess", {"version": "2026.1", "gates": []}),
    ("p08 search", "get", "/api/p08/search?q=remise", None),
    ("p08 overview", "get", "/api/p08/overview", None),
    ("index page", "get", "/", None),
]


def call(spec: tuple) -> dict:
    name, response = dispatch(spec)
    return {"name": name, "status": response.status_code, "keys": keys_of(response)}


def dispatch(spec: tuple) -> tuple:
    name, method, path, body = spec
    return name, client.get(path) if method == "get" else client.post(path, json=body)


def keys_of(response) -> list[str]:
    return list(response.json())[:6] if response.headers.get("content-type", "").startswith("application/json") else []


def report(rows: list[dict]) -> int:
    print("\n".join(f"{row['name']:20} {row['status']} {row['keys']}" for row in rows))
    return 0 if all(row["status"] == 200 for row in rows) else 1


def main() -> int:
    return report([call(spec) for spec in CHECKS])


if __name__ == "__main__":
    raise SystemExit(main())
