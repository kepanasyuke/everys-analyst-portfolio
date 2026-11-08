"""P07 — Release Gate: взвешенная оценка готовности релиза и протокол приёмки."""

from __future__ import annotations

GATES = [
    {"id": "regression", "weight": 20, "category": "качество", "title_ru": "Регрессия на пилотных аптеках", "title_fr": "Régression sur officines pilotes", "blocker": True},
    {"id": "migration", "weight": 20, "category": "данные", "title_ru": "Миграция схемы проверена на копии прод-данных", "title_fr": "Migration testée sur copie de production", "blocker": True},
    {"id": "rollback", "weight": 15, "category": "надёжность", "title_ru": "План и проверка отката", "title_fr": "Plan de retour arrière testé", "blocker": True},
    {"id": "monitoring", "weight": 12, "category": "эксплуатация", "title_ru": "Алерты и дашборд стабильности включены", "title_fr": "Alertes et tableau de bord activés", "blocker": False},
    {"id": "support", "weight": 10, "category": "эксплуатация", "title_ru": "Поддержка обучена, эскалация описана", "title_fr": "Support formé, escalade documentée", "blocker": False},
    {"id": "soap", "weight": 10, "category": "интеграции", "title_ru": "Контракт SOAP проверен на стенде", "title_fr": "Contrat SOAP validé sur recette", "blocker": True},
    {"id": "perf", "weight": 8, "category": "производительность", "title_ru": "Нагрузочная проверка кассы", "title_fr": "Test de charge caisse", "blocker": False},
    {"id": "docs", "weight": 5, "category": "документация", "title_ru": "Release notes и инструкция обновлены", "title_fr": "Notes de version et procédure à jour", "blocker": False},
]

STATUS_VALUE = {"done": 1.0, "warn": 0.5, "fail": 0.0}
DEFAULT_STATUS = {"regression": "done", "migration": "warn", "rollback": "fail", "monitoring": "done", "support": "warn", "soap": "done", "perf": "warn", "docs": "done"}
VERDICTS = {
    "go": {"label_ru": "Релиз разрешён", "label_fr": "Mise en production autorisée", "tone": "green"},
    "conditional": {"label_ru": "Условный допуск: устранить блокеры", "label_fr": "Admission conditionnelle", "tone": "amber"},
    "no-go": {"label_ru": "Релиз запрещён", "label_fr": "Mise en production refusée", "tone": "red"},
}


def gate(gate_id: str) -> dict:
    return next((g for g in GATES if g["id"] == gate_id), {})


def weight_of(gate_id: str) -> int:
    return gate(gate_id).get("weight", 0)


def value_of(status: str) -> float:
    return STATUS_VALUE.get(status, 0.0)


def scored(rows: list[dict]) -> list[dict]:
    return [{**r, "weight": weight_of(r["id"]), "value": value_of(r["status"]), "title": gate(r["id"]).get("title_ru", ""), "blocker": gate(r["id"]).get("blocker", False)} for r in rows]


def total_score(rows: list[dict]) -> int:
    return round(100 * sum(r["weight"] * r["value"] for r in rows) / max(sum(r["weight"] for r in rows), 1))


def blockers(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["blocker"] and r["status"] == "fail"]


def warnings(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["status"] == "warn" and not r["blocker"]]


def verdict(rows: list[dict]) -> str:
    return "no-go" if blockers(rows) else "go" if total_score(rows) >= 85 and not warnings(rows) else "conditional"


def actions(rows: list[dict]) -> list[dict]:
    ordered = sorted(rows, key=lambda r: (r["weight"] * (1 - r["value"])) * (2 if r["blocker"] else 1), reverse=True)
    return [{**r, "impact": round(r["weight"] * (1 - r["value"]), 1)} for r in ordered if r["value"] < 1][:4]


def protocol(rows: list[dict], version: str) -> dict:
    mark = verdict(rows)
    return {"version": version, "score": total_score(rows), "verdict": mark, "verdict_ru": VERDICTS[mark]["label_ru"], "verdict_fr": VERDICTS[mark]["label_fr"], "tone": VERDICTS[mark]["tone"], "blockers": [b["title"] for b in blockers(rows)], "warnings": [w["title"] for w in warnings(rows)], "actions": actions(rows), "sign_off_ru": f"Версия {version}: {VERDICTS[mark]['label_ru']} при готовности {total_score(rows)} %. Ответственный аналитик подтверждает перечень блокеров и план отката.", "sign_off_fr": f"Version {version} : {VERDICTS[mark]['label_fr']} (score {total_score(rows)} %). L'analyste confirme les blocages et le plan de retour arrière."}


def rows_from(statuses: dict) -> list[dict]:
    return [{"id": g["id"], "status": statuses.get(g["id"], "fail")} for g in GATES]


def assess(statuses: dict | None = None, version: str = "2026.1") -> dict:
    rows = scored(rows_from(statuses or DEFAULT_STATUS))
    return {**protocol(rows, version), "gates": rows, "weights_total": sum(r["weight"] for r in rows)}


def coverage(rows: list[dict]) -> dict:
    return {"done": sum(1 for r in rows if r["status"] == "done"), "warn": sum(1 for r in rows if r["status"] == "warn"), "fail": sum(1 for r in rows if r["status"] == "fail"), "total": len(rows)}


def catalog() -> list[dict]:
    return GATES
