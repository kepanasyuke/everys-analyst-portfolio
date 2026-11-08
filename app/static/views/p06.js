import { get, post } from "../api.js";
import { errorBox, esc, num, pageHead, stats, tag, withSpinner } from "../ui.js";

const SLA_TONE = { healthy: "green", degraded: "amber", blocked: "red" };
const LEVEL_TONE = { blocker: "red", warning: "amber", info: "grey" };

function checks(row) {
  return (row.findings || [])
    .map((item) => `<li>${tag(item.code, LEVEL_TONE[item.level] || "grey")} ${esc(item.message)} — ${tag(item.status, item.status === "ok" ? "green" : "red")}</li>`)
    .join("");
}

function targetRow(row) {
  return `<div class="card">
    <div class="btn-row">${tag(row.sla, SLA_TONE[row.sla] || "grey")}${tag(row.mode, "grey")}<span class="muted">${esc(row.url)}</span></div>
    <h3>${esc(row.target)}</h3>
    ${stats([
      ["Оценка", String(row.score ?? 0), row.score >= 80 ? "good" : row.score >= 50 ? "" : "bad"],
      ["Латентность", row.latency_ms === undefined ? "—" : `${row.latency_ms} мс`],
      ["TLS", row.tls_version || "—"],
      ["Сертификат", row.tls_days === undefined ? "—" : `${row.tls_days} дн.`],
    ])}
    ${row.error ? `<div class="error">${esc(row.error)}</div>` : ""}
    <ul class="list">${checks(row)}</ul>
  </div>`;
}

function report(data) {
  const summary = data.summary || {};
  return `${stats([
    ["Целей", String(summary.targets ?? 0)],
    ["Здоровых", String(summary.healthy ?? 0), "good"],
    ["Деградация", String(summary.degraded ?? 0)],
    ["Заблокировано", String(summary.blocked ?? 0), "bad"],
    ["Средний балл", String(summary.avg_score ?? 0)],
  ])}
  ${(data.results || []).map(targetRow).join("")}
  <p class="muted">Проверено: ${esc(data.checked_at)}. Демо-режим не выходит в сеть и воспроизводим в офлайне.</p>`;
}

function soapReport(data) {
  return `<div class="card">
    <div class="btn-row">${tag(data.verdict, data.valid ? "green" : "red")}${tag(`idFlux: ${data.id_flux}`, "grey")}</div>
    ${data.missing.length ? `<p><strong>Отсутствуют:</strong> ${data.missing.map((item) => tag(item, "red")).join(" ")}</p>` : ""}
    <p class="muted">Теги: ${data.tags.map((item) => `<code>${esc(item)}</code>`).join(" · ")}</p>
  </div>`;
}

export default {
  slug: "integration-watch",
  code: "P06",
  title: "Integration Watch",
  async mount(root) {
    const meta = await get("/api/p06/targets").catch(() => ({ targets: [], soap_sample: "" }));
    root.innerHTML = `${pageHead("P06 · интеграции", "API, TLS и SOAP: то, что валит телепередачу",
      "Проба endpoint-ов: код ответа, латентность, версия TLS и срок сертификата. Отдельно — валидация SOAP-конверта по контракту: Envelope, Header, Body, idFlux. Приватные и loopback-адреса блокируются.")}
      <div class="card">
        <div class="btn-row">
          <button class="btn" id="demo">Демо-проба целей Everys</button>
          <button class="btn ghost" id="live">Живая проба (интернет)</button>
        </div>
        <p class="muted">Живой режим: ${(meta.targets || []).length} цели из корпуса, таймаут 8 с. В офлайне используйте демо-режим.</p>
      </div>
      <div id="out"><div class="card"><h3>Результаты проб</h3></div></div>
      <h2>Валидатор SOAP-конверта</h2>
      <div class="split">
        <div class="card">
          <label>XML конверта<textarea id="xml" class="mono">${esc(meta.soap_sample || "")}</textarea></label>
          <button class="btn" id="check">Проверить контракт</button>
        </div>
        <div id="soap"><div class="card"><h3>Здесь будет вердикт</h3></div></div>
      </div>`;
    const run = async (event, simulate) => {
      const out = document.getElementById("out");
      const result = await withSpinner(event.currentTarget, () => post("/api/p06/probe", { targets: simulate ? [] : meta.targets, simulate }));
      out.innerHTML = result.ok ? report(result.value) : errorBox(result.error);
    };
    document.getElementById("demo").addEventListener("click", (event) => run(event, true));
    document.getElementById("live").addEventListener("click", (event) => run(event, false));
    document.getElementById("check").addEventListener("click", async (event) => {
      const xml = document.getElementById("xml").value;
      const result = await withSpinner(event.currentTarget, () => post("/api/p06/soap", { xml }));
      document.getElementById("soap").innerHTML = result.ok ? soapReport(result.value) : errorBox(result.error);
    });
    document.getElementById("demo").click();
    document.getElementById("check").click();
  },
};
