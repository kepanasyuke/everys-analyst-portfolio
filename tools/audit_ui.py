"""Аудит интерфейса: id-элементы, адреса API, регистрация вью и статические ресурсы.

Запуск: python tools/audit_ui.py
Код возврата 0 — расхождений нет.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
VIEWS = STATIC / "views"

ID_USE = re.compile(r'getElementById\("([^"]+)"\)')
ID_DEF = re.compile(r'id="([^"]+)"')
API_USE = re.compile(r'(?:get|post|query)\(\s*[`"\'](/api/[^`"\']*)')
IMPORT_VIEW = re.compile(r'from "\./views/([a-z0-9_]+)\.js"')
ASSET = re.compile(r'(?:src|href)="(/static/[^"]+)"')


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def view_files() -> list[Path]:
    return sorted(VIEWS.glob("*.js"))


def orphan_ids() -> list[tuple]:
    return [(path.name, element) for path in view_files() for element in sorted(set(ID_USE.findall(read(path))) - set(ID_DEF.findall(read(path))))]


def api_uses() -> list[tuple]:
    return [(path.name, address) for path in view_files() for address in API_USE.findall(read(path))]


def api_routes() -> set[str]:
    return set(app.openapi()["paths"])


def reachable(address: str) -> bool:
    return address in api_routes()


def unknown_api() -> list[tuple]:
    return [(name, address) for name, address in api_uses() if not reachable(address)]


def unregistered_views() -> list[str]:
    imported = set(IMPORT_VIEW.findall(read(STATIC / "app.js")))
    return sorted({path.stem for path in view_files()} - imported)


def missing_views() -> list[str]:
    return sorted(set(IMPORT_VIEW.findall(read(STATIC / "app.js"))) - {path.stem for path in view_files()})


def missing_assets() -> list[str]:
    return [asset for asset in ASSET.findall(read(STATIC / "index.html")) if not (STATIC / asset.removeprefix("/static/")).exists()]


def report(rows: list[str]) -> int:
    print("\n".join(rows + (["Аудит интерфейса: расхождений нет"] if not rows else [])))
    return 1 if rows else 0


def issues() -> list[str]:
    checks = [
        "висячие getElementById: " + str(orphan_ids()),
        "неизвестные адреса: " + str(unknown_api()),
        "вью без импорта: " + str(unregistered_views()),
        "импорт без файла: " + str(missing_views()),
        "нет статики: " + str(missing_assets()),
    ]
    return [line for line in checks if not line.endswith("[]")]


if __name__ == "__main__":
    raise SystemExit(report(issues()))
