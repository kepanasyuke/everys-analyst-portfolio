import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const BASE = "http://127.0.0.1:8077";
const OUT = "screenshots";
const SHOTS = [
  ["home", "view-desktop-home"],
  ["app", "view-desktop-app"],
  ["catalog", "view-desktop-catalog"],
  ["counter", "view-desktop-counter"],
  ["stock", "view-desktop-stock"],
  ["reorder", "view-desktop-reorder"],
  ["sales", "view-desktop-sales"],
  ["pharmacies", "view-desktop-pharmacies"],
];

mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ channel: "msedge", headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 950 } });
const page = await context.newPage();

for (const [route, name] of SHOTS) {
  await page.goto(`${BASE}/#/${route}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${OUT}/${name}.png` });
  console.log(`ok ${name}`);
}

await context.close();
const mobile = await browser.newContext({ viewport: { width: 390, height: 844 } });
const mobilePage = await mobile.newPage();
await mobilePage.goto(`${BASE}/#/counter`, { waitUntil: "networkidle" });
await mobilePage.waitForTimeout(1200);
await mobilePage.screenshot({ path: `${OUT}/view-mobile-counter.png` });
console.log("ok view-mobile-counter");
await mobile.close();
await browser.close();