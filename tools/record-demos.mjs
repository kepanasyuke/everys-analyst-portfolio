import { chromium } from "playwright";
import { mkdirSync, rmSync } from "node:fs";

const BASE = "http://127.0.0.1:8077";
const TMP = "assets/tmp";
const SIZE = { width: 1000, height: 700 };
const STEP = 180;

rmSync(TMP, { recursive: true, force: true });
mkdirSync(TMP, { recursive: true });

const wait = (page, ms) => page.waitForTimeout(ms);
const uniqueCip = () => `340093${String(Date.now()).slice(-6)}${Math.floor(Math.random() * 10)}`;

async function call(method, path, body) {
  const response = await fetch(`${BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(`${method} ${path} -> ${response.status} ${JSON.stringify(payload).slice(0, 300)}`);
  return payload;
}

async function seed(body) {
  const cip = uniqueCip();
  const base = { nom: "Demo", dci: "demo", categorie: "antalgique", prix_public: 5, stock_actuel: 10, seuil: 2 };
  await call("POST", "/api/app/products", { ...base, ...body, cip });
  await call("PATCH", `/api/app/products/${cip}`, { stock_actuel: body.stock_actuel ?? 10, seuil: body.seuil ?? 2 });
  return { ...base, ...body, cip };
}

async function snap(page, sink) {
  await page.screenshot({ path: `${sink.dir}/f${String(sink.n).padStart(4, "0")}.png`, animations: "disabled" });
  sink.n += 1;
}

async function hold(page, sink, ms) {
  const count = Math.max(1, Math.round(ms / STEP));
  for (let index = 0; index < count; index += 1) {
    await snap(page, sink);
    await page.waitForTimeout(STEP);
  }
}

async function record(scenario) {
  const dir = `${TMP}/${scenario.name}`;
  mkdirSync(dir, { recursive: true });
  const sink = { dir, n: 0 };
  const browser = await chromium.launch({ channel: "msedge", headless: true, args: ["--disable-gpu", "--hide-scrollbars"] });
  const context = await browser.newContext({ viewport: SIZE });
  const page = await context.newPage();
  const data = await scenario.setup(page);
  await scenario.scene(page, data, sink);
  await context.close();
  await browser.close();
  console.log(`ok ${scenario.name}: ${sink.n} кадров`);
}

const scenarios = [
  {
    name: "demo-sale",
    setup: async () => seed({ nom: "Demo Doliprane 1000" }),
    scene: async (page, product, sink) => {
      await page.goto(`${BASE}/#/counter`, { waitUntil: "domcontentloaded" });
      await hold(page, sink, 1200);
      await page.fill("#q", product.cip);
      await hold(page, sink, 900);
      await page.locator(`[data-add="${product.cip}"]`).click();
      await hold(page, sink, 800);
      await page.fill(`[data-qty="${product.cip}"]`, "2");
      await hold(page, sink, 700);
      await page.click("#submit");
      await hold(page, sink, 1800);
    },
  },
  {
    name: "demo-return",
    setup: async () => {
      const product = await seed({ nom: "Demo Amoxicilline 1 g" });
      await call("POST", "/api/app/sales", { officine_id: 1, lignes: [{ cip: product.cip, quantite: 4 }] });
      return product;
    },
    scene: async (page, product, sink) => {
      await page.goto(`${BASE}/#/sales`, { waitUntil: "domcontentloaded" });
      await hold(page, sink, 1400);
      await page.getByRole("button", { name: "Вернуть" }).first().click();
      await hold(page, sink, 900);
      await page.locator(`[data-back="${product.cip}"]`).fill("1");
      await hold(page, sink, 800);
      await page.click("#do-return");
      await hold(page, sink, 1800);
    },
  },
  {
    name: "demo-reorder",
    setup: async () => {
      const product = await seed({ nom: "Demo Stock Zero", stock_actuel: 0, seuil: 10 });
      const plan = await call("GET", "/api/app/reorder?limit=60");
      if (!plan.plan.items.some((item) => item.cip === product.cip)) throw new Error("демо-товар не попал в план пополнения");
      return product;
    },
    scene: async (page, product, sink) => {
      await page.goto(`${BASE}/#/reorder`, { waitUntil: "domcontentloaded" });
      await hold(page, sink, 1600);
      await page.locator(`[data-order="${product.cip}"]`).scrollIntoViewIfNeeded();
      await hold(page, sink, 700);
      await page.click("#order");
      await wait(page, 600);
      await page.locator("#out").scrollIntoViewIfNeeded();
      await hold(page, sink, 1800);
    },
  },
];

for (const scenario of scenarios) {
  await record(scenario);
}
