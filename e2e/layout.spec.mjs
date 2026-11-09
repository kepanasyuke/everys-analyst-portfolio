import { expect, test } from "@playwright/test";

const ROUTES = [
  "home",
  "app",
  "catalog",
  "counter",
  "stock",
  "reorder",
  "sales",
  "pharmacies",
  "requirements",
  "sql-lab",
  "conflicts",
  "edge-cases",
  "ab-lab",
  "integration-watch",
  "release-gate",
  "glossary",
];

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 950 },
  { name: "laptop", width: 1100, height: 800 },
  { name: "mobile", width: 390, height: 844 },
];

const measure = () => {
  const scrollable = (el) => {
    const parent = el.parentElement;
    if (!parent) return false;
    return getComputedStyle(parent).overflowX !== "visible" ? true : scrollable(parent);
  };
  const doc = document.documentElement;
  const wide = [...document.querySelectorAll("#view *")].filter((el) => el.getBoundingClientRect().right > window.innerWidth + 1 && !scrollable(el));
  return { page: doc.scrollWidth - doc.clientWidth, wide: wide.slice(0, 3).map((el) => el.tagName.toLowerCase()) };
};

for (const viewport of VIEWPORTS) {
  test.describe(`${viewport.name} ${viewport.width}px`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });
    for (const route of ROUTES) {
      test(`экран ${route} без горизонтального переполнения`, async ({ page }) => {
        await page.goto(`/#/${route}`, { waitUntil: "domcontentloaded" });
        await page.waitForSelector("#view .page-head, #view .hero");
        await page.waitForTimeout(600);
        const result = await page.evaluate(measure);
        expect(result.page, `переполнение страницы на ${route}`).toBeLessThanOrEqual(1);
        expect(result.wide, `элементы за пределами экрана на ${route}`).toEqual([]);
      });
    }
  });
}
