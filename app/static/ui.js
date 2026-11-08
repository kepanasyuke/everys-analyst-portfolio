const ENTITIES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

const W = 640;
const H = 220;
const PAD_BOTTOM = 28;

export const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ENTITIES[char]);

export const md = (value) =>
  esc(value)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|\s)_([^_]+)_(?=\s|$)/g, "$1<em>$2</em>");

export const num = (value, digits = 2) => (Number.isFinite(Number(value)) ? Number(value).toFixed(digits).replace(".", ",") : "—");

export const pct = (value) => `${num(Number(value) * 100, 1)} %`;

export function pageHead(kicker, title, lead) {
  return `<header class="page-head"><span class="kicker">${esc(kicker)}</span><h1>${esc(title)}</h1><p class="lead">${lead}</p></header>`;
}

export function tag(text, tone = "") {
  return `<span class="tag ${tone}">${esc(text)}</span>`;
}

export function stat(label, value, tone = "") {
  return `<div class="stat"><span class="k">${esc(label)}</span><span class="v ${tone}">${esc(value)}</span></div>`;
}

export function stats(rows) {
  return `<div class="stat-row">${rows.map(([label, value, tone]) => stat(label, value, tone)).join("")}</div>`;
}

export function table(columns, rows) {
  const head = columns.map((column) => `<th>${esc(column)}</th>`).join("");
  const body = rows
    .map((row) => `<tr>${row.map((cell) => `<td>${cell ?? ""}</td>`).join("")}</tr>`)
    .join("");
  return `<div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

export function codeBlock(code) {
  const safe = esc(code)
    .replace(/\b(SELECT|FROM|JOIN|WHERE|GROUP BY|ORDER BY|LIMIT|ON|AS|AND|INNER|LEFT)\b/g, '<span class="kw">$1</span>')
    .replace(/'([^']*)'/g, '<span class="str">\'$1\'</span>');
  return `<pre>${safe}</pre>`;
}

export function bars(points, color = "#9e12c9") {
  const values = points.map((point) => Number(point.y) || 0);
  const max = Math.max(...values, 1);
  const step = W / Math.max(points.length, 1);
  const drawable = H - PAD_BOTTOM - 10;
  const marks = points
    .map((point, index) => {
      const value = Number(point.y) || 0;
      const height = Math.max(3, (value / max) * drawable);
      const x = index * step + step * 0.16;
      const label = String(point.x ?? "").slice(0, 12);
      return `<rect x="${x.toFixed(1)}" y="${(H - PAD_BOTTOM - height).toFixed(1)}" width="${(step * 0.68).toFixed(1)}" height="${height.toFixed(1)}" rx="3" fill="${color}"><title>${esc(point.x)}: ${esc(point.y)}</title></rect>
        <text x="${(index * step + step / 2).toFixed(1)}" y="${H - 10}" text-anchor="middle" font-size="9" fill="#8a8a8a">${esc(label)}</text>`;
    })
    .join("");
  return `<svg viewBox="0 0 ${W} ${H}" class="chart" role="img" aria-label="график">${marks}</svg>`;
}

export function line(points, color = "#4bd411") {
  const values = points.map((point) => Number(point.y) || 0);
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const span = max - min || 1;
  const step = W / Math.max(points.length - 1, 1);
  const drawable = H - PAD_BOTTOM - 10;
  const coords = points.map((point, index) => {
    const value = Number(point.y) || 0;
    return [index * step, H - PAD_BOTTOM - ((value - min) / span) * drawable];
  });
  const path = coords.map(([x, y], index) => `${index ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const dots = coords
    .map(([x, y], index) => `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3" fill="${color}"><title>${esc(points[index].x)}: ${esc(points[index].y)}</title></circle>
      <text x="${x.toFixed(1)}" y="${H - 10}" text-anchor="middle" font-size="9" fill="#8a8a8a">${esc(String(points[index].x).slice(0, 12))}</text>`)
    .join("");
  return `<svg viewBox="0 0 ${W} ${H}" class="chart" role="img" aria-label="динамика"><path d="${path}" fill="none" stroke="${color}" stroke-width="2.5" />${dots}</svg>`;
}

export function chart(spec) {
  const points = (spec.x || []).map((label, index) => ({ x: label, y: (spec.y || [])[index] }));
  return spec.type === "line" ? line(points) : spec.type === "bar" ? bars(points) : "";
}

export function field(label, control) {
  return `<label>${esc(label)}${control}</label>`;
}

export function chips(items) {
  return items.map((item) => `<button class="btn ghost small" type="button" data-chip="${esc(item)}">${esc(item)}</button>`).join("");
}

export async function withSpinner(button, task) {
  const original = button.innerHTML;
  button.disabled = true;
  button.innerHTML = '<span class="spinner"></span> Считаю…';
  try {
    return { ok: true, value: await task() };
  } catch (error) {
    return { ok: false, error: error.message || String(error) };
  } finally {
    button.disabled = false;
    button.innerHTML = original;
  }
}

export function errorBox(message) {
  return `<div class="error" data-error="1">${esc(message)}</div>`;
}

export function note(message) {
  return `<div class="note">${message}</div>`;
}

export function warn(message) {
  return `<div class="warn">${message}</div>`;
}

export function scoreTone(score) {
  return score >= 85 ? "good" : score >= 60 ? "" : "bad";
}

export const eur = (value) => `${Number(value || 0).toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`;

export const qty = (value) => Number(value || 0).toLocaleString("ru-RU");

export function statusTag(status) {
  const map = { ok: ["в наличии", "green"], alerte: ["порог", "amber"], rupture: ["дефицит", "red"], validee: ["проведена", "green"], annulee: ["отменена", "red"] };
  const [label, tone] = map[status] || [status, "grey"];
  return tag(label, tone);
}
