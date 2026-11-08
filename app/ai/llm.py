"""LLM-шлюз: OpenAI-совместимый провайдер + честный детерминированный fallback.

Если EVERYS_LLM_BASE_URL / EVERYS_LLM_API_KEY не заданы, ядро работает локально:
BM25-ретривер + шаблонная генерация + критические проверки (app/ai/guard.py).
"""

from __future__ import annotations

import os
from contextlib import suppress

import httpx

BASE_URL = os.getenv("EVERYS_LLM_BASE_URL", "").rstrip("/")
API_KEY = os.getenv("EVERYS_LLM_API_KEY", "")
MODEL = os.getenv("EVERYS_LLM_MODEL", "gpt-4o-mini")
TIMEOUT = float(os.getenv("EVERYS_LLM_TIMEOUT", "30"))


def enabled() -> bool:
    return bool(BASE_URL and API_KEY)


def status() -> dict:
    return {"active": enabled(), "provider": "openai-compatible" if enabled() else "local-deterministic", "model": MODEL if enabled() else "bm25+template"}


def payload(system: str, prompt: str) -> dict:
    return {"model": MODEL, "temperature": 0.2, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}


def headers() -> dict:
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def call(system: str, prompt: str) -> str:
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.post(f"{BASE_URL}/chat/completions", json=payload(system, prompt), headers=headers())
    return response.json()["choices"][0]["message"]["content"]


def attempt(system: str, prompt: str) -> tuple[bool, str | None]:
    text = safe_call(lambda: call(system, prompt))
    return (True, text) if text else (False, None)


def safe_call(fn) -> str | None:
    try:
        value = fn()
    except Exception:
        value = None
    return value


def complete(system: str, prompt: str) -> dict:
    ok, text = attempt(system, prompt) if enabled() else (False, None)
    return {"ok": ok, "text": text, "provider": status()["provider"]}
