import { get, post } from "../api.js";
import { chips, errorBox, esc, note, pageHead, stats, tag, withSpinner } from "../ui.js";

const PRIORITY_TONE = { P1: "red", P2: "amber", P3: "grey" };

function caseCard(item) {
  return `<div class="card">
    <div class="btn-row">${tag(item.priority, PRIORITY_TONE[item.priority] || "grey")}${tag(item.category, "grey")}<span class="muted">${esc(item.id)}</span></div>
    <h3>${esc(item.title)}</h3>
    <p><strong>Предусловие.</strong> ${esc(item.precondition)}</p>
    <p><strong>Шаги.</strong> ${esc(item.steps)}</p>
    <p><strong>Ожидаемый результат.</strong> ${esc(item.expected)}</p>
    <p class="muted">${esc(item.risk)}</p>
  </div>`;
}

function report(data) {
  const summary = data.summary || {};
  const categories = (summary.categories || []).map((category) => tag(category, "grey")).join(" ");
  return `${stats([
    ["Сценариев", String(summary.total ?? 0)],
    ["P1 блокирующих", String(summary.p1 ?? 0), "bad"],
    ["P2 важных", String(summary.p2 ?? 0)],
    ["P3 прочих", String(summary.p3 ?? 0)],
    ["Категорий", String((summary.categories || []).length)],
  ])}
  ${note(`Категории риска: ${categories}`)}
  ${(data.checklist || []).length ? `<div class="card"><h3>Обязательный минимум перед приёмкой</h3><ul class="list">${data.checklist.map((line) => `<li>${esc(line)}</li>`).join("")}</ul></div>` : ""}
  ${(data.cases || []).map(caseCard).join("")}`;
}

export default {
  slug: "edge-cases",
  code: "P04",
  title: "Граничные сценарии",
  async mount(root) {
    const meta = await get("/api/p04/examples").catch(() => ({ samples: [], presets: [] }));
    const samples = meta.samples || [];
    root.innerHTML = `${pageHead("P04 · тест-анализ", "Граничные сценарии из текста спецификации",
      "Из спеки извлекаются числовые пороги и предметные правила, затем порождаются проверки ±1 от границы, права доступа, конкурентность, идемпотентность, холодовой режим и форматы данных.")}
      <div class="split">
        <div class="card">
          <label>Текст спецификации (FR/RU)
            <textarea id="spec">${esc(samples[0] ? samples[0].text : "")}</textarea>
          </label>
          <div class="btn-row" id="samples">${chips(samples.map((sample) => sample.label))}</div>
          <button class="btn" id="run">Сгенерировать сценарии</button>
          <p class="muted">Пресеты: ${(meta.presets || []).length} предметных правил (склад, касса, рецепт, SOAP, холодовая цепь, права).</p>
        </div>
        <div id="out"><div class="card"><h3>Сценарии появятся здесь</h3></div></div>
      </div>`;
    document.getElementById("samples").addEventListener("click", (event) => {
      const chip = event.target.closest("[data-chip]");
      const sample = samples.find((item) => item.label === (chip && chip.dataset.chip));
      if (sample) document.getElementById("spec").value = sample.text;
    });
    document.getElementById("run").addEventListener("click", async (event) => {
      const spec = document.getElementById("spec").value.trim();
      const out = document.getElementById("out");
      if (spec.length < 10) {
        out.innerHTML = errorBox("Нужен текст спецификации");
        return;
      }
      const result = await withSpinner(event.currentTarget, () => post("/api/p04/generate", { spec }));
      out.innerHTML = result.ok ? report(result.value) : errorBox(result.error);
    });
    document.getElementById("run").click();
  },
};
