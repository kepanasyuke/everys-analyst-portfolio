"""HTTP-тесты приложения офисины: продажи, возвраты, фильтры, выгрузки, чек."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.store import DB as DEMO_DB
from app.main import app
from app.officine import repo

CIP = "3400939990001"


def duplicated(target: Path) -> Path:
    shutil.copy(DEMO_DB, target)
    return target


def initialized(target: Path) -> Path:
    repo.ensure_schema()
    return target


def bound(monkeypatch, target: Path) -> Path:
    monkeypatch.setattr(repo, "DB", target)
    return initialized(target)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    bound(monkeypatch, duplicated(tmp_path / "officine.db"))
    return TestClient(app)


def seeded(client) -> str:
    client.post("/api/app/products", json={"cip": CIP, "nom": "API Test", "dci": "test", "categorie": "antalgique", "prix_public": 5, "stock_actuel": 10, "seuil": 2})
    return CIP


def sold(client, quantite: int = 3) -> dict:
    return client.post("/api/app/sales", json={"officine_id": 1, "lignes": [{"cip": seeded(client), "quantite": quantite}]}).json()


def stock(client) -> int:
    return client.get("/api/app/products", params={"q": "API Test"}).json()["items"][0]["stock_actuel"]


def returned(client, quantite: int, retour: int) -> dict:
    sale = sold(client, quantite)
    return client.post(f"/api/app/sales/{sale['id']}/return", json={"lignes": [{"cip": CIP, "quantite": retour}]}).json()


def stock_after_return(client) -> int:
    returned(client, 4, 1)
    return stock(client)


def discounted_sale(client) -> dict:
    seeded(client)
    return client.post("/api/app/sales", json={"officine_id": 1, "remise_pct": 10, "lignes": [{"cip": CIP, "quantite": 2}]}).json()


def discounted_return(client) -> dict:
    return client.post(f"/api/app/sales/{discounted_sale(client)['id']}/return", json={"lignes": [{"cip": CIP, "quantite": 1}]}).json()


def cancelled_sale(client) -> dict:
    sale = sold(client, 2)
    return client.post(f"/api/app/sales/{sale['id']}/cancel", json={}).json()


def return_of_cancelled(client) -> int:
    return client.post(f"/api/app/sales/{cancelled_sale(client)['id']}/return", json={"lignes": [{"cip": CIP, "quantite": 1}]}).status_code


def returned_sale(client) -> dict:
    sale = sold(client, 2)
    return client.post(f"/api/app/sales/{sale['id']}/return", json={"lignes": [{"cip": CIP, "quantite": 1}]}).json()


def movement_kinds(client) -> set:
    returned_sale(client)
    return {item["kind"] for item in client.get(f"/api/app/products/{CIP}/movements").json()["items"]}


def today() -> str:
    return date.today().isoformat()


def today_sales(client) -> dict:
    sold(client)
    return client.get("/api/app/sales", params={"date_from": today(), "date_to": today()}).json()


def sales_csv(client) -> str:
    sold(client)
    return client.get("/api/app/export/sales.csv").text


def refused_discount(client) -> int:
    seeded(client)
    return client.post("/api/app/sales", json={"officine_id": 1, "remise_pct": 40, "lignes": [{"cip": CIP, "quantite": 1}]}).status_code


def titulaire_sale(client) -> dict:
    seeded(client)
    return client.post("/api/app/sales", json={"officine_id": 1, "remise_pct": 40, "role": "titulaire", "lignes": [{"cip": CIP, "quantite": 2}]}).json()


def test_overview_endpoint_exposes_kpi(client) -> None:
    assert client.get("/api/app/overview").json()["kpi"]["days"] == 30


def test_overview_accepts_period(client) -> None:
    assert client.get("/api/app/overview", params={"days": 7}).json()["kpi"]["days"] == 7


def test_create_sale_returns_lines(client) -> None:
    sale = sold(client)
    assert sale["statut"] == "validee" and sale["montant_ttc"] == 15.0


def test_sale_rejects_ovestock(client) -> None:
    seeded(client)
    assert client.post("/api/app/sales", json={"officine_id": 1, "lignes": [{"cip": CIP, "quantite": 99}]}).status_code == 409


def test_sale_detail_contains_lines(client) -> None:
    sale = sold(client, 2)
    assert len(client.get(f"/api/app/sales/{sale['id']}").json()["lignes"]) == 1


def test_partial_return_restores_stock(client) -> None:
    assert stock_after_return(client) == 7


def test_return_total_respects_discount(client) -> None:
    assert discounted_return(client)["montant"] == 4.5


def test_return_cannot_exceed_sold(client) -> None:
    sale = sold(client, 2)
    assert client.post(f"/api/app/sales/{sale['id']}/return", json={"lignes": [{"cip": CIP, "quantite": 3}]}).status_code == 409


def test_return_blocked_after_cancel(client) -> None:
    assert return_of_cancelled(client) == 409


def test_movements_include_sale_and_return(client) -> None:
    assert {"sale", "return"} <= movement_kinds(client)


def test_movements_for_unknown_product_returns_404(client) -> None:
    assert client.get("/api/app/products/0000000000000/movements").status_code == 404


def test_sales_filter_by_today(client) -> None:
    assert today_sales(client)["total"] >= 1


def test_sales_filter_unknown_status_is_empty(client) -> None:
    assert client.get("/api/app/sales", params={"statut": "zzz"}).json()["total"] == 0


def test_sales_csv_has_bom_and_header(client) -> None:
    text = sales_csv(client)
    assert text.startswith("\ufeff") and "montant_ttc" in text


def test_products_csv_has_header(client) -> None:
    assert "taux_remboursement" in client.get("/api/app/export/products.csv").text


def test_receipt_renders_html(client) -> None:
    sale = sold(client)
    assert f"№ {sale['id']}" in client.get(f"/api/app/sales/{sale['id']}/receipt").text


def test_delete_sold_product_is_refused(client) -> None:
    sold(client, 1)
    assert client.delete(f"/api/app/products/{CIP}").status_code == 409


def test_patch_negative_stock_is_refused(client) -> None:
    seeded(client)
    assert client.patch(f"/api/app/products/{CIP}", json={"stock_actuel": -1}).status_code == 422


def test_discount_above_limit_needs_titulaire(client) -> None:
    assert refused_discount(client) == 409


def test_titulaire_discount_is_accepted(client) -> None:
    sale = titulaire_sale(client)
    assert sale["montant_ttc"] == 6.0 and sale["statut"] == "validee"

def reorder_plan(client) -> dict:
    return client.get("/api/app/reorder").json()


def ordered(client, quantite: int = 5) -> dict:
    seeded(client)
    return client.post("/api/app/reorder", json={"lignes": [{"cip": CIP, "quantite": quantite}]}).json()


def test_reorder_plan_describes_rule(client) -> None:
    assert "порог" in reorder_plan(client)["plan"]["rule"]


def test_reorder_apply_increases_stock(client) -> None:
    ordered(client, 5)
    assert stock(client) == 15


def test_reorder_writes_journal_action(client) -> None:
    ordered(client, 5)
    assert client.get("/api/app/journal", params={"action": "stock.reorder"}).json()["items"][0]["action"] == "stock.reorder"
