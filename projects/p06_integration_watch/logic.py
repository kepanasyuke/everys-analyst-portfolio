"""P06 — Integration Watch: проба HTTP/SOAP-endpoint-ов, TLS, SLA и валидация конверта."""

from __future__ import annotations

import re
import socket
import ssl
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from ipaddress import ip_address

import httpx

PRIVATE_PREFIXES = ("127.", "10.", "192.168.", "169.254.", "localhost")
SOAP_NS = re.compile(r"\{[^}]+\}")
TIMEOUT = 8.0
SLOW_MS = 800
CERT_WARN_DAYS = 30
USER_AGENT = "Everys-Analyst-Portfolio/1.0"

DEMO_TARGETS = [
    {"url": "https://www.winpharma.com/", "label": "WinPharma — портал продукта", "simulate": {"status": 200, "latency_ms": 342, "tls_days": 214, "tls_version": "TLSv1.3"}},
    {"url": "https://moscow.everys.com/", "label": "Everys Москва — страница вакансий", "simulate": {"status": 200, "latency_ms": 271, "tls_days": 96, "tls_version": "TLSv1.3"}},
    {"url": "https://api.everys-demo.com/soap/transmission", "label": "Сервис передачи потоков (демо)", "simulate": {"status": 503, "latency_ms": 1240, "tls_days": 12, "tls_version": "TLSv1.2"}},
]

SOAP_SAMPLE = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
  <soap:Header><EnteteSecurite><idOfficine>OFF-7731</idOfficine><horodatage>2026-11-08T09:12:00Z</horodatage></EnteteSecurite></soap:Header>
  <soap:Body><TransmettreFlux><idFlux>FLX-20261108-0001</idFlux><Flux>UEsDBBQ=</Flux></TransmettreFlux></soap:Body>
</soap:Envelope>"""


def is_local_ip(host: str) -> bool:
    address = parse_ip(host)
    return address.is_private if address else False


def parse_ip(host: str):
    try:
        value = ip_address(host)
    except ValueError:
        value = None
    return value


def is_private(url: str) -> bool:
    host = httpx.URL(url).host or ""
    return not host or host.startswith(PRIVATE_PREFIXES) or is_local_ip(host)


def validated(url: str) -> dict:
    return {"ok": False, "error": "Разрешены только публичные https-адреса: приватные и loopback-хосты заблокированы"} if is_private(url) or not url.startswith("https://") else {"ok": True, "error": ""}


def days_left(cert: dict) -> int:
    expires = datetime.strptime(cert.get("notAfter", ""), "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)
    return (expires - datetime.now(UTC)).days


def ssl_probe(host: str, port: int = 443) -> dict:
    with socket.create_connection((host, port), timeout=TIMEOUT) as sock:
        with ssl.create_default_context().wrap_socket(sock, server_hostname=host) as tls:
            info = {"tls_version": tls.version() or "—", "tls_days": days_left(tls.getpeercert())}
    return info


def http_probe(url: str) -> dict:
    started = time.perf_counter()
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True, verify=True) as client:
        return describe(client.get(url, headers={"User-Agent": USER_AGENT}), started)


def describe(response, started: float) -> dict:
    return {"status": response.status_code, "headers": dict(response.headers), "body": response.text[:4000], "latency_ms": int((time.perf_counter() - started) * 1000)}


def probe(url: str) -> dict:
    host = httpx.URL(url).host or ""
    return {"url": url, **safe_http(url), **safe_ssl(host)}


def safe_http(url: str) -> dict:
    try:
        result = http_probe(url)
    except (httpx.HTTPError, ValueError) as exc:
        result = {"status": 0, "headers": {}, "body": "", "latency_ms": -1, "error": f"{type(exc).__name__}: {str(exc)[:120]}"}
    return result


def safe_ssl(host: str) -> dict:
    try:
        result = ssl_probe(host)
    except (OSError, ssl.SSLError, ValueError) as exc:
        result = {"tls_version": "—", "tls_days": -1, "tls_error": f"{type(exc).__name__}: {str(exc)[:120]}"}
    return result


def checks_of(result: dict) -> list[dict]:
    return [{**c, "status": "ok" if c["ok"] else "fail"} for c in raw_checks(result)]


def raw_checks(result: dict) -> list[dict]:
    header_names = {k.lower() for k in result.get("headers", {})}
    return [
        {"code": "HTTP", "ok": 0 < result.get("status", 0) < 400, "level": "blocker", "message": f"Код ответа {result.get('status', 0)}"},
        {"code": "TLS", "ok": result.get("tls_version") in ("TLSv1.2", "TLSv1.3"), "level": "blocker", "message": f"Протокол {result.get('tls_version', '—')}"},
        {"code": "CERT", "ok": result.get("tls_days", -1) > CERT_WARN_DAYS, "level": "warning", "message": f"Сертификат истекает через {result.get('tls_days', -1)} дн."},
        {"code": "LATENCY", "ok": 0 < result.get("latency_ms", -1) < SLOW_MS, "level": "warning", "message": f"Ответ за {result.get('latency_ms', -1)} мс (порог {SLOW_MS} мс)"},
        {"code": "HSTS", "ok": "strict-transport-security" in header_names, "level": "info", "message": "Заголовок Strict-Transport-Security отсутствует"},
    ]


def score(checks: list[dict]) -> int:
    return round(100 * sum(1 for c in checks if c["ok"]) / max(len(checks), 1))


def sla(checks: list[dict]) -> str:
    return "blocked" if any(c["status"] == "fail" and c["level"] == "blocker" for c in checks) else "degraded" if any(c["status"] == "fail" for c in checks) else "healthy"


def row(target: dict, result: dict, mode: str) -> dict:
    cards = checks_of(result)
    return {"target": target.get("label") or target.get("url", ""), "url": target.get("url", ""), "mode": mode, "findings": cards, "score": score(cards), "sla": sla(cards), **result}


def demo_row(target: dict) -> dict:
    return row(target, {**target["simulate"], "headers": {"content-type": "text/html; charset=utf-8", "server": "demo"}, "body": ""}, "demo")


def live_row(target: dict) -> dict:
    check = validated(target.get("url", ""))
    return row(target, probe(target["url"]), "live") if check["ok"] else {"target": target.get("label", ""), "url": target.get("url", ""), "mode": "live", "sla": "blocked", "score": 0, "error": check["error"], "findings": []}


def run(targets: list[dict] | None = None, simulate: bool = True) -> dict:
    rows = execute(targets or DEMO_TARGETS, simulate)
    return {"results": rows, "summary": summarize(rows), "checked_at": datetime.now(UTC).isoformat(timespec="seconds")}


def execute(targets: list[dict], simulate: bool) -> list[dict]:
    return [demo_row(t) for t in targets] if simulate else [live_row(t) for t in targets]


def summarize(rows: list[dict]) -> dict:
    return {"targets": len(rows), "healthy": sum(1 for r in rows if r["sla"] == "healthy"), "degraded": sum(1 for r in rows if r["sla"] == "degraded"), "blocked": sum(1 for r in rows if r["sla"] == "blocked"), "avg_score": round(sum(r["score"] for r in rows) / max(len(rows), 1))}


def local_tags(xml_text: str) -> list[str]:
    root, error = parse_xml(xml_text)
    return [SOAP_NS.sub("", node.tag) for node in root.iter()] if root is not None else [error]


def parse_xml(xml_text: str):
    try:
        root, error = ET.fromstring(xml_text), ""
    except ET.ParseError as exc:
        root, error = None, f"XML parse error: {exc}"
    return root, error


def soap_check(xml_text: str) -> dict:
    return verdict_of(local_tags(xml_text))


def verdict_of(tags: list[str]) -> dict:
    missing = [t for t in ("Envelope", "Header", "Body") if t not in tags]
    return {"tags": tags[:20], "missing": missing, "valid": not missing and "TransmettreFlux" in tags, "id_flux": "oui" if "idFlux" in tags else "non", "verdict": "конверт соответствует контракту" if not missing else "конверт не соответствует контракту: отсутствуют " + ", ".join(missing)}


def demo_targets() -> list[dict]:
    return [{"label": t["label"], "url": t["url"]} for t in DEMO_TARGETS]
