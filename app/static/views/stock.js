import { get, post } from "../api.js";
import { eur, errorBox, esc, pageHead, qty, statusTag, stats, table, withSpinner } from "../ui.js";

function rowsOf(items) {
  return items.map((item) => [
    `<strong>${esc(item.nom)}</strong><br><span class="muted">${esc(item.cip)} · ${esc(item.categorie)}</span>`,
    qty(item.stock_actuel),
    qty(item.seuil),
    statusTag(item.statut_stock),
    `<span class="row-actions"><input class="mini-input" type="number" min="1" value="${Math.max(10, item.seuil * 2 - item.stock_actuel)}" data-qty="${esc(item.cip)}" /><button class="btn ghost small" data-restock="${esc(item.cip)}">Пополнить</button></span>`,
  ]);
}

function block(data) {
  const alerts = data.alerts || [];
  const ruptures = alerts.filter((item) => item.statut_stock === "rupture").length;
  return `${stats([
    ["Позиций под угрозой", qty(alerts.length), alerts.length ? "bad" : "good"],
    ["Полный дефицит", qty(ruptures), ruptures ? "bad" : "good"],
    ["Стоимость склада", eur(data.kpi.valeur_stock)],
    ["Позиций в дефиците по сети", qty(data.kpi.ruptures)],
  ])}
  ${alerts.length ? table(["Товар", "Остаток", "Порог", "Статус", "Пополнение"], rowsOf(alerts)) : `<p class="muted">Все позиции выше порога пополнения.</p>`}
  <p class="muted">Пополнение увеличивает остаток и пишется в журнал как действие «stock.restock».</p>`;
}

export default {
  slug: "stock",
  code: "A3",
  group: "app",
  title: "Склад",
  async mount(root) {
    root.innerHTML = `${pageHead("Приложение officine · склад", "Дефицит, пороги и пополнение",
      "Позиции, у которых остаток меньше или равен порогу. Пополнение проводится в транзакции: остаток растёт, журнал фиксирует количество и автора.")}
      <div class="btn-row"><button class="btn" id="refresh">Обновить</button></div>
      <div id="out"></div>`;

    const load = async (button) => {
      const result = await withSpinner(button, () => get("/api/app/stock?limit=60"));
      document.getElementById("out").innerHTML = result.ok ? block(result.value) : errorBox(result.error);
    };
    await load(document.getElementById("refresh"));

    document.getElementById("refresh").addEventListener("click", (event) => load(event.currentTarget));
    document.getElementById("out").addEventListener("click", async (event) => {
      const button = event.target.closest("[data-restock]");
      if (!button) return;
      const field = document.querySelector(`[data-qty="${button.dataset.restock}"]`);
      const result = await withSpinner(button, () => post(`/api/app/products/${button.dataset.restock}/restock`, { quantite: Number(field.value) || 1 }));
      if (!result.ok) document.getElementById("out").insertAdjacentHTML("afterbegin", errorBox(result.error));
      await load(document.getElementById("refresh"));
    });
  },
};
