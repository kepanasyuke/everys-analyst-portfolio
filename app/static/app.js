import { get } from "./api.js";
import { esc } from "./ui.js";
import home from "./views/home.js";
import p01 from "./views/p01.js";
import p02 from "./views/p02.js";
import p03 from "./views/p03.js";
import p04 from "./views/p04.js";
import p05 from "./views/p05.js";
import p06 from "./views/p06.js";
import p07 from "./views/p07.js";
import p08 from "./views/p08.js";

const VIEWS = [home, p01, p02, p03, p04, p05, p06, p07, p08];
const ROUTES = Object.fromEntries(VIEWS.map((view) => [view.slug, view]));
const nav = document.getElementById("nav");
const root = document.getElementById("view");
const state = { catalog: { projects: [], corpus: {}, ai: {} } };

function renderNav() {
  nav.innerHTML = VIEWS.map(
    (view) => `<a href="#/${view.slug}" data-slug="${view.slug}"><span class="idx">${esc(view.code || "")}</span><span>${esc(view.title)}</span></a>`,
  ).join("");
}

function currentSlug() {
  return location.hash.replace(/^#\/?/, "") || "home";
}

function markActive(slug) {
  document.querySelectorAll(".nav a").forEach((link) => {
    link.classList.toggle("active", link.dataset.slug === slug);
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
