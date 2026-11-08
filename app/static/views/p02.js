import { get, post } from "../api.js";
import { chart, chips, codeBlock, errorBox, esc, note, pageHead, stats, table, tag, withSpinner } from "../ui.js";

function rowsTable(data) {
  const cells = (data.rows || []).map((row) => row.map((value) => esc(typeof value === "number" ? value.toLocaleString("ru-RU") : value)));
  return table(data.columns || [], cells);
}

function report(data) {
  const safety = data.safety || {};
  return `${stats([
    ["Строк", String((data.rows || []).length)],
    ["Интент", data.label || "—"],
    ["Колонок", String((data.columns || []).length)],
    ["Режим", safety.read_only ? "read-only" : "—"],
    ["LIMIT", String(safety.limit ?? "—")],
  ])}
  <div class="card">
    <div class="btn-row">${tag("SELECT-only", "green")}${tag(`guard ${safety.ok ? "ok" : "fail"}`, safety.ok ? "green" : "red")}${tag("LIMIT принудительный", "grey")}</div>
    ${data.sql ? codeBlock(data.sql) : ""}
    ${chart(data.chart || {})}
    ${data.columns && data.columns.length ? rowsTable(data) : ""}
    <h3>Что это значит</h3>
    <ul class="list">${(data.explanation || []).map((line) => `<li>${esc(line)}</li>`).join("")}</ul>
    ${(data.suggestions || []).length ? `<div class="warn">Попробуйте один из запросов: ${data.suggestions.map((s) => tag(s, "grey")).join(" ")}</div>` : ""}
  </div>`;
}

function schemaBlock(data) {
  return `<div class="card"><h3>Схема демо-базы</h3>${(data.schema || [])
    .map((entry) => `<p><strong>${esc(entry.table)}</strong><br><span class="muted">${entry.columns.map(esc).join(" · ")}</span></p>`)
    .join("")}</div>`;
}

export default {
  slug: "sql-lab",
  code: "P02",
  title: "SQL Lab",
  async mount(root) {
    const meta = await get("/api/p02/examples").catch(() => ({ examples: [], schema: [] }));
    root.innerHTML = `${pageHead("P02 · работа с данными", "Вопрос на бизнес-языке → проверяемый SQL",
      "Разбор интента, шаблонный SELECT по реальным таблицам аптечной сети (1400 продаж, 12 аптек, 30 SKU), принудительный LIMIT и запрет любых изменяющих команд.")}
      <div class="split">
        <div class="card">
          <label>Вопрос аналитика
            <input type="text" id="question" value="Топ-10 препаратов по выручке" />
          </label>
          <div class="btn-row" id="chips">${chips(meta.examples || [])}</div>
          <button class="btn" id="run">Выполнить запрос</button>
          <p class="muted">Свободный SQL тоже можно проверить — он проходит тот же guard, что и сгенерированный.</p>
        </div>
        <div id="out">${schemaBlock(meta)}</div>
      </div>`;
    document.getElementById("chips").addEventListener("click", (event) => {
      const chip = event.target.closest("[data-chip]");
      if (chip) document.getElementById("question").value = chip.dataset.chip;
    });
    document.getElementById("run").addEventListener("click", async (event) => {
      const question = document.getElementById("question").value.trim();
      const out = document.getElementById("out");
      if (question.length < 2) {
        out.innerHTML = errorBox("Введите вопрос");
        return;
      }
      const result = await withSpinner(event.currentTarget, () => post("/api/p02/query", { question }));
      out.innerHTML = result.ok ? report(result.value) : errorBox(result.error);
    });
  },
};
