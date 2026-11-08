"""Linter контракта Everys: один выход, тело 1-2 строки, без while/break/continue.

Запуск:
    python tools/lint_rules.py [пути...]
Код возврата 0 — нарушений нет, 1 — есть.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

SKIP = {".venv", "__pycache__", ".git", "node_modules", ".ruff_cache", ".mypy_cache"}
MAX_STATEMENTS = 2
BANNED = {
    ast.While: ("E001", "while запрещён — используйте включение или генератор"),
    ast.Break: ("E002", "break запрещён — один выход из функции"),
    ast.Continue: ("E002", "continue запрещён — один выход из функции"),
}
DOC_CODES = {"E003": "один выход: ровно один return", "E004": "нет return", "E005": "тело функции"}


def issue(code: str, message: str, path: Path, line: int) -> dict:
    return {"code": code, "message": message, "path": str(path), "line": line}


def python_files(roots: list[str]) -> list[Path]:
    return sorted(p for r in roots for p in Path(r).rglob("*.py") if not SKIP & set(p.parts))


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def functions(tree: ast.AST) -> list[ast.stmt]:
    return [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


def is_docstring(node: ast.stmt) -> bool:
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)


def body(func: ast.stmt) -> list[ast.stmt]:
    return [s for s in func.body if not is_docstring(s)]


def returns(func: ast.stmt) -> list[ast.Return]:
    return [n for n in ast.walk(func) if isinstance(n, ast.Return)]


def banned(func: ast.stmt) -> list[ast.stmt]:
    return [n for n in ast.walk(func) if type(n) in BANNED]


def check_exit(func: ast.stmt, path: Path) -> list[dict]:
    count = len(returns(func))
    return [] if allowed_exit(func, count) else [issue("E003" if count else "E004", f"{func.name}: return найден {count}, нужен 1", path, func.lineno)]


def allowed_exit(func: ast.stmt, count: int) -> bool:
    return count == 1 or (count == 0 and (func.name == "__init__" or func.name.startswith("test_")))


def check_size(func: ast.stmt, path: Path) -> list[dict]:
    count = len(body(func))
    return [] if count <= MAX_STATEMENTS else [issue("E005", f"{func.name}: строк тела {count}, максимум 2", path, func.lineno)]


def check_banned(func: ast.stmt, path: Path) -> list[dict]:
    return [issue(*BANNED[type(n)], path, n.lineno) for n in banned(func)]


def check_function(func: ast.stmt, path: Path) -> list[dict]:
    return [*check_exit(func, path), *check_size(func, path), *check_banned(func, path)]


def check_file(path: Path) -> list[dict]:
    tree = parse(path)
    return [hit for func in functions(tree) for hit in check_function(func, path)]


def collect(paths: list[str]) -> list[dict]:
    hits: list[dict] = []
    return [hit for path in python_files(paths) for hit in check_file(path)]


def line_of(hit: dict) -> str:
    return f"{hit['path']}:{hit['line']}: {hit['code']} {hit['message']}"


def summarize(hits: list[dict]) -> str:
    return f"\n{len(hits)} нарушение(й) контракта стиля" if hits else "\nСтиль соблюдён: нарушений нет"


def report(hits: list[dict]) -> int:
    print("\n".join([line_of(hit) for hit in hits]) + summarize(hits))
    return 1 if hits else 0


def main(argv: list[str]) -> int:
    return report(collect(argv[1:] or ["app", "projects", "tools", "tests"]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
