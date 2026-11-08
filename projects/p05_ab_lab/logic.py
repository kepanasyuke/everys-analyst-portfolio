"""P05 — A/B Lab: двухпропорциональный z-тест, доверительный интервал и размер выборки."""

from __future__ import annotations

from math import erf, sqrt

Z_ALPHA = {0.1: 1.644854, 0.05: 1.959964, 0.01: 2.575829}
Z_POWER = {0.8: 0.841621, 0.9: 1.281552}
SCENARIOS = [
    {"label": "Скидка 20 % по умолчанию в кассе", "a": [2400, 480], "b": [2400, 528], "baseline": 0.2, "mde": 0.1},
    {"label": "Подсказка о дженерике на экране выдачи", "a": [1800, 216], "b": [1810, 262], "baseline": 0.12, "mde": 0.15},
    {"label": "Напоминание о дозаказе в приложении", "a": [900, 63], "b": [880, 70], "baseline": 0.07, "mde": 0.2},
]


def rate(conversions: float, visitors: float) -> float:
    return conversions / visitors if visitors else 0.0


def lift(base: float, other: float) -> float:
    return (other - base) / base if base else 0.0


def pooled(p1: float, n1: float, p2: float, n2: float) -> float:
    return (p1 * n1 + p2 * n2) / (n1 + n2) if n1 + n2 else 0.0


def se_pooled(p1: float, n1: float, p2: float, n2: float) -> float:
    p = pooled(p1, n1, p2, n2)
    return sqrt(p * (1 - p) * (1 / n1 + 1 / n2)) if n1 and n2 else 0.0


def se_unpooled(p1: float, n1: float, p2: float, n2: float) -> float:
    return sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2) if n1 and n2 else 0.0


def z_score(p1: float, n1: float, p2: float, n2: float) -> float:
    denom = se_pooled(p1, n1, p2, n2)
    return (p2 - p1) / denom if denom else 0.0


def p_value(z: float) -> float:
    return round(2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2)))), 5)


def z_crit(alpha: float) -> float:
    return Z_ALPHA.get(alpha, 1.959964)


def z_power(power: float) -> float:
    return Z_POWER.get(power, 0.841621)


def interval(p1: float, n1: float, p2: float, n2: float, alpha: float) -> tuple[float, float]:
    se = se_unpooled(p1, n1, p2, n2)
    return (round(p2 - p1 - z_crit(alpha) * se, 4), round(p2 - p1 + z_crit(alpha) * se, 4))


def sample_size(baseline: float, mde: float, alpha: float = 0.05, power: float = 0.8) -> int:
    effect = (baseline * mde) ** 2
    return int((z_crit(alpha) + z_power(power)) ** 2 * variance(baseline, baseline * (1 + mde)) / effect) if effect else 0


def variance(p1: float, p2: float) -> float:
    return p1 * (1 - p1) + p2 * (1 - p2)


def decision(p: float, alpha: float, low: float, high: float) -> str:
    return "эффект значим, можно раскатывать" if p < alpha and low > 0 else "эффект значим, но отрицательный — откатывать" if p < alpha and high < 0 else "эффект не доказан: данных мало или разница в пределах шума"


def verdict(p: float, alpha: float, low: float, high: float) -> str:
    return "rollout" if p < alpha and low > 0 else "rollback" if p < alpha and high < 0 else "keep_testing"


def traffic_note(needed: int, current: int, days_elapsed: int) -> dict:
    daily = current / max(days_elapsed, 1)
    return {"needed_per_arm": needed, "current_total": current, "days_elapsed": days_elapsed, "extra_days": max(0, int(needed / daily) - days_elapsed) if daily else 0}


def compute(visitors_a: int, conv_a: int, visitors_b: int, conv_b: int, alpha: float = 0.05, power: float = 0.8, mde: float = 0.1, days: int = 14) -> dict:
    stats = statistics_of(visitors_a, conv_a, visitors_b, conv_b, alpha)
    return {**stats, "power": power, "mde": mde, "sample": traffic_note(sample_size(stats["a"]["rate"], mde, alpha, power), visitors_a + visitors_b, days), "guardrail": "Проверять маржу на транзакцию: рост конверсии при падении маржи на 5 % — повод остановить тест."}


def statistics_of(visitors_a: int, conv_a: int, visitors_b: int, conv_b: int, alpha: float) -> dict:
    p1, p2 = rate(conv_a, visitors_a), rate(conv_b, visitors_b)
    return {"a": {"visitors": visitors_a, "conversions": conv_a, "rate": round(p1, 4)}, "b": {"visitors": visitors_b, "conversions": conv_b, "rate": round(p2, 4)}, **inference(p1, visitors_a, p2, visitors_b, alpha)}


def inference(p1: float, n1: int, p2: float, n2: int, alpha: float) -> dict:
    z = z_score(p1, n1, p2, n2)
    return {"lift_pct": round(lift(p1, p2) * 100, 2), "diff_pp": round((p2 - p1) * 100, 2), "z": round(z, 3), "p_value": p_value(z), "alpha": alpha, **ci_block(z, p1, n1, p2, n2, alpha)}


def ci_block(z: float, p1: float, n1: int, p2: float, n2: int, alpha: float) -> dict:
    low, high = interval(p1, n1, p2, n2, alpha)
    return {"ci": {"low": low, "high": high, "level": round((1 - alpha) * 100)}, "significant": p_value(z) < alpha, "verdict": verdict(p_value(z), alpha, low, high), "decision": decision(p_value(z), alpha, low, high)}


def scenario(index: int) -> dict:
    item = SCENARIOS[index % len(SCENARIOS)]
    return {"label": item["label"], "a": {"visitors": item["a"][0], "conversions": item["a"][1]}, "b": {"visitors": item["b"][0], "conversions": item["b"][1]}, "mde": item["mde"]}


def scenarios() -> list[dict]:
    return [{"label": s["label"], "a": {"visitors": s["a"][0], "conversions": s["a"][1]}, "b": {"visitors": s["b"][0], "conversions": s["b"][1]}, "mde": s["mde"]} for s in SCENARIOS]


def plan(baseline: float, mde: float, alpha: float = 0.05, power: float = 0.8) -> dict:
    return {"baseline": baseline, "mde": mde, "alpha": alpha, "power": power, "needed_per_arm": sample_size(baseline, mde, alpha, power), "weeks_at_900_per_week": round(sample_size(baseline, mde, alpha, power) / 900, 1)}
