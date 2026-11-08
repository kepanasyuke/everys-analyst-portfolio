"""Тесты приложения офисины: каталог, касса, склад, отмена, журнал.

Каждый тест работает на копии демо-базы, поэтому прогон не портит данные портфолио.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.core.store import DB as DEMO_DB
from app.officine import logic, repo
from app.officine.errors import OfficineError

CIP = "3400939999999"


def copied(tmp_path: Path) -> Path:
    return duplicated(tmp_path / "officine.db")


def duplicated(target: Path) -> Path:
    shutil.copy(DEMO_DB, target)
    return target


def bound(monkeypatch, target: Path) -> Path:
    monkeypatch.setattr(repo, "DB", target)
    return initialized(target)


def initialized(target: Path) -> Path:
    repo.ensure_schema()
    return target


@pytest.fixture()
def database(tmp_path, monkeypatch):
    return bound(monkeypatch, copied(tmp_path))


def sample_product(**overrides) -> dict:
    base = {"cip": CIP, "nom": "Test Paracetamol", "dci": "paracetamol", "categorie": "antalgique", "prix_public": 3.5, "taux_remboursement": 65, "thermosensible": False, "stock_actuel": 10, "seuil": 4}
    return {**base, **overrides}


def refusal(call) -> OfficineError:
    with pytest.raises(OfficineError) as error:
        call()
    return error.value


def stock_of(cip: str) -> int:
    return next(item["stock_actuel"] for item in logic.list_products()["items"] if item["cip"] == cip)


def status_of(cip: str) -> str:
    return next(item["statut_stock"] for item in logic.list_products()["items"] if item["cip"] == cip)


def first_product() -> dict:
    return logic.list_products()["items"][0]


def sold(cip: str, quantite: int) -> dict:
    return logic.create_sale({"officine_id": 1, "lignes": [{"cip": cip, "quantite": quantite}]})


def merged(cip: str) -> tuple:
    sale = logic.create_sale({"officine_id": 1, "lignes": [{"cip": cip, "quantite": 2}, {"cip": cip, "quantite": 1}]})
    return (len(sale["lignes"]), sale["lignes"][0]["quantite"])


def cancelled(cip: str, quantite: int) -> dict:
    return logic.cancel_sale(sold(cip, quantite)["id"])


def cancelled_twice(cip: str) -> dict:
    return logic.cancel_sale(cancelled(cip, 1)["id"])


def deleted_after_sale(cip: str) -> dict:
    sold(cip, 1)
    return logic.delete_product(cip)


def recorded(call) -> list:
    call()
    return [row["action"] for row in logic.journal(10)]


def test_create_product_appears_in_catalog(database) -> None:
    logic.create_product(sample_product())
    assert any(item["cip"] == CIP for item in logic.list_products("Test")["items"])


def test_create_product_rejects_short_cip(database) -> None:
    assert refusal(lambda: logic.create_product(sample_product(cip="123"))).status == 422


def test_create_product_rejects_duplicate(database) -> None:
    logic.create_product(sample_product())
    assert refusal(lambda: logic.create_product(sample_product(nom="Дубль"))).status == 409


def test_patch_product_price(database) -> None:
    logic.create_product(sample_product())
    assert logic.update_product(CIP, {"prix_public": 4.2})["prix_public"] == 4.2


def test_patch_rejects_negative_stock(database) -> None:
    logic.create_product(sample_product())
    assert refusal(lambda: logic.update_product(CIP, {"stock_actuel": -5})).status == 422


def test_restock_increments_stock(database) -> None:
    logic.create_product(sample_product())
    assert logic.restock(CIP, 7)["stock_actuel"] == 17


def test_restock_rejects_zero(database) -> None:
    logic.create_product(sample_product())
    assert refusal(lambda: logic.restock(CIP, 0)).status == 422


def test_sale_decrements_stock(database) -> None:
    logic.create_product(sample_product())
    assert (sold(CIP, 3)["montant_ttc"], stock_of(CIP)) == (10.5, 7)


def test_sale_total_applies_discount(database) -> None:
    logic.create_product(sample_product(prix_public=10))
    assert logic.create_sale({"officine_id": 1, "remise_pct": 10, "lignes": [{"cip": CIP, "quantite": 2}]})["montant_ttc"] == 18.0


def test_sale_merges_duplicate_lines(database) -> None:
    logic.create_product(sample_product())
    assert merged(CIP) == (1, 3)


def test_sale_rejects_insufficient_stock(database) -> None:
    logic.create_product(sample_product(stock_actuel=2))
    assert refusal(lambda: sold(CIP, 5)).status == 409


def test_failed_sale_keeps_stock_intact(database) -> None:
    logic.create_product(sample_product(stock_actuel=2))
    assert (refusal(lambda: sold(CIP, 5)).status, stock_of(CIP)) == (409, 2)


def test_sale_rejects_remise_above_limit(database) -> None:
    logic.create_product(sample_product())
    assert "титуляра" in refusal(lambda: logic.create_sale({"officine_id": 1, "remise_pct": 40, "lignes": [{"cip": CIP, "quantite": 1}]})).message


def test_sale_rejects_empty_basket(database) -> None:
    assert refusal(lambda: logic.create_sale({"officine_id": 1, "lignes": []})).status == 422


def test_sale_rejects_unknown_officine(database) -> None:
    logic.create_product(sample_product())
    assert refusal(lambda: logic.create_sale({"officine_id": 999, "lignes": [{"cip": CIP, "quantite": 1}]})).status == 404


def test_cancel_restores_stock(database) -> None:
    logic.create_product(sample_product())
    assert (cancelled(CIP, 4)["statut"], stock_of(CIP)) == ("annulee", 10)


def test_double_cancel_is_rejected(database) -> None:
    logic.create_product(sample_product())
    assert refusal(lambda: cancelled_twice(CIP)).status == 409


def test_delete_product_without_sales(database) -> None:
    logic.create_product(sample_product())
    assert logic.delete_product(CIP)["ok"] is True


def test_delete_sold_product_is_forbidden(database) -> None:
    logic.create_product(sample_product())
    assert refusal(lambda: deleted_after_sale(CIP)).status == 409


def test_journal_records_sale(database) -> None:
    logic.create_product(sample_product())
    assert "sale.create" in recorded(lambda: sold(CIP, 1))


def test_journal_records_cancel(database) -> None:
    logic.create_product(sample_product())
    assert "sale.cancel" in recorded(lambda: cancelled(CIP, 1))


def test_pharmacies_list_has_twelve_rows(database) -> None:
    assert len(logic.pharmacies()) == 12


def test_kpi_has_positive_revenue(database) -> None:
    assert logic.kpi()["ca"] > 0


def test_overview_contains_key_blocks(database) -> None:
    assert {"kpi", "alerts", "top", "recent", "journal"} <= set(logic.overview())


def test_product_status_marks_rupture(database) -> None:
    logic.create_product(sample_product(stock_actuel=0))
    assert status_of(CIP) == "rupture"


def test_list_products_filters_by_category(database) -> None:
    assert all(item["categorie"] == "antalgique" for item in logic.list_products(category="antalgique")["items"])


def test_first_product_is_available(database) -> None:
    assert first_product()["cip"]
