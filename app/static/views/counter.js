import { get, post } from "../api.js";
import { eur, errorBox, esc, pageHead, qty, stats, table, withSpinner } from "../ui.js";

function pickerList(items) {
  return items.map((item) => `<button type="button" data-add="${esc(item.cip)}"><strong>${esc(item.nom)}</strong> · ${eur(item.prix_public)} · остаток ${qty(item.stock_actuel)}</button>`).join("");
}

function basketBlock(basket) {
  if (!basket.length) return `<p class="muted">Корзина пуста: найдите товар и добавьте его.</p>`;
  return `<div class="basket">${basket
    .map((line) => `<div class="basket-line">
      <span>${esc(line.nom)}</span>
      <input class="mini-input" type="number" min="1" max="${line.stock}" value="${line.quantite}" data-qty="${esc(line.cip)}" />
      <span>${eur(line.prix * line.quantite)}</span>
      <button class="btn ghost small" data-del="${esc(line.cip)}">×</button>
    </div>`)
    .join("")}</div>`;
}

function cancelCell(item) {
  return item.statut === "validee" ? `<button class="btn ghost small" data-cancel="${esc(item.id)}">Отменить</button>` : `<span class="muted">отменена</span>`;
}

function saleRow(item) {
  return [esc(item.id), esc(item.date), esc(item.ville), eur(item.montant_ttc), cancelCell(item)];
}

function receipt(data) {
  return `<div class="receipt"><strong>Продажа №${esc(data.id)} проведена</strong><br>
    ${data.date} · ${esc(data.officine)}<br>
    ${data.lignes.map((line) => `${esc(line.nom)} × ${qty(line.quantite)} — ${eur(line.prix_unitaire * line.quantite)}`).join("<br>")}
    <br><strong>Итого: ${eur(data.montant_ttc)}</strong>${data.remise_pct ? ` (скидка ${data.remise_pct} %)` : ""}</div>`;
}

export default {
  slug: "counter",
  code: "A2",
  group: "app",
  title: "Касса",
  async mount(root) {
    const state = { catalog: [], basket: [] };
    root.innerHTML = `${pageHead("Приложение officine · касса", "Продажа за прилавком: от корзины до чека",
      "Остаток списывается в момент проведения, отрицательный остаток невозможен, скидка выше 30 % требует титуляра. Отмена возвращает товар на склад и пишется в журнал.")}
      <div class="split">
        <div>
          <div class="card">
            <div class="grid two">
              <label>Аптека<select id="off"></select></label>
              <label>Канал<select id="canal"><option value="comptoir">comptoir</option><option value="drive">drive</option><option value="livraison">livraison</option></select></label>
              <label>Роль<select id="role"><option value="pharmacien">фармацевт</option><option value="titulaire">титуляр</option></select></label>
              <label>Скидка, %<input type="number" id="remise" min="0" max="30" step="1" value="0" /></label>
            </div>
            <p class="muted" id="rule">Фармацевт: скидка до 30 %. Выше — только титуляр, с записью в журнал.</p>
          </div>
          <div class="card">
            <label>Найти товар<input type="text" id="q" placeholder="Название или CIP13" /></label>
            <div class="picker" id="picker"></div>
          </div>
        </div>
        <div>
          <div class="card">
            <h3>Корзина</h3>
            <div id="basket"></div>
            <div class="btn-row"><strong id="total">0,00 €</strong><button class="btn" id="submit">Провести продажу</button></div>
          </div>
          <div id="receipt"></div>
          <div class="card">
            <h3>Последние продажи</h3>
            <div id="recent"></div>
          </div>
        </div>
      </div>`;

    const totals = () => {
      const remise = Number(document.getElementById("remise").value) || 0;
      return state.basket.reduce((sum, line) => sum + line.prix * line.quantite, 0) * (1 - remise / 100);
    };
    const paint = () => {
      document.getElementById("basket").innerHTML = basketBlock(state.basket);
      document.getElementById("total").textContent = eur(totals());
    };
    const paintPicker = (term = "") => {
      const found = state.catalog.filter((item) => `${item.nom} ${item.cip} ${item.dci}`.toLowerCase().includes(term.toLowerCase())).slice(0, 40);
      document.getElementById("picker").innerHTML = pickerList(found) || `<p class="muted">Ничего не найдено</p>`;
    };
    const loadSales = async () => {
      const result = await get("/api/app/sales?limit=8");
      document.getElementById("recent").innerHTML = table(["№", "Дата", "Город", "Сумма", ""], result.items.map(saleRow));
    };

    const catalog = await get("/api/app/products?limit=200");
    state.catalog = catalog.items;
    const pharmacies = await get("/api/app/pharmacies");
    document.getElementById("off").innerHTML = pharmacies.items.map((item) => `<option value="${item.id}">${esc(item.nom)} · ${esc(item.ville)}</option>`).join("");
    paintPicker();
    paint();
    await loadSales();

    document.getElementById("q").addEventListener("input", (event) => paintPicker(event.target.value));
    document.getElementById("remise").addEventListener("input", paint);
    document.getElementById("role").addEventListener("change", (event) => {
      const titulaire = event.target.value === "titulaire";
      document.getElementById("remise").max = titulaire ? "100" : "30";
      document.getElementById("rule").textContent = titulaire
        ? "Титуляр: скидка до 100 %, каждое подтверждение попадает в журнал."
        : "Фармацевт: скидка до 30 %. Выше — только титуляр, с записью в журнал.";
    });
    document.getElementById("picker").addEventListener("click", (event) => {
      const button = event.target.closest("[data-add]");
      const item = button && state.catalog.find((entry) => entry.cip === button.dataset.add);
      if (!item) return;
      const line = state.basket.find((entry) => entry.cip === item.cip);
      if (line) line.quantite = Math.min(line.quantite + 1, line.stock);
      else state.basket.push({ cip: item.cip, nom: item.nom, prix: item.prix_public, quantite: 1, stock: item.stock_actuel });
      paint();
    });
    document.getElementById("basket").addEventListener("input", (event) => {
      const field = event.target.closest("[data-qty]");
      const line = field && state.basket.find((entry) => entry.cip === field.dataset.qty);
      if (!line) return;
      line.quantite = Math.max(1, Math.min(Number(field.value) || 1, line.stock));
      paint();
    });
    document.getElementById("basket").addEventListener("click", (event) => {
      const button = event.target.closest("[data-del]");
      if (!button) return;
      state.basket = state.basket.filter((entry) => entry.cip !== button.dataset.del);
      paint();
    });
    document.getElementById("submit").addEventListener("click", async (event) => {
      const body = {
        officine_id: Number(document.getElementById("off").value),
        canal: document.getElementById("canal").value,
        remise_pct: Number(document.getElementById("remise").value) || 0,
        role: document.getElementById("role").value,
        acteur: document.getElementById("role").value,
        lignes: state.basket.map((line) => ({ cip: line.cip, quantite: line.quantite })),
      };
      const result = await withSpinner(event.currentTarget, () => post("/api/app/sales", body));
      document.getElementById("receipt").innerHTML = result.ok ? receipt(result.value) : errorBox(result.error);
      if (!result.ok) return;
      state.basket = [];
      paint();
      await loadSales();
      paintPicker(document.getElementById("q").value);
    });
    document.getElementById("recent").addEventListener("click", async (event) => {
      const button = event.target.closest("[data-cancel]");
      if (!button) return;
      const result = await withSpinner(button, () => post(`/api/app/sales/${button.dataset.cancel}/cancel`, {}));
      if (!result.ok) document.getElementById("receipt").innerHTML = errorBox(result.error);
      await loadSales();
    });
  },
};
