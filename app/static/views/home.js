import { esc, pct, stats, tag } from "../ui.js";

function card(project) {
  return `<a class="card link" href="#/${project.slug}">
    <span class="meta">${esc(project.code)} · ${esc(project.stack[0])}</span>
    <h3>${esc(project.title_ru)}</h3>
    <p>${esc(project.problem)}</p>
    <p class="muted"><strong>AI:</strong> ${esc(project.ai)}</p>
    <div class="btn-row">${project.stack.map((item) => tag(item, "grey")).join("")}</div>
    <span class="muted">${esc(project.endpoint)}</span>
  </a>`;
}

function hero(catalog) {
  return `<section class="hero">
    <span class="kicker">Everys · WinPharma · системный и продуктовый аналитик</span>
    <h1>Восемь рабочих инструментов аналитика на аптечном домене</h1>
    <p>Учебно-демонстрационный портфолио-проект под вакансию системного/продуктового аналитика
    Everys (Московское представительство). Каждый инструмент закрывает конкретный участок работы:
    разбор документации с AI/RAG, проектирование решений и критериев приёмки, сквозное сопровождение
    фичи до релиза, поиск граничных сценариев и контроль стабильности выпусков.</p>
    <p class="muted">Стек: Python 3.14, FastAPI, SQLite, BM25-RAG, чистый ES-модульный фронтенд.
    Внешний LLM подключается переменными окружения, по умолчанию работает локальное детерминированное ядро.</p>
  </section>`;
}

function providerLabel(ai) {
  const provider = (ai || {}).provider || "—";
  return provider === "local-deterministic" ? "local · BM25" : provider;
}

function overview(catalog) {
  const corpus = catalog.corpus || {};
  return stats([
    ["Проектов", String((catalog.projects || []).length)],
    ["Документов в корпусе", String(corpus.documents ?? "—")],
    ["Фрагментов для RAG", String(corpus.chunks ?? "—")],
    ["Терминов в индексе", String(corpus.terms ?? "—")],
    ["AI-провайдер", providerLabel(catalog.ai)],
  ]);
}

function footer() {
  return `<footer class="foot">
    <span>Контракт стиля: один выход из функции · тело 1–2 строки · без while/break/continue</span>
    <span>${esc(pct(1))} локальный запуск · <a href="/api/docs">OpenAPI</a></span>
  </footer>`;
}

export default {
  slug: "home",
  code: "00",
  title: "Обзор",
  async mount(root, state) {
    const catalog = state.catalog || {};
    root.innerHTML = `${hero(catalog)}${overview(catalog)}<div class="grid">${(catalog.projects || []).map(card).join("")}</div>${footer()}`;
  },
};
