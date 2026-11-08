import { get } from "./api.js";
import { esc } from "./ui.js";
import home from "./views/home.js";
import dashboard from "./views/dashboard.js";
import catalog from "./views/catalog.js";
import counter from "./views/counter.js";
import stock from "./views/stock.js";
import pharmacies from "./views/pharmacies.js";
import sales from "./views/sales.js";
import p01 from "./views/p01.js";
import p02 from "./views/p02.js";
import p03 from "./views/p03.js";
import p04 from "./views/p04.js";
import p05 from "./views/p05.js";
import p06 from "./views/p06.js";
import p07 from "./views/p07.js";
import p08 from "./views/p08.js";

const GROUPS = [
  { title: "", views: [home] },
  { title: "Приложение officine", views: [dashboard, catalog, counter, stock, sales, pharmacies] },
  { title: "Портфолио · AI-инструменты", views: [p01, p02, p03, p04, p05, p06, p07, p08] },
];
const VIEWS = GROUPS.flatMap((group) => group.views);
const ROUTES = Object.fromEntries(VIEWS.map((view) => [view.slug, view]));
const nav = document.getElementById("nav");
const root = document.getElementById("view");
const state = { catalog: { projects: [], corpus: {}, ai: {} } };

function link(view) {
  return `<a href="#/${view.slug}" data-slug="${view.slug}"><span class="idx">${esc(view.code || "")}</span><span>${esc(view.title)}</span></a>`;
}

function renderNav() {
  nav.innerHTML = GROUPS.map((group) => `${group.title ? `<div class="nav-group">${esc(group.title)}</div>` : ""}${group.views.map(link).join("")}`).join("");
}

function currentSlug() {
  return location.hash.replace(/^#\/?/, "") || "home";
}

function markActive(slug) {
  document.querySelectorAll(".nav a").forEach((element) => {
    element.classList.toggle("active", element.dataset.slug === slug);
  });
}

async function route() {
  const slug = currentSlug();
  const view = ROUTES[slug] || ROUTES.home;
  markActive(view.slug);
  root.innerHTML = "";
  await view.mount(root, state);
  window.scrollTo({ top: 0, behavior: "instant" });
}

async function boot() {
  state.catalog = await get("/api/catalog").catch(() => state.catalog);
  renderNav();
  window.addEventListener("hashchange", route);
  await route();
}

boot();
