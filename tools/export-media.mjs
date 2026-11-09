import { chromium } from "playwright";

const BASE = "http://127.0.0.1:8077";
const SCALE = 2;

const browser = await chromium.launch({ channel: "msedge", headless: true, args: ["--disable-gpu", "--hide-scrollbars"] });

const bannerContext = await browser.newContext({ viewport: { width: 1200, height: 420 }, deviceScaleFactor: SCALE });
const bannerPage = await bannerContext.newPage();
await bannerPage.goto(`${BASE}/static/media/officine-banner.svg`, { waitUntil: "networkidle" });
await bannerPage.waitForTimeout(600);
await bannerPage.screenshot({ path: "assets/officine-banner.png" });
await bannerContext.close();

const cardContext = await browser.newContext({ viewport: { width: 1440, height: 1200 }, deviceScaleFactor: SCALE });
const cardPage = await cardContext.newPage();
await cardPage.goto(`${BASE}/#/home`, { waitUntil: "networkidle" });
await cardPage.waitForTimeout(900);
await cardPage.locator(".product").screenshot({ path: "assets/product-card.png" });
await cardContext.close();

await browser.close();
console.log("ok: assets/officine-banner.png, assets/product-card.png");
