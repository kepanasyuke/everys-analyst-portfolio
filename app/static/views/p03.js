import { get, post } from "../api.js";
import { errorBox, esc, note, pageHead, stats, tag, withSpinner } from "../ui.js";

function side(entry, tone) {
  return `<div>
    <div class="btn-row">${tag(entry.value, tone)}<span class="muted">${esc(entry.doc)}</span></div>
    <p class="muted">${esc(entry.title)}</p>
    <p>${esc(entry.text)}</p>
  </div>`;
}

function conflict(item) {
  const tone = item.severity === "high" ? "red" : "amber";
  return `<div class="card">
    <div class="btn-row">${tag(item.severity, tone)}${tag(item.kind, "grey")}</div>
    <h3>${esc(item.topic)}</h3>
    <div class="grid two">${side(item.left, tone)}${side(item.right, tone)}</div>
    <div class="warn"><strong>Рекомендация.</strong> ${esc(item.recommendation)}</div>
  </div>`;
}

function documents(rows) {
  return `<div class="card"><h3>Версии документов</h3><table><thead><tr><th>Документ</th><th>Версия</th><th>Статус</th></tr></thead><tbody>${rows
    .map((row) => `<tr><td>${esc(row.title)}</td><td>${esc(row.version)}</td><td>${tag(row.status, row.status === "в силе" ? "green" : "amber")}</td></tr>`)
    .join("")}</tbody></table></div>`;
}

function report(data) {
  const summary = data.summary || {};
  return `${stats([
    ["Противоречий", String(summary.total ?? 0)],
    ["Критичных", String(summary.high ?? 0), "bad"],
    ["Модальных", String(summary.medium ?? 0), ""],
    ["Утверждений разобрано", String(summary.statements ?? 0)],
    ["Документов", String(summary.docs ?? 0)],
  ])}
  ${note(`Темы под наблюдением: ${(summary.topics || []).map((topic) => tag(topic, "grey")).join(" ") || "—"}`)}
  ${(data.conflicts || []).map(conflict).join("") || `<div class="note">Противоречий не найдено.</div>`}
  ${documents(data.documents || [])}`;
}

export default {
  slug: "conflicts",
  code: "P03",
  title: "Радар противоречий",
  async mount(root) {
    root.innerHTML = `${pageHead("P03 · качество требований", "Противоречия между спецификациями — до разработки",
      "Девять документов корпуса разбираются на утверждения с числовыми и модальными значениями. Совпадающие темы сравниваются между документами: 30 % против 20 %, TLS 1.3 против 1.2, 48 часов против 24.")}
      <div class="card">
        <div class="btn-row">
          <button class="btn" id="scan-all">Сканировать корпус</button>
          <button class="btn ghost" id="scan-high">Только критичные</button>
        </div>
        <p class="muted">Эвристики детерминированы: одинаковый корпус даёт одинаковый отчёт, поэтому его можно приложить к задаче.</p>
      </div>
      <div id="out"><div class="card"><h3>Отчёт появится здесь</h3></div></div>`;
    const run = async (event, body) => {
      const out = document.getElementById("out");
      const result = await withSpinner(event.currentTarget, () => post("/api/p03/scan", body));
      out.innerHTML = result.ok ? report(result.value) : errorBox(result.error);
    };
    document.getElementById("scan-all").addEventListener("click", (event) => run(event, { min_severity: "medium" }));
    document.getElementById("scan-high").addEventListener("click", (event) => run(event, { min_severity: "high" }));
    document.getElementById("scan-all").click();
  },
};
