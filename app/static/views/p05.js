import { get, post } from "../api.js";
import { errorBox, esc, num, pageHead, pct, stats, tag, withSpinner } from "../ui.js";

function form() {
  return `<div class="card">
    <h3>Данные эксперимента</h3>
    <div class="grid two">
      <label>Группа A · посетители<input type="number" id="va" value="2400" min="1" /></label>
      <label>Группа A · конверсии<input type="number" id="ca" value="480" min="0" /></label>
      <label>Группа B · посетители<input type="number" id="vb" value="2400" min="1" /></label>
      <label>Группа B · конверсии<input type="number" id="cb" value="528" min="0" /></label>
      <label>Уровень значимости α<input type="number" id="alpha" value="0.05" step="0.01" /></label>
      <label>Минимальный эффект MDE<input type="number" id="mde" value="0.1" step="0.01" /></label>
    </div>
    <div class="btn-row"><button class="btn" id="run">Проверить гипотезу</button></div>
    <div id="scenarios" class="btn-row"></div>
  </div>`;
}

function verdict(data) {
  const tone = data.tone || (data.verdict === "rollout" ? "green" : data.verdict === "rollback" ? "red" : "amber");
  const label = data.verdict === "rollout" ? "Раскатывать" : data.verdict === "rollback" ? "Откатывать" : "Продолжать тест";
  return `<div class="card">
    <div class="btn-row">${tag(label, tone)}${tag(`p = ${num(data.p_value, 4)}`, data.significant ? "green" : "grey")}${tag(`α = ${num(data.alpha, 2)}`, "grey")}</div>
    <p>${esc(data.decision)}</p>
    <p class="muted">${esc(data.guardrail)}</p>
  </div>`;
}

function report(data) {
  return `${stats([
    ["A · конверсия", pct(data.a.rate)],
    ["B · конверсия", pct(data.b.rate)],
    ["Относительный прирост", `${num(data.lift_pct, 2)} %`, data.lift_pct > 0 ? "good" : "bad"],
    ["Разница, п.п.", num(data.diff_pp, 2)],
    ["z-оценка", num(data.z, 3)],
  ])}
  ${verdict(data)}
  <div class="split">
    <div class="card">
      <h3>Доверительный интервал</h3>
      <p>${data.ci.level} % интервал разницы: <strong>${num(data.ci.low * 100, 2)} … ${num(data.ci.high * 100, 2)} п.п.</strong></p>
      <p class="muted">${data.ci.low > 0 ? "Ноль вне интервала — эффект устойчиво положительный." : data.ci.high < 0 ? "Интервал целиком ниже нуля — эффект отрицательный." : "Интервал содержит ноль — эффект не отделён от шума."}</p>
    </div>
    <div class="card">
      <h3>Размер выборки</h3>
      <p>Нужно по ${num(data.sample.needed_per_arm, 0)} наблюдений на группу при MDE ${pct(data.mde)}.</p>
      <p>Сейчас набрано ${num(data.sample.current_total, 0)} за ${num(data.sample.days_elapsed, 0)} дн.</p>
      <p class="muted">${data.sample.extra_days ? `Ещё около ${num(data.sample.extra_days, 0)} дн. до мощности ${pct(data.power)}.` : "Мощность достигнута — можно принимать решение."}</p>
    </div>
  </div>`;
}

export default {
  slug: "ab-lab",
  code: "P05",
  title: "A/B Lab",
  async mount(root) {
    const meta = await get("/api/p05/scenarios").catch(() => ({ scenarios: [] }));
    root.innerHTML = `${pageHead("P05 · проверка гипотез", "A/B-тест без «на глаз»: z-тест, интервал, мощность",
      "Гипотеза «предзаполненная скидка 20 % поднимает средний чек» проверяется двухпропорциональным z-тестом с доверительным интервалом и расчётом необходимого размера выборки. Без scipy и numpy — только математика.")}
      <div class="split">${form()}<div id="out"><div class="card"><h3>Результат</h3><p class="muted">Заполните данные и нажмите «Проверить гипотезу».</p></div></div></div>`;
    const scenarios = meta.scenarios || [];
    const holder = document.getElementById("scenarios");
    holder.innerHTML = scenarios.map((item, index) => `<button class="btn ghost small" type="button" data-index="${index}">${esc(item.label)}</button>`).join("");
    holder.addEventListener("click", (event) => {
      const button = event.target.closest("[data-index]");
      const scenario = button && scenarios[Number(button.dataset.index)];
      if (!scenario) return;
      document.getElementById("va").value = scenario.a.visitors;
      document.getElementById("ca").value = scenario.a.conversions;
      document.getElementById("vb").value = scenario.b.visitors;
      document.getElementById("cb").value = scenario.b.conversions;
      document.getElementById("mde").value = scenario.mde;
    });
    document.getElementById("run").addEventListener("click", async (event) => {
      const body = {
        visitors_a: Number(document.getElementById("va").value),
        conversions_a: Number(document.getElementById("ca").value),
        visitors_b: Number(document.getElementById("vb").value),
        conversions_b: Number(document.getElementById("cb").value),
        alpha: Number(document.getElementById("alpha").value),
        mde: Number(document.getElementById("mde").value),
        days: 14,
      };
      const out = document.getElementById("out");
      const result = await withSpinner(event.currentTarget, () => post("/api/p05/test", body));
      out.innerHTML = result.ok ? report(result.value) : errorBox(result.error);
    });
  },
};
