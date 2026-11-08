"""Тесты проектов P05–P08: A/B-тест, интеграции, релизный гейт, глоссарий."""

from projects.p05_ab_lab.logic import compute, p_value, sample_size, z_score
from projects.p06_integration_watch.logic import SOAP_SAMPLE, is_private, run, soap_check, validated
from projects.p07_release_gate.logic import assess, catalog
from projects.p08_glossary.logic import annotate, lookup, overview


def test_p05_z_score_positive_when_b_better() -> None:
    assert z_score(0.20, 2400, 0.22, 2400) > 0


def test_p05_p_value_of_zero_is_one() -> None:
    assert p_value(0.0) == 1.0


def test_p05_p_value_of_196_is_about_005() -> None:
    assert abs(p_value(1.96) - 0.05) < 0.001


def test_p05_compute_marks_significance() -> None:
    assert compute(2400, 480, 2400, 528)["significant"] is False


def test_p05_strong_effect_is_significant() -> None:
    assert compute(5000, 900, 5000, 1200)["significant"] is True


def test_p05_ci_contains_observed_diff() -> None:
    result = compute(2400, 480, 2400, 528)
    assert result["ci"]["low"] <= result["diff_pp"] / 100 <= result["ci"]["high"]


def test_p05_sample_size_grows_when_mde_shrinks() -> None:
    assert sample_size(0.2, 0.05) > sample_size(0.2, 0.2)


def test_p06_soap_sample_is_valid() -> None:
    assert soap_check(SOAP_SAMPLE)["valid"] is True


def test_p06_soap_without_body_is_invalid() -> None:
    assert soap_check("<soap:Envelope><soap:Header/></soap:Envelope>")["valid"] is False


def test_p06_private_host_is_blocked() -> None:
    assert validated("https://127.0.0.1:8077/")["ok"] is False


def test_p06_http_is_blocked() -> None:
    assert validated("http://example.com/")["ok"] is False


def test_p06_public_https_is_allowed() -> None:
    assert validated("https://www.winpharma.com/")["ok"] is True


def test_p06_demo_run_returns_three_targets() -> None:
    assert len(run()["results"]) == 3


def test_p06_demo_has_blocked_target() -> None:
    assert run()["summary"]["blocked"] == 1


def test_p06_is_private_detects_loopback() -> None:
    assert is_private("https://localhost/api") is True


def test_p07_default_release_is_no_go() -> None:
    assert assess()["verdict"] == "no-go"


def test_p07_all_done_release_is_go() -> None:
    statuses = {gate["id"]: "done" for gate in catalog()}
    assert assess(statuses)["verdict"] == "go"


def test_p07_missing_blocker_still_no_go() -> None:
    statuses = {gate["id"]: "done" for gate in catalog()} | {"rollback": "fail"}
    assert assess(statuses)["score"] < 100


def test_p07_sign_off_mentions_version() -> None:
    assert "2026.1" in assess({}, "2026.1")["sign_off_ru"]


def test_p08_lookup_finds_french_term() -> None:
    assert lookup("remise")["matches"][0]["fr"] == "remise"


def test_p08_lookup_finds_russian_term() -> None:
    assert lookup("скидка")["matches"][0]["ru"] == "скидка"


def test_p08_lookup_reports_missing_term() -> None:
    assert lookup("ксерокс")["missing"] is True


def test_p08_annotate_finds_two_terms() -> None:
    assert len(annotate("La créance rejetée et l'ordonnance en tiers payant")["terms"]) >= 2


def test_p08_overview_counts_thirty_terms() -> None:
    assert overview()["terms"] >= 30
