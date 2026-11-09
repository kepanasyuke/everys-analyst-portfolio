import { get } from "../api.js";
import { iconLabel } from "../icons.js";
import { eur, errorBox, esc, num, pageHead, qty, statusTag, stats, table, tag, withSpinner } from "../ui.js";

function kpiBlock(kpi) {
  return stats([
    ["Выручка за период", eur(kpi.ca)],
    ["Продаж за период", qty(kpi.ventes)],
    ["Средний чек", eur(kpi.panier)],
    ["Позиций в дефиците", qty(kpi.ruptures), kpi.ruptures ? "bad" : "good"],
    ["Стоимость склада", eur(kpi.valeur_stock)],
    ["Продаж сегодня", qty(kpi.aujourdhui)],
  ]);
}

function alertsBlock(items) {
  const rows = items.map((item) => [esc(item.nom), qty(item.stock_actuel), qty(item.seuil), statusTag(item.statut_stock)]);
  return rows.length ? table(["Товар", "Остаток", "Порог", ""], rows) : `<p class="muted">Дефицита нет — все позиции выше порога.</p>`;
}

function topBlock(items) {
  return table(["Товар", "Штук", "Выручка"], items.map((item) => [esc(item.nom), qty(item.quantite), eur(item.ca)]));
}

function salesBlock(items) {
  return table(["№", "Дата", "Аптека", "Сумма", "Статус"], items.map((item) => [esc(item.id), esc(item.date), esc(item.ville), eur(item.montant_ttc), statusTag(item.statut)]));
}

function journalBlock(items) {
  return table(["Время", "Действие", "Объект", "Кто"], items.map((item) => [esc(item.ts.slice(11, 19)), tag(item.action, "grey"), esc(item.cible), esc(item.acteur)]));
}

function render(data) {
  document.getElementById("kpi").innerHTML = kpiBlock(data.kpi);
  document.getElementById("alerts").innerHTML = alertsBlock(data.alerts);
  document.getElementById("top").innerHTML = topBlock(data.top);
  document.getElementById("sales").innerHTML = salesBlock(data.recent);
  document.getElementById("journal").innerHTML = journalBlock(data.journal);
  document.getElementById("stamp").textContent = `данные по ${data.kpi.reference} · период ${data.kpi.days} дн. · обновлено ${new Date().toLocaleTimeString("ru-RU")}`;
}

export default {
  slug: "app",
  code: "A0",
  group: "app",
  title: "Рабочее место",
  async mount(root) {
    root.innerHTML = `${pageHead("Приложение officine · дашборд", "Рабочее место аптеки: продажи, остатки, журнал",
      "Живые данные из SQLite: каждая продажа, пополнение и отмена пишутся в журнал и меняют остаток. Ниже — что происходит в сети за последние 30 дней данных.")}
      <div class="btn-row"><select id="days" style="max-width:180px"><option value="7">7 дней</option><option value="30" selected>30 дней</option><option value="90">90 дней</option></select><button class="btn" id="refresh">${iconLabel("refresh", "Обновить")}</button><a class="btn ghost" href="/api/app/export/sales.csv" download>${iconLabel("download", "Выгрузить продажи CSV")}</a><span class="muted" id="stamp"></span></div>
      <div id="kpi"></div>
      <div class="split">
        <div>
          <div class="card"><h3>Дефицит и порог</h3><div id="alerts"></div></div>
          <div class="card"><h3>Журнал действий</h3><div id="journal"></div><p class="muted">Каждая операция фиксируется: создание товара, правка цены, пополнение, продажа, отмена.</p></div>
        </div>
        <div>
          <div class="card"><h3>Топ препаратов по выручке</h3><div id="top"></div></div>
          <div class="card"><h3>Последние продажи</h3><div id="sales"></div><p class="muted">Отменить продажу можно на экране «Касса».</p></div>
        </div>
      </div>`;
    const load = async (button) => {
      const days = document.getElementById("days").value;
      const result = await withSpinner(button, () => get(`/api/app/overview?days=${days}`));
      if (result.ok) render(result.value);
      else document.getElementById("kpi").innerHTML = errorBox(result.error);
    };
    document.getElementById("refresh").addEventListener("click", (event) => load(event.currentTarget));
    await load(document.getElementById("refresh"));
  },
};
