import { get } from "../api.js";
import { eur, errorBox, esc, pageHead, qty, stats, table, withSpinner } from "../ui.js";

function rowsOf(items) {
  return items.map((item) => [esc(item.nom), esc(item.ville), esc(item.region), qty(item.surface_m2), qty(item.ventes), eur(item.ca), eur(item.panier)]);
}

function block(items) {
  const ca = items.reduce((sum, item) => sum + item.ca, 0);
  const ventes = items.reduce((sum, item) => sum + item.ventes, 0);
  return `${stats([
    ["Аптек в сети", qty(items.length)],
    ["Выручка сети", eur(ca)],
    ["Продаж всего", qty(ventes)],
    ["Средний чек сети", eur(ca / Math.max(ventes, 1))],
  ])}
  ${table(["Аптека", "Город", "Регион", "м²", "Продаж", "Выручка", "Средний чек"], rowsOf(items))}
  <p class="muted">Данные включают исторические продажи демо-периода и все продажи, проведённые в приложении.</p>`;
}

export default {
  slug: "pharmacies",
  code: "A4",
  group: "app",
  title: "Сеть аптек",
  async mount(root) {
    root.innerHTML = `${pageHead("Приложение officine · сеть", "Двенадцать аптек: выручка и средний чек",
      "Срез по офисинам сети: объём продаж, выручка и средний чек. Продажи, проведённые в кассе, сразу попадают в эту таблицу.")}
      <div class="btn-row"><button class="btn" id="refresh">Обновить</button></div>
      <div id="out"></div>`;
    const load = async (button) => {
      const result = await withSpinner(button, () => get("/api/app/pharmacies"));
      document.getElementById("out").innerHTML = result.ok ? block(result.value.items) : errorBox(result.error);
    };
    document.getElementById("refresh").addEventListener("click", (event) => load(event.currentTarget));
    await load(document.getElementById("refresh"));
  },
};
