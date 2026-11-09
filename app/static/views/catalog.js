import { get, patch, post, remove } from "../api.js";
import { icon, iconLabel } from "../icons.js";
import { eur, errorBox, esc, md, note, pageHead, qty, statusTag, stats, table, tag, withSpinner } from "../ui.js";

function rowsOf(items) {
  return items.map((item) => [
    `<strong>${esc(item.nom)}</strong><br><span class="muted">${esc(item.cip)} · ${esc(item.dci || "—")}</span>`,
    esc(item.categorie),
    eur(item.prix_public),
    qty(item.stock_actuel),
    qty(item.seuil),
    `${statusTag(item.statut_stock)} ${tag(`${item.taux_remboursement} %`, "grey")}`,
    `<span class="row-actions"><button class="btn ghost small" data-edit="${esc(item.cip)}">${iconLabel("edit", "Править", 14)}</button><button class="btn ghost small" data-history="${esc(item.cip)}">${iconLabel("history", "История", 14)}</button></span>`,
  ]);
}

function catalogBlock(data) {
  return `${stats([["Позиций", qty(data.total.n)], ["Категорий", qty(data.categories.length)], ["Стоимость выборки", eur(data.items.reduce((sum, item) => sum + item.valeur_stock, 0))]])}
  ${table(["Товар", "Категория", "Цена", "Остаток", "Порог", "Статус", ""], rowsOf(data.items))}`;
}

function editForm(item) {
  return `<div class="card">
    <div class="btn-row">${tag(item.cip, "grey")}${statusTag(item.statut_stock)}</div>
    <h3>${esc(item.nom)}</h3>
    <div class="grid two">
      <label>Цена, €<input type="number" id="edit-prix" step="0.01" min="0.01" value="${item.prix_public}" /></label>
      <label>Остаток<input type="number" id="edit-stock" step="1" min="0" value="${item.stock_actuel}" /></label>
      <label>Порог пополнения<input type="number" id="edit-seuil" step="1" min="0" value="${item.seuil}" /></label>
      <label>Ставка возмещения, %<input type="number" id="edit-taux" step="1" min="0" max="100" value="${item.taux_remboursement}" /></label>
    </div>
    <div class="btn-row">
      <button class="btn" id="save">${iconLabel("check", "Сохранить")}</button>
      <input class="mini-input" type="number" id="restock-qty" min="1" value="20" />
      <button class="btn ghost" id="restock">${iconLabel("plus", "Пополнить")}</button>
      <button class="btn ghost" id="remove">${iconLabel("trash", "Удалить")}</button>
    </div>
    <p class="muted">Удаление разрешено только для товара без продаж. Все действия попадают в журнал.</p>
  </div>`;
}

function createForm(categories) {
  return `<details class="card"><summary><strong>Новый товар</strong></summary>
    <div class="grid two">
      <label>CIP13<input type="text" id="new-cip" placeholder="3400930000123" maxlength="13" /></label>
      <label>Название<input type="text" id="new-nom" placeholder="Paracetamol 1 g" /></label>
      <label>Действующее вещество<input type="text" id="new-dci" placeholder="paracetamol" /></label>
      <label>Категория<input type="text" id="new-cat" list="cats" value="antalgique" /><datalist id="cats">${categories.map((item) => `<option value="${esc(item)}"></option>`).join("")}</datalist></label>
      <label>Цена, €<input type="number" id="new-prix" step="0.01" min="0.01" value="3.50" /></label>
      <label>Остаток<input type="number" id="new-stock" step="1" min="0" value="20" /></label>
      <label>Порог<input type="number" id="new-seuil" step="1" min="0" value="5" /></label>
      <label>Ставка возмещения, %<input type="number" id="new-taux" step="1" min="0" max="100" value="65" /></label>
    </div>
    <div class="btn-row"><button class="btn" id="create">${iconLabel("plus", "Добавить в справочник")}</button></div>
  </details>`;
}

function historyBlock(data) {
  const rows = data.items.map((move) => [
    esc(String(move.ts).slice(0, 16).replace("T", " ")),
    tag(move.kind === "sale" ? "расход" : move.kind === "return" ? "возврат" : "приход", move.quantite > 0 ? "green" : "amber"),
    `${move.quantite > 0 ? "+" : ""}${qty(move.quantite)}`,
    esc(move.ref),
  ]);
  return `<div class="card">
    <div class="btn-row"><h3>${esc(data.product.nom)} — движения</h3></div>
    ${stats([["Остаток", qty(data.product.stock_actuel)], ["Порог", qty(data.product.seuil)], ["Цена", eur(data.product.prix_public)]])}
    ${rows.length ? table(["Когда", "Тип", "Кол-во", "Источник"], rows) : `<p class="muted">Движений ещё не было.</p>`}
  </div>`;
}

export default {
  slug: "catalog",
  code: "A1",
  group: "app",
  title: "Каталог",
  async mount(root) {
    const state = { items: [], current: "" };
    root.innerHTML = `${pageHead("Приложение officine · справочник", "Каталог товаров и остатков",
      "Поиск по названию, действующему веществу и коду CIP13. Правка цены и остатка, пополнение, добавление новой позиции — всё в одной таблице.")}
      <div class="card">
        <div class="btn-row">
          <input type="text" id="q" placeholder="Название, DCI или CIP13" value="" style="max-width:280px" />
          <select id="cat"><option value="">Все категории</option></select>
          <button class="btn" id="search">${iconLabel("search", "Найти")}</button>
          <a class="btn ghost" href="/api/app/export/products.csv" download>${iconLabel("download", "Выгрузить CSV")}</a>
        </div>
      </div>
      <div id="table"></div>
      <div id="history"></div>
      <div id="editor"></div>
      <div id="create-slot"></div>`;
    const load = async (button, query = true) => {
      const params = new URLSearchParams({ q: query ? document.getElementById("q").value.trim() : "", category: document.getElementById("cat").value });
      const result = await withSpinner(button, () => get(`/api/app/products?${params}`));
      if (!result.ok) {
        document.getElementById("table").innerHTML = errorBox(result.error);
        return;
      }
      state.items = result.value.items;
      document.getElementById("cat").innerHTML = [`<option value="">Все категории</option>`, ...result.value.categories.map((item) => `<option value="${esc(item)}">${esc(item)}</option>`)].join("");
      document.getElementById("table").innerHTML = catalogBlock(result.value);
      document.getElementById("create-slot").innerHTML = createForm(result.value.categories);
      document.getElementById("editor").innerHTML = note("Выберите позицию кнопкой «Править», чтобы изменить цену, остаток или порог.");
    };
    const openEditor = (cip) => {
      const item = state.items.find((entry) => entry.cip === cip);
      if (!item) return;
      state.current = cip;
      document.getElementById("editor").innerHTML = editForm(item);
    };
    const refresh = async (button) => load(button, false);

    root.addEventListener("click", async (event) => {
      const edit = event.target.closest("[data-edit]");
      if (edit) openEditor(edit.dataset.edit);
      const history = event.target.closest("[data-history]");
      if (history) {
        const result = await get(`/api/app/products/${history.dataset.history}/movements`);
        document.getElementById("history").innerHTML = historyBlock(result);
      }
    });
    document.getElementById("search").addEventListener("click", (event) => load(event.currentTarget));
    document.getElementById("q").addEventListener("keydown", (event) => {
      if (event.key === "Enter") load(document.getElementById("search"));
    });
    document.getElementById("editor").addEventListener("click", async (event) => {
      const action = event.target.closest("#save, #restock, #remove");
      if (!action) return;
      if (action.id === "save") {
        const body = { prix_public: Number(document.getElementById("edit-prix").value), stock_actuel: Number(document.getElementById("edit-stock").value), seuil: Number(document.getElementById("edit-seuil").value), taux_remboursement: Number(document.getElementById("edit-taux").value) };
        const result = await withSpinner(action, () => patch(`/api/app/products/${state.current}`, body));
        if (!result.ok) document.getElementById("editor").insertAdjacentHTML("afterbegin", errorBox(result.error));
        await refresh(document.getElementById("search"));
      }
      if (action.id === "restock") {
        const result = await withSpinner(event.target, () => post(`/api/app/products/${state.current}/restock`, { quantite: Number(document.getElementById("restock-qty").value) }));
        if (!result.ok) document.getElementById("editor").insertAdjacentHTML("afterbegin", errorBox(result.error));
        await refresh(document.getElementById("search"));
      }
      if (action.id === "remove") {
        const result = await withSpinner(action, () => remove(`/api/app/products/${state.current}?acteur=analyste`));
        if (!result.ok) document.getElementById("editor").insertAdjacentHTML("afterbegin", errorBox(result.error));
        await refresh(document.getElementById("search"));
      }
    });
    document.getElementById("create-slot").addEventListener("click", async (event) => {
      const createButton = event.target.closest("#create");
      if (!createButton) return;
      const body = { cip: document.getElementById("new-cip").value.trim(), nom: document.getElementById("new-nom").value.trim(), dci: document.getElementById("new-dci").value.trim(), categorie: document.getElementById("new-cat").value.trim() || "autre", prix_public: Number(document.getElementById("new-prix").value), stock_actuel: Number(document.getElementById("new-stock").value), seuil: Number(document.getElementById("new-seuil").value), taux_remboursement: Number(document.getElementById("new-taux").value) };
      const result = await withSpinner(createButton, () => post("/api/app/products", body));
      if (!result.ok) document.getElementById("create-slot").insertAdjacentHTML("afterbegin", errorBox(result.error));
      await refresh(document.getElementById("search"));
    });
    await load(document.getElementById("search"));
  },
};
