import { esc, pct, stats, tag } from "../ui.js";
import { icon, iconLabel } from "../icons.js";

const APP_LINKS = [
  ["Рабочее место", "app", "Выручка, дефицит, журнал действий", "grid"],
  ["Каталог", "catalog", "Товары, цены, остатки, правка справочника", "box"],
  ["Касса", "counter", "Корзина, проведение продажи, отмена", "cart"],
  ["Склад", "stock", "Пороги, пополнение, дефицит", "layers"],
  ["Пополнение", "reorder", "Потребность по порогам, заказ одной транзакцией", "truck"],
  ["Архив продаж", "sales", "Фильтры, чеки, частичные возвраты", "archive"],
  ["Сеть аптек", "pharmacies", "Выручка и средний чек по офисинам", "pharmacy"],
];

const FEATURES = [
  ["cart", "Продажи в транзакции"],
  ["undo", "Возвраты"],
  ["truck", "Réassort"],
  ["receipt", "Печатный чек"],
  ["download", "CSV-выгрузки"],
  ["history", "История движений"],
];

const KPIS = [
  ["Экранов в приложении", "7"],
  ["Аптек в сети", "12"],
  ["Продаж в демо-базе", "1400"],
  ["Тестов и E2E-проверок", "167"],
];

function feature(item) {
  return `<li>${icon(item[0], 15)}<span>${esc(item[1])}</span></li>`;
}

function screenLink([title, slug, text, name]) {
  return `<a class="card link" href="#/${slug}">
    <span class="card-icon">${icon(name, 18)}</span>
    <h3>${esc(title)}</h3>
    <p>${esc(text)}</p>
  </a>`;
}

function productCard() {
  return `<section class="product">
    <div class="product-cover">
      <img class="product-mesh" src="/static/media/officine-mesh.svg" alt="" aria-hidden="true" />
      <img class="product-shot" src="/static/media/officine-shot.svg" alt="Экран кассы: поиск по CIP13, корзина, сумма и кнопка «Провести продажу»" />
      <span class="product-flag">${icon("check", 13)} демо-база · 1400 продаж</span>
    </div>
    <div class="product-body">
      <img class="product-mark" src="/static/media/officine-mark.svg" alt="officine — приложение Everys WinPharma" />
      <p class="lead">Рабочее место аптеки поверх SQLite: справочник, касса со списанием остатка,
      возвраты, пополнение по порогам и сеть офисин. Продажа проходит в транзакции, каждое действие
      пишется в журнал, роль в кассе ограничивает скидку.</p>
      ${stats(KPIS)}
      <ul class="product-features">${FEATURES.map(feature).join("")}</ul>
      <div class="btn-row">
        <a class="btn" href="#/counter">${iconLabel("cart", "Открыть кассу")}</a>
        <a class="btn ghost" href="#/app">${iconLabel("grid", "Рабочее место")}</a>
        <a class="btn ghost" href="/api/docs">${iconLabel("layers", "OpenAPI")}</a>
      </div>
    </div>
  </section>`;
}

function appLinks() {
  return `<h2>Приложение officine — работает на демо-базе</h2>
  ${productCard()}
  <h2>Экраны приложения</h2>
  <div class="grid">${APP_LINKS.map(screenLink).join("")}</div>`;
}

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
    root.innerHTML = `${hero(catalog)}${appLinks()}${overview(catalog)}<div class="grid">${(catalog.projects || []).map(card).join("")}</div>${footer()}`;
  },
};
