import { get, post } from "../api.js";
import { icon, iconLabel } from "../icons.js";
import { eur, errorBox, esc, pageHead, qty, stats, statusTag, table, tag, withSpinner } from "../ui.js";

const PAGE = 10;

function rowOf(item) {
  return [
    esc(item.id),
    esc(item.date),
    `${esc(item.officine)}<br><span class="muted">${esc(item.ville)} · ${esc(item.canal)}</span>`,
    eur(item.montant_ttc),
    statusTag(item.statut),
    `<span class="row-actions"><a class="btn ghost small" href="/api/app/sales/${esc(item.id)}/receipt" target="_blank" rel="noopener">${iconLabel("receipt", "Чек", 14)}</a>${item.statut === "validee" ? `<button class="btn ghost small" data-return="${esc(item.id)}">${iconLabel("undo", "Вернуть", 14)}</button>` : ""}</span>`,
  ];
}

function linesForm(sale) {
  return sale.lignes
    .map((line) => {
      const returned = (sale.retours || []).flatMap((item) => item.lignes).filter((item) => item.cip === line.cip).reduce((sum, item) => sum + item.quantite, 0);
      const available = line.quantite - returned;
      return `<div class="basket-line">
        <span>${esc(line.nom)}<br><span class="muted">продано ${qty(line.quantite)}, возвращено ${qty(returned)}</span></span>
        <input class="mini-input" type="number" min="0" max="${available}" value="${available}" data-back="${esc(line.cip)}" ${available ? "" : "disabled"} />
        <span>${eur(line.prix_unitaire)}</span>
        <span class="muted">${tag(`доступно ${available}`, available ? "grey" : "red")}</span>
      </div>`;
    })
    .join("");
}

function returnPanel(sale) {
  return `<div class="card">
    <div class="btn-row">${tag(`продажа №${sale.id}`, "grey")}${statusTag(sale.statut)}<a href="/api/app/sales/${sale.id}/receipt" target="_blank" rel="noopener" class="btn ghost small">Чек</a></div>
    <h3>Возврат по продаже</h3>
    <div class="basket">${linesForm(sale)}</div>
    <div class="btn-row"><button class="btn" id="do-return">${iconLabel("undo", "Оформить возврат")}</button><button class="btn ghost" id="cancel-return">Отмена</button></div>
    <p class="muted">Вернуть можно не больше проданного и не больше остатка возврата: количество ограничено в полях.</p>
  </div>`;
}

export default {
  slug: "sales",
  code: "A5",
  group: "app",
  title: "Архив продаж",
  async mount(root) {
    const state = { offset: 0, saleId: 0, items: [] };
    root.innerHTML = `${pageHead("Приложение officine · архив", "Архив продаж: фильтры, чеки, возвраты",
      "Продажи за период с фильтром по статусу. Чек открывается как печатная форма, возврат оформляется здесь же и возвращает товар на склад с записью в журнал.")}
      <div class="card">
        <div class="grid two">
          <label>С даты<input type="date" id="from" /></label>
          <label>По дату<input type="date" id="to" /></label>
          <label>Статус<select id="statut"><option value="">все</option><option value="validee">проведена</option><option value="annulee">отменена</option></select></label>
        </div>
        <div class="btn-row">
          <button class="btn" id="apply">${iconLabel("search", "Показать")}</button>
          <a class="btn ghost" id="export" href="/api/app/export/sales.csv" download>${iconLabel("download", "Выгрузить CSV")}</a>
        </div>
      </div>
      <div id="totals"></div>
      <div class="card"><div id="table"></div><div class="btn-row" id="pager"></div></div>
      <div id="panel"></div>`;

    const params = () => {
      const query = new URLSearchParams({ limit: PAGE, offset: state.offset });
      const statut = document.getElementById("statut").value;
      if (statut) query.set("statut", statut);
      if (document.getElementById("from").value) query.set("date_from", document.getElementById("from").value);
      if (document.getElementById("to").value) query.set("date_to", document.getElementById("to").value);
      return query;
    };
    const load = async (button) => {
      const result = await withSpinner(button, () => get(`/api/app/sales?${params()}`));
      if (!result.ok) {
        document.getElementById("table").innerHTML = errorBox(result.error);
        return;
      }
      state.items = result.value.items;
      const total = result.value.total;
      document.getElementById("totals").innerHTML = stats([["Продаж по фильтру", qty(total)], ["На странице", qty(state.items.length)], ["Сумма страницы", eur(state.items.reduce((sum, item) => sum + item.montant_ttc, 0))]]);
      document.getElementById("table").innerHTML = state.items.length ? table(["№", "Дата", "Аптека", "Сумма", "Статус", "Действия"], state.items.map(rowOf)) : `<div class="empty">${icon("archive", 18)}<span>По этому фильтру продаж нет</span></div>`;
      document.getElementById("pager").innerHTML = `<button class="btn ghost small" id="prev" ${state.offset ? "" : "disabled"}>${iconLabel("chevron-left", "Назад", 14)}</button><span class="muted">${state.offset + 1}–${state.offset + state.items.length} из ${qty(total)}</span><button class="btn ghost small" id="next" ${state.offset + PAGE < total ? "" : "disabled"}>${iconLabel("chevron-right", "Вперёд", 14)}</button>`;
      document.getElementById("export").href = `/api/app/export/sales.csv?${params()}`;
    };
    const openReturn = async (saleId) => {
      const sale = await get(`/api/app/sales/${saleId}`);
      state.saleId = saleId;
      document.getElementById("panel").innerHTML = returnPanel(sale);
    };

    document.getElementById("apply").addEventListener("click", (event) => {
      state.offset = 0;
      load(event.currentTarget);
    });
    ["from", "to"].forEach((id) => {
      document.getElementById(id).addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        state.offset = 0;
        load(document.getElementById("apply"));
      });
    });
    document.getElementById("pager").addEventListener("click", (event) => {
      const target = event.target.closest("#prev, #next");
      if (!target) return;
      state.offset = target.id === "prev" ? Math.max(0, state.offset - PAGE) : state.offset + PAGE;
      load(document.getElementById("apply"));
    });
    document.getElementById("table").addEventListener("click", (event) => {
      const button = event.target.closest("[data-return]");
      if (button) openReturn(button.dataset.return);
    });
    document.getElementById("panel").addEventListener("click", async (event) => {
      if (event.target.id === "cancel-return") document.getElementById("panel").innerHTML = "";
      if (event.target.id !== "do-return") return;
      const lignes = [...document.querySelectorAll("[data-back]")].map((input) => ({ cip: input.dataset.back, quantite: Number(input.value) })).filter((line) => line.quantite > 0);
      const result = await withSpinner(event.target, () => post(`/api/app/sales/${state.saleId}/return`, { lignes }));
      document.getElementById("panel").innerHTML = result.ok ? `<div class="receipt"><strong>Возврат оформлен</strong><br>Продажа №${result.value.vente_id} · сумма возврата ${eur(result.value.montant)}<br>${result.value.lignes.map((line) => `${esc(line.nom)} × ${qty(line.quantite)}`).join("<br>")}</div>` : errorBox(result.error);
      await load(document.getElementById("apply"));
    });
    await load(document.getElementById("apply"));
  },
};
