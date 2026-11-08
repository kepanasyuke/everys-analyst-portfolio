import { get, post, query } from "../api.js";
import { chips, errorBox, esc, md, pageHead, stats, tag, withSpinner } from "../ui.js";

function termCard(entry) {
  return `<div class="card">
    <div class="btn-row">${tag(entry.domain_label, "grey")}${tag(`в корпусе: ${entry.uses}`, entry.uses ? "green" : "amber")}</div>
    <h3>${esc(entry.fr)} <span class="muted">→ ${esc(entry.ru)}</span></h3>
    <p>${md(entry.def_fr)}</p>
    <p>${md(entry.def_ru)}</p>
    ${(entry.synonyms || []).length ? `<p class="muted">Синонимы: ${entry.synonyms.map(esc).join(", ")}</p>` : ""}
    ${(entry.examples || []).length ? `<p class="muted">Пример: ${esc(entry.examples[0])}</p>` : ""}
  </div>`;
}

function searchReport(data) {
  return `${stats([
    ["Найдено", String((data.matches || []).length)],
    ["Словарь", String(data.total)],
    ["Статус", data.missing ? "нет совпадений" : "есть", data.missing ? "bad" : "good"],
  ])}
  ${data.missing ? `<div class="warn">Термин не найден. Проверьте французское написание и попробуйте синоним: <em>ordonnance, tiers payant, rupture, CIP13</em>.</div>` : ""}
  ${(data.matches || []).map(termCard).join("")}`;
}

function overview(data) {
  return `${stats([
    ["Терминов", String(data.terms)],
    ["Используются в корпусе", String(data.used_in_corpus), "good"],
    ["Покрытие", `${Math.round(data.coverage * 100)} %`],
    ["Доменов", String((data.domains || []).length)],
  ])}
  <div class="card">
    <h3>Домены</h3>
    <p>${(data.domains || []).map((domain) => `${tag(`${domain.label} · ${domain.count}`, "grey")}`).join(" ")}</p>
  </div>
  <div class="card">
    <h3>Пробелы терминологии</h3>
    <p class="muted">Частотные слова корпуса, которых нет в глоссарии — кандидаты на добавление.</p>
    <p>${(data.uncovered || []).map((item) => tag(`${item.term} · ${item.count}`, "amber")).join(" ") || "—"}</p>
  </div>`;
}

function annotateReport(data) {
  return `<div class="card">
    <div class="btn-row">${tag(`покрытие терминов ${Math.round(data.coverage * 100)} %`, data.coverage > 0.15 ? "green" : "amber")}</div>
    ${(data.terms || []).map((term) => `<p><strong>${esc(term.fr)}</strong> → ${esc(term.ru)}<br><span class="muted">${esc(term.def_ru)}</span></p>`).join("") || "<p class='muted'>Знакомых терминов не найдено — текст вне домена или нужен новый термин.</p>"}
  </div>`;
}

export default {
  slug: "glossary",
  code: "P08",
  title: "Глоссарий FR↔RU",
  async mount(root) {
    const meta = await get("/api/p08/overview").catch(() => ({ terms: 0, domains: [], uncovered: [] }));
    root.innerHTML = `${pageHead("P08 · домен и язык", "Глоссарий аптечного домена FR↔RU",
      "30 терминов officine: ordonnance, tiers payant, créance, rupture, CIP13, chaîne du froid. Поиск по обеим языковым сторонам, примеры употребления, покрытие корпуса и пробелы терминологии.")}
      <div class="card">
        <label>Термин или фраза на французском / русском
          <input type="text" id="q" value="remise" />
        </label>
        <div class="btn-row" id="chips">${chips(["remise", "tiers payant", "ordonnance", "rupture", "chaîne du froid", "idFlux", "скидка"])}</div>
        <button class="btn" id="run">Найти</button>
      </div>
      <div id="results"></div>
      <h2>Обзор словаря</h2>
      <div id="overview">${overview(meta)}</div>
      <h2>Аннотировать французский текст</h2>
      <div class="split">
        <div class="card">
          <label>Фрагмент документа<textarea id="text">La créance rejetée doit être retransmise sous 48 heures ; l'ordonnance est délivrée en tiers payant.</textarea></label>
          <button class="btn" id="annotate">Разметить термины</button>
        </div>
        <div id="annotation"><div class="card"><h3>Разметка появится здесь</h3></div></div>
      </div>`;
    document.getElementById("chips").addEventListener("click", (event) => {
      const chip = event.target.closest("[data-chip]");
      if (chip) document.getElementById("q").value = chip.dataset.chip;
    });
    document.getElementById("run").addEventListener("click", async (event) => {
      const value = document.getElementById("q").value.trim();
      const results = document.getElementById("results");
      if (!value) {
        results.innerHTML = errorBox("Введите термин");
        return;
      }
      const result = await withSpinner(event.currentTarget, () => query("/api/p08/search", { q: value, limit: 6 }));
      results.innerHTML = result.ok ? searchReport(result.value) : errorBox(result.error);
    });
    document.getElementById("annotate").addEventListener("click", async (event) => {
      const text = document.getElementById("text").value;
      const result = await withSpinner(event.currentTarget, () => post("/api/p08/annotate", { text }));
      document.getElementById("annotation").innerHTML = result.ok ? annotateReport(result.value) : errorBox(result.error);
    });
    document.getElementById("run").click();
  },
};
