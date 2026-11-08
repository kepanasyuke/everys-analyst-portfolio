import { get, post } from "../api.js";
import { chips, errorBox, esc, num, pageHead, stats, tag, withSpinner } from "../ui.js";

function criterion(item, index) {
  return `<div class="card">
    <span class="meta">AC-${String(index + 1).padStart(2, "0")} · ${esc(item.kind)} · ${esc(item.value)}</span>
    <p><strong>Given.</strong> ${esc(item.given)}</p>
    <p><strong>When.</strong> ${esc(item.when)}</p>
    <p><strong>Then.</strong> ${esc(item.then)}</p>
    <span class="muted">источник: ${esc(item.source)}</span>
  </div>`;
}

function verification(report) {
  const rows = (report.claims || []).map((claim) => `<li>${esc(claim.claim)} — ${tag(`поддержка ${num(claim.support, 2)}`, claim.support >= 0.5 ? "green" : "amber")}</li>`);
  const unsupported = (report.unsupported || []).map((claim) => `<li>${esc(claim)}</li>`);
  return `<div class="card">
    <h3>Критическая валидация</h3>
    <div class="stat-row">
      <div class="stat"><span class="k">Средняя поддержка</span><span class="v ${report.score >= 0.5 ? "good" : "bad"}">${num(report.score, 2)}</span></div>
      <div class="stat"><span class="k">Утверждений</span><span class="v">${(report.claims || []).length}</span></div>
      <div class="stat"><span class="k">Без опоры</span><span class="v ${unsupported.length ? "bad" : "good"}">${unsupported.length}</span></div>
    </div>
    <ul class="list">${rows.join("")}</ul>
    ${unsupported.length ? `<div class="warn"><strong>Проверить вручную:</strong><ul class="list">${unsupported.join("")}</ul></div>` : `<div class="note">Каждый критерий опирается на фрагмент документа.</div>`}
  </div>`;
}

function report(data) {
  const items = data.criteria || [];
  return `${stats([
    ["Критериев", String(items.length)],
    ["Открытых вопросов", String((data.questions || []).length)],
    ["Рисков", String((data.risks || []).length)],
    ["Язык", data.language === "ru" ? "RU" : "FR"],
    ["Источников", String((data.context || []).length)],
  ])}
  <div class="split">
    <div>
      <div class="card">
        <h3>Разбор запроса</h3>
        <p><strong>Роль:</strong> ${esc(data.actor)}</p>
        <p><strong>Цель:</strong> ${esc(data.goal)}</p>
        <p class="muted">Пайплайн: BM25-поиск по корпусу → извлечение ограничений → GWT-шаблон → проверка поддержки.</p>
      </div>
      <div class="card">
        <h3>Открытые вопросы</h3>
        <ul class="list">${(data.questions || []).map((question) => `<li>${esc(question)}</li>`).join("")}</ul>
      </div>
      <div class="card">
        <h3>Риски</h3>
        <ul class="list">${(data.risks || []).map((risk) => `<li>${esc(risk.risk)} <span class="muted">(${esc(risk.source)})</span></li>`).join("") || "<li class='muted'>Не выявлено</li>"}</ul>
      </div>
    </div>
    <div>
      <h2>Критерии приёмки</h2>
      ${items.map(criterion).join("")}
      ${verification(data.verification || {})}
      <div class="card">
        <h3>Использованные фрагменты</h3>
        ${(data.context || []).map((hit) => `<p><span class="muted">${esc(hit.id)} · score ${num(hit.score, 2)}</span><br>${esc(hit.text)}</p>`).join("")}
      </div>
    </div>
  </div>`;
}

export default {
  slug: "requirements",
  code: "P01",
  title: "Требования → AC",
  async mount(root) {
    const examples = await get("/api/p01/examples").catch(() => ({ examples: [] }));
    root.innerHTML = `${pageHead("P01 · анализ требований", "User story → критерии приёмки за один проход",
      "RAG-поиск по корпусу спецификаций WinPharma, извлечение ограничений и модальностей, сборка Given/When/Then и обязательная проверка каждого утверждения по источнику.")}
      <div class="split">
        <div class="card">
          <label>User story (FR или RU)
            <textarea id="story" placeholder="En tant que pharmacien je veux …">En tant que pharmacien je veux délivrer une ordonnance partiellement afin de ne pas bloquer le patient</textarea>
          </label>
          <div class="btn-row" id="chips">${chips(examples.examples || [])}</div>
          <button class="btn" id="run">Сгенерировать критерии</button>
        </div>
        <div id="out"><div class="card"><h3>Результат появится здесь</h3><p class="muted">Нажмите «Сгенерировать критерии».</p></div></div>
      </div>`;
    document.getElementById("chips").addEventListener("click", (event) => {
      const chip = event.target.closest("[data-chip]");
      if (chip) document.getElementById("story").value = chip.dataset.chip;
    });
    document.getElementById("run").addEventListener("click", async (event) => {
      const story = document.getElementById("story").value.trim();
      const out = document.getElementById("out");
      if (story.length < 3) {
        out.innerHTML = errorBox("Слишком короткий запрос");
        return;
      }
      const result = await withSpinner(event.currentTarget, () => post("/api/p01/generate", { story, limit: 5 }));
      out.innerHTML = result.ok ? report(result.value) : errorBox(result.error);
    });
  },
};
