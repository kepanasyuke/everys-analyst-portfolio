/**
 * Динамический прогон экранов: каждый view монтируется в минимальный DOM-шим,
 * дергает реальные API на запущенном сервере и рендерит результат.
 *
 * Запуск: node tools/ui-smoke.mjs   (сервер на 127.0.0.1:8077 должен быть поднят)
 */

const BASE = "http://127.0.0.1:8077";
const registry = new Map();
const ID_RE = /id="([^"]+)"/g;
const VALUE_RE = /<input[^>]*id="([^"]+)"[^>]*value="([^"]*)"/g;
const TEXTAREA_RE = /<textarea[^>]*id="([^"]+)"[^>]*>([\s\S]*?)<\/textarea>/g;
const realFetch = globalThis.fetch;

class Element {
  constructor(id = "") {
    this.id = id;
    this.html = "";
    this.value = "";
    this.text = "";
    this.disabled = false;
    this.dataset = {};
    this.handlers = {};
  }

  set innerHTML(value) {
    this.html = String(value);
    register(this.html);
  }

  get innerHTML() {
    return this.html;
  }

  set textContent(value) {
    this.text = String(value);
  }

  get textContent() {
    return this.text;
  }

  addEventListener(type, handler) {
    this.handlers[type] = [...(this.handlers[type] || []), handler];
  }

  click() {
    return Promise.all((this.handlers.click || []).map((handler) => handler({ currentTarget: this, target: this })));
  }

  closest() {
    return null;
  }

  querySelectorAll() {
    return [];
  }
}

const SELECT_RE = /<select data-gate="([^"]+)">([\s\S]*?)<\/select>/g;
const SELECTED_RE = /<option value="([^"]+)" selected/;

function register(html) {
  [...html.matchAll(ID_RE)].forEach(([, id]) => registry.set(id, registry.get(id) || new Element(id)));
  [...html.matchAll(VALUE_RE)].forEach(([, id, value]) => Object.assign(element(id), { value }));
  [...html.matchAll(TEXTAREA_RE)].forEach(([, id, text]) => Object.assign(element(id), { value: unescapeHtml(text) }));
  [...html.matchAll(SELECT_RE)].forEach(([, gate, body]) => Object.assign(element(`gate:${gate}`), { dataset: { gate }, value: (body.match(SELECTED_RE) || [null, "fail"])[1] }));
}

function unescapeHtml(text) {
  return text.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, "&").trim();
}

function element(id) {
  registry.set(id, registry.get(id) || new Element(id));
  return registry.get(id);
}

globalThis.document = {
  getElementById: (id) => element(id),
  querySelectorAll: (selector) => (selector.includes("data-gate") ? [...registry.values()].filter((item) => item.dataset.gate) : []),
  querySelector: () => null,
};
globalThis.window = { scrollTo: () => {} };
globalThis.fetch = (url, options) => realFetch(`${BASE}${url}`, options);

const settle = (ms = 1200) => new Promise((resolve) => setTimeout(resolve, ms));

const CASES = [
  { file: "home.js", label: "Обзор", marker: "Восемь рабочих инструментов", button: null },
  { file: "dashboard.js", label: "A0 рабочее место", marker: "Выручка · 30 дней", button: "refresh" },
  { file: "catalog.js", label: "A1 каталог", marker: "Стоимость выборки", button: "search" },
  { file: "counter.js", label: "A2 касса", marker: "остаток", button: null },
  { file: "stock.js", label: "A3 склад", marker: "Позиций под угрозой", button: "refresh" },
  { file: "pharmacies.js", label: "A4 сеть", marker: "Аптек в сети", button: "refresh" },
  { file: "p01.js", label: "P01 требования", marker: "Критерии приёмки", button: "run" },
  { file: "p02.js", label: "P02 SQL Lab", marker: "Что это значит", button: "run" },
  { file: "p03.js", label: "P03 противоречия", marker: "Рекомендация.", button: "scan-all" },
  { file: "p04.js", label: "P04 граничные", marker: "Ожидаемый результат.", button: "run" },
  { file: "p05.js", label: "P05 A/B", marker: "Доверительный интервал", button: "run" },
  { file: "p06.js", label: "P06 интеграции", marker: "Сертификат", button: "demo" },
  { file: "p07.js", label: "P07 release", marker: "Готовность", button: "run" },
  { file: "p08.js", label: "P08 глоссарий", marker: "Словарь", button: "run" },
];

const OUTPUT_BLOCKS = ["out", "results", "soap", "annotation", "kpi", "alerts", "top", "sales", "journal", "basket", "recent", "receipt", "picker"];

function collected(root) {
  const blocks = [...registry.values()].map((item) => item.html);
  return [root.html, ...blocks, ...OUTPUT_BLOCKS.map((id) => element(id).html)].join("\n");
}

async function runCase(testCase) {
  registry.clear();
  const root = element("root");
  const module = await import(`../app/static/views/${testCase.file}`);
  await module.default.mount(root, { catalog: {} });
  await settle();
  if (testCase.button) {
    await element(testCase.button).click();
    await settle();
  }
  const html = collected(root);
  return { ...testCase, html, ok: html.includes(testCase.marker) && !html.includes("data-error") };
}

function line(result) {
  const size = String(result.html.length).padStart(6);
  return `${result.ok ? "PASS" : "FAIL"} ${result.label.padEnd(20)} ${size} символов`;
}

async function main() {
  const health = await realFetch(`${BASE}/api/health`).then((response) => response.status).catch(() => 0);
  console.log(`сервер: ${health === 200 ? "ok" : "НЕ ОТВЕЧАЕТ"}`);
  const results = [];
  for (const testCase of CASES) {
    const result = await runCase(testCase).catch((error) => ({ ...testCase, html: `ERR ${error.message}`, ok: false }));
    results.push(result);
    console.log(line(result));
  }
  const failed = results.filter((result) => !result.ok);
  console.log(failed.length ? `\nПРОБЛЕМЫ: ${failed.map((result) => result.label).join(", ")}` : "\nВСЕ ЭКРАНЫ РЕНДЕРЯТСЯ");
  process.exit(failed.length ? 1 : 0);
}

main();
