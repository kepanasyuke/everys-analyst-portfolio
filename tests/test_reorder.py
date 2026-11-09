"""Тесты пополнения по порогам: расчёт потребности, массовый заказ, журнал."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.core.store import DB as DEMO_DB
from app.officine import logic, reorder, repo
from app.officine.errors import OfficineError

CIP = "3400939990002"


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
def database(tmp_path, monkeypatch):
    return bound(monkeypatch, duplicated(tmp_path / "officine.db"))


def empty_product(**overrides) -> dict:
    base = {"cip": CIP, "nom": "Reorder Test", "dci": "test", "categorie": "antalgique", "prix_public": 4.0, "stock_actuel": 0, "seuil": 10}
    return {**base, **overrides}


def created(**overrides) -> str:
    logic.create_product(empty_product(**overrides))
    return CIP


def refusal(call) -> OfficineError:
    with pytest.raises(OfficineError) as error:
        call()
    return error.value


def stock_of(cip: str) -> int:
    return next(item["stock_actuel"] for item in logic.list_products()["items"] if item["cip"] == cip)


def proposed(cip: str = CIP) -> dict:
    return next((item for item in reorder.plan()["items"] if item["cip"] == cip), {})


def test_plan_includes_product_below_threshold(database) -> None:
    created(stock_actuel=0)
    assert proposed()["cip"] == CIP


def test_plan_excludes_product_above_threshold(database) -> None:
    created(stock_actuel=50)
    assert proposed() == {}


def test_besoin_is_target_minus_stock(database) -> None:
    created(stock_actuel=3, seuil=10)
    assert proposed()["besoin"] == 17


def test_besoin_has_minimum_order(database) -> None:
    created(stock_actuel=2, seuil=2)
    assert proposed()["besoin"] == 5


def test_plan_summary_counts_ruptures(database) -> None:
    created(stock_actuel=0)
    assert reorder.plan()["summary"]["ruptures"] >= 1


def place_order(quantite: int) -> dict:
    return reorder.create_order({"lignes": [{"cip": CIP, "quantite": quantite}]})


def units_after(quantite: int) -> int:
    place_order(quantite)
    return reorder.recent_orders(1)[0]["units"]


def ordered(quantite: int = 12) -> int:
    created(stock_actuel=0)
    return stock_after_order(quantite)


def stock_after_order(quantite: int) -> int:
    place_order(quantite)
    return stock_of(CIP)


def claimed_units(quantite: int) -> int:
    created(stock_actuel=0)
    return units_after(quantite)


def test_order_increases_stock(database) -> None:
    assert ordered() == 12


def test_order_writes_journal_batch(database) -> None:
    assert claimed_units(12) == 12


def test_order_rejects_unknown_product(database) -> None:
    assert refusal(lambda: reorder.create_order({"lignes": [{"cip": "0000000000000", "quantite": 1}]})).status == 404


def test_order_rejects_empty_basket(database) -> None:
    assert refusal(lambda: reorder.create_order({"lignes": []})).status == 422


def test_order_rejects_zero_quantity(database) -> None:
    created(stock_actuel=0)
    assert refusal(lambda: reorder.create_order({"lignes": [{"cip": CIP, "quantite": 0}]})).status == 422


def journal_after_order() -> list:
    created(stock_actuel=0)
    return filtered_journal()


def filtered_journal() -> list:
    place_order(5)
    return logic.journal(5, "stock.reorder")


def test_journal_filters_by_action(database) -> None:
    assert journal_after_order()[0]["action"] == "stock.reorder"
