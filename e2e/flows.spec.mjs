import { expect, test } from "@playwright/test";

function uniqueCip() {
  return `340093${String(Date.now()).slice(-6)}${Math.floor(Math.random() * 10)}`;
}

async function createProduct(request, overrides = {}) {
  const cip = uniqueCip();
  const body = { cip, nom: `E2E ${cip}`, dci: "e2e", categorie: "antalgique", prix_public: 5, stock_actuel: 10, seuil: 2, ...overrides };
  const response = await request.post("/api/app/products", { data: body });
  expect(response.ok()).toBeTruthy();
  return { ...body, cip };
}

async function sell(request, cip, quantite = 2) {
  const response = await request.post("/api/app/sales", { data: { officine_id: 1, lignes: [{ cip, quantite }] } });
  expect(response.ok()).toBeTruthy();
  return response.json();
}

async function stockOf(request, cip) {
  const response = await request.get(`/api/app/products?q=${cip}`);
  const data = await response.json();
  return data.items[0].stock_actuel;
}

test("касса: продажа из корзины до чека", async ({ page, request }) => {
  const product = await createProduct(request);
  await page.goto("/#/counter");
  await page.fill("#q", product.cip);
  await page.locator(`[data-add="${product.cip}"]`).click();
  await page.fill(`[data-qty="${product.cip}"]`, "2");
  await expect(page.locator("#basket")).toContainText(product.nom);
  await page.click("#submit");
  await expect(page.locator("#receipt")).toContainText("проведена");
  expect(await stockOf(request, product.cip)).toBe(8);
});

test("архив: частичный возврат возвращает остаток", async ({ page, request }) => {
  const product = await createProduct(request);
  const sale = await sell(request, product.cip, 4);
  await page.goto("/#/sales");
  await page.locator("tr", { has: page.getByRole("cell", { name: String(sale.id), exact: true }) }).getByRole("button", { name: "Вернуть" }).click();
  await page.fill(`[data-back="${product.cip}"]`, "1");
  await page.click("#do-return");
  await expect(page.locator("#panel")).toContainText("Возврат оформлен");
  expect(await stockOf(request, product.cip)).toBe(7);
});

test("пополнение: заказ по порогу увеличивает остаток", async ({ page, request }) => {
  const product = await createProduct(request, { stock_actuel: 0, seuil: 10 });
  await page.goto("/#/reorder");
  await page.fill(`[data-order="${product.cip}"]`, "20");
  await page.click("#order");
  await expect(page.locator("#out")).toContainText("Заказ №");
  expect(await stockOf(request, product.cip)).toBe(20);
});

test("каталог: поиск и правка цены", async ({ page, request }) => {
  const product = await createProduct(request);
  await page.goto("/#/catalog");
  await page.fill("#q", product.cip);
  await page.click("#search");
  await expect(page.locator("#table")).toContainText(product.nom);
  await page.locator(`[data-edit="${product.cip}"]`).click();
  await page.fill("#edit-prix", "7.25");
  const saved = page.waitForResponse((response) => response.request().method() === "PATCH" && response.url().includes("/api/app/products/"));
  await page.click("#save");
  await saved;
  await page.fill("#q", product.cip);
  await page.click("#search");
  await expect(page.locator("#table")).toContainText("7,25");
});

test("печатный чек открывается отдельной страницей", async ({ page, request }) => {
  const product = await createProduct(request);
  const sale = await sell(request, product.cip, 2);
  await page.goto(`/api/app/sales/${sale.id}/receipt`);
  await expect(page.locator(".receipt")).toContainText("WinPharma");
  await expect(page.locator(".receipt")).toContainText(`№ ${sale.id}`);
  await expect(page.locator(".total")).toContainText("10,00");
});
