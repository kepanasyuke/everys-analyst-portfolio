"""Точка входа: FastAPI-приложение портфолио Everys (8 AI-native аналитических инструментов)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.ai import llm
from app.core.catalog import PROJECTS
from app.core.store import ROOT, corpus_stats
from app.officine.errors import OfficineError
from app.officine.repo import ensure_schema
from app.officine.router import router as officine
from projects.p01_requirements.router import router as p01
from projects.p02_sql_lab.router import router as p02
from projects.p03_conflicts.router import router as p03
from projects.p04_edge_cases.router import router as p04
from projects.p05_ab_lab.router import router as p05
from projects.p06_integration_watch.router import router as p06
from projects.p07_release_gate.router import router as p07
from projects.p08_glossary.router import router as p08

STATIC = ROOT / "app" / "static"
app = FastAPI(title="Everys · Analyst Portfolio", version="1.0.0", docs_url="/api/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")

for router in (p01, p02, p03, p04, p05, p06, p07, p08, officine):
    app.include_router(router)

ensure_schema()


@app.exception_handler(OfficineError)
def officine_error_handler(request: Request, error: OfficineError) -> JSONResponse:
    return JSONResponse(status_code=error.status, content={"detail": error.message})


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/catalog")
def catalog() -> dict:
    return {"projects": PROJECTS, "corpus": corpus_stats(), "ai": llm.status()}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "projects": len(PROJECTS), "corpus": corpus_stats(), "ai": llm.status()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8077, reload=False)
