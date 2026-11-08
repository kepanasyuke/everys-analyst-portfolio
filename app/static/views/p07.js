import { get, post } from "../api.js";
import { errorBox, esc, pageHead, scoreTone, stats, tag, withSpinner } from "../ui.js";

const STATUSES = [
  ["done", "выполнено"],
  ["warn", "с оговоркой"],
  ["fail", "не выполнено"],
];

function gateRow(gate) {
  const options = STATUSES.map(([value, label]) => `<option value="${value}" ${gate.status === value ? "selected" : ""}>${label}</option>`).join("");
  return `<tr>
    <td>${esc(gate.title_ru)}<br><span class="muted">${esc(gate.id)} · вес ${gate.weight}${gate.blocker ? " · блокер" : ""}</span></td>
    <td><select data-gate="${esc(gate.id)}">${options}</select></td>
    <td>${tag(gate.status, gate.status === "done" ? "green" : gate.status === "warn" ? "amber" : "red")}</td>
  </tr>`;
}

function report(data) {
  const tone = scoreTone(data.score);
  return `${stats([
    ["Готовность", `${data.score} %`, tone],
    ["Вердикт", data.verdict_ru, data.tone],
    ["Блокеров", String((data.blockers || []).length), data.blockers.length ? "bad" : "good"],
    ["Оговорок", String((data.warnings || []).length)],
  ])}
  <div class="card">
    <div class="btn-row">${tag(data.verdict_fr, data.tone)}${tag(data.version, "grey")}</div>
    <h3>Что делать в первую очередь</h3>
    <ul class="list">${(data.actions || [])
      .map((action) => `<li><strong>${esc(action.title)}</strong> — вес ${action.weight}, вклад в риск ${action.impact}${action.blocker ? " · блокер" : ""}</li>`)
      .join("") || "<li class='muted'>Критичных действий нет</li>"}</ul>
    ${(data.blockers || []).length ? `<div class="error"><strong>Блокеры:</strong> ${data.blockers.map((item) => esc(item)).join("; ")}</div>` : ""}
  </div>
  <div class="split">
    <div class="card"><h3>Протокол приёмки · RU</h3><p>${esc(data.sign_off_ru)}</p></div>
    <div class="card"><h3>Procès-verbal · FR</h3><p>${esc(data.sign_off_fr)}</p></div>
  </div>`;
}

export default {
  slug: "release-gate",
  code: "P07",
  title: "Release Gate",
  async mount(root) {
    const meta = await get("/api/p07/catalog").catch(() => ({ gates: [], default_status: {} }));
    const seeded = (meta.gates || []).map((gate) => ({ ...gate, status: (meta.default_status || {})[gate.id] || "fail" }));
    root.innerHTML = `${pageHead("P07 · контроль стабильности выпуска", "Release Gate: идём в прод или нет",
      "Взвешенная оценка восьми ворот: регрессия, миграция, откат, мониторинг, поддержка, контракт SOAP, нагрузка, документация. Блокер обнуляет вердикт независимо от суммы баллов.")}
      <div class="split">
        <div class="card">
          <h3>Чек-лист версии</h3>
          <label>Версия<input type="text" id="version" value="2026.1" /></label>
          <table><thead><tr><th>Ворота</th><th>Статус</th><th></th></tr></thead><tbody>${seeded.map(gateRow).join("")}</tbody></table>
          <div class="btn-row"><button class="btn" id="run">Оценить готовность</button><button class="btn ghost" id="preset">Вернуть данные 2026.1</button></div>
        </div>
        <div id="out"><div class="card"><h3>Вердикт появится здесь</h3></div></div>
      </div>`;
    const assess = async (button) => {
      const gates = [...document.querySelectorAll("select[data-gate]")].map((select) => ({ id: select.dataset.gate, status: select.value }));
      const out = document.getElementById("out");
      const result = await withSpinner(button, () => post("/api/p07/assess", { version: document.getElementById("version").value || "2026.1", gates }));
      out.innerHTML = result.ok ? report(result.value) : errorBox(result.error);
    };
    document.getElementById("run").addEventListener("click", (event) => assess(event.currentTarget));
    document.getElementById("preset").addEventListener("click", () => {
      document.querySelectorAll("select[data-gate]").forEach((select) => {
        select.value = (meta.default_status || {})[select.dataset.gate] || "fail";
      });
    });
    document.getElementById("run").click();
  },
};
