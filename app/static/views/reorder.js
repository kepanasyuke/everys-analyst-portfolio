import { get, post } from "../api.js";
import { icon, iconLabel } from "../icons.js";
import { eur, errorBox, esc, pageHead, qty, stats, table, tag, withSpinner } from "../ui.js";

function rows(items) {
  return items.map((item) => [
    `<strong>${esc(item.nom)}</strong><br><span class="muted">${esc(item.cip)}</span>`,
    esc(item.categorie),
    qty(item.stock_actuel),
    qty(item.seuil),
    `<input class="mini-input" type="number" min="0" max="100000" value="${item.besoin}" data-order="${esc(item.cip)}" aria-label="Количество к заказу ${esc(item.nom)}" />`,
    eur(item.prix_public),
  ]);
}

function block(data) {
  const plan = data.plan;
  const summary = plan.summary;
  const categories = summary.categories.map((item) => tag(`${item.categorie}: ${item.positions} поз. / ${item.units} шт.`, "grey")).join(" ");
  return `${stats([
    ["Позиций к заказу", qty(summary.positions), summary.positions ? "bad" : "good"],
    ["Штук в заказе по расчёту", qty(summary.units)],
    ["Полный дефицит", qty(summary.ruptures), summary.ruptures ? "bad" : "good"],
    ["Правило", plan.rule],
  ])}
  ${note(plan)}
  ${plan.items.length ? table(["Товар", "Категория", "Остаток", "Порог", "Заказать, шт.", "Цена"], rows(plan.items)) : `<div class="empty">${icon("check", 18)}<span>Пополнять нечего: все позиции выше порога.</span></div>`}
  ${categories ? `<p class="muted">По категориям: ${categories}</p>` : ""}
  <h3>Последние заказы</h3>
  ${data.recent.length ? table(["Когда", "Кто", "Позиций", "Штук"], data.recent.map((item) => [esc(String(item.ts).slice(0, 16).replace("T", " ")), esc(item.acteur), qty(item.positions), qty(item.units)])) : `<div class="empty">${icon("truck", 18)}<span>Заказов ещё не было.</span></div>`}`;
}

function note(plan) {
  return `<div class="note">Расчёт на ${esc(plan.generated_at)}: ${esc(plan.rule)}. Количество можно изменить перед оформлением — заказ применяется одной транзакцией и пишется в журнал.</div>`;
}

export default {
  slug: "reorder",
  code: "A6",
  group: "app",
  title: "Пополнение",
  async mount(root) {
    root.innerHTML = `${pageHead("Приложение officine · пополнение", "Réassort: что заказать по порогам",
      "Позиции с остатком ниже порога: система считает потребность как «порог × 2 минус остаток», минимум пять штук. Заказ оформляется одной транзакцией, остатки растут, в журнале появляется запись «stock.reorder».")}
      <div class="btn-row"><button class="btn" id="refresh">${iconLabel("refresh", "Обновить")}</button><button class="btn green" id="order">${iconLabel("check", "Оформить заказ")}</button></div>
      <div id="out"></div>`;

    const load = async (button) => {
      const result = await withSpinner(button, () => get("/api/app/reorder?limit=60"));
      document.getElementById("out").innerHTML = result.ok ? block(result.value) : errorBox(result.error);
    };

    document.getElementById("refresh").addEventListener("click", (event) => load(event.currentTarget));
    document.getElementById("order").addEventListener("click", async (event) => {
      const lignes = [...document.querySelectorAll("[data-order]")].map((input) => ({ cip: input.dataset.order, quantite: Number(input.value) })).filter((line) => line.quantite > 0);
      if (!lignes.length) {
        document.getElementById("out").insertAdjacentHTML("afterbegin", errorBox("Нет позиций для заказа"));
        return;
      }
      const result = await withSpinner(event.currentTarget, () => post("/api/app/reorder", { lignes }));
      if (!result.ok) {
        document.getElementById("out").insertAdjacentHTML("afterbegin", errorBox(result.error));
        return;
      }
      document.getElementById("out").insertAdjacentHTML("afterbegin", `<div class="receipt"><strong>Заказ №${result.value.batch} оформлен</strong><br>Позиций: ${qty(result.value.positions)} · штук: ${qty(result.value.units)}</div>`);
      await load(document.getElementById("refresh"));
    });
    await load(document.getElementById("refresh"));
  },
};
