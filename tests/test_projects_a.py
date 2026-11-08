"""Тесты проектов P01–P04: требования, SQL Lab, противоречия, граничные сценарии."""

from projects.p01_requirements.logic import build as build_criteria
from projects.p02_sql_lab.logic import detect, query, safe_run
from projects.p03_conflicts.logic import scan
from projects.p04_edge_cases.logic import generate

STORY_FR = "En tant que pharmacien je veux délivrer une ordonnance partiellement afin de ne pas bloquer le patient"
STORY_RU = "Как фармацевт я хочу видеть остаток препарата при продаже"
SPEC = "La remise maximale autorisée est de 30 % du prix public. Rupture quand le stock disponible est nul."


def test_p01_detects_french_language() -> None:
    assert build_criteria(STORY_FR)["language"] == "fr"


def test_p01_detects_russian_language() -> None:
    assert build_criteria(STORY_RU)["language"] == "ru"


def test_p01_returns_given_when_then() -> None:
    assert set(build_criteria(STORY_FR)["criteria"][0]) >= {"given", "when", "then", "source"}


def test_p01_actor_is_not_the_whole_story() -> None:
    assert build_criteria(STORY_FR)["actor"] == "pharmacien"


def test_p01_verification_reports_support() -> None:
    assert build_criteria(STORY_FR)["verification"]["score"] > 0.3


def test_p02_detects_revenue_intent() -> None:
    assert detect("Топ-10 препаратов по выручке") == "top_produits"


def test_p02_detects_stock_intent() -> None:
    assert detect("Что ниже порога пополнения") == "stock"


def test_p02_unknown_question_is_handled() -> None:
    assert query("погода в Париже")["intent"] == ""


def test_p02_query_returns_rows() -> None:
    assert len(query("Средний чек по городам")["rows"]) == 12


def test_p02_guard_blocks_mutation() -> None:
    assert safe_run("DELETE FROM ventes")["ok"] is False


def test_p02_guard_allows_select() -> None:
    assert safe_run("SELECT nom FROM produits LIMIT 3")["ok"] is True


def test_p03_finds_discount_conflict() -> None:
    values = {tuple(sorted([c["left"]["value"], c["right"]["value"]])) for c in scan()["conflicts"]}
    assert ("20 %", "30 %") in values


def test_p03_finds_tls_conflict() -> None:
    topics = {c["topic"] for c in scan()["conflicts"]}
    assert "Минимальная версия TLS" in topics


def test_p03_summary_counts_high() -> None:
    assert scan()["summary"]["high"] >= 3


def test_p04_generates_boundary_around_threshold() -> None:
    titles = " ".join(case["title"] for case in generate(SPEC)["cases"])
    assert "29,9 %" in titles and "30,1 %" in titles


def test_p04_matches_stock_preset() -> None:
    categories = {case["category"] for case in generate(SPEC)["cases"]}
    assert "конкурентность" in categories


def test_p04_assigns_p1_priority() -> None:
    assert generate(SPEC)["summary"]["p1"] >= 1
