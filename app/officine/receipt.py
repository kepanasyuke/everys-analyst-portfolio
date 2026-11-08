"""Печатная форма чека: самостоятельная HTML-страница со стилями для печати."""

from __future__ import annotations

from html import escape

from app.officine import logic, returns

STYLE = """
:root { --violet:#9e12c9; --ink:#1f1f24; --muted:#7b7b86; }
* { box-sizing:border-box; }
body { margin:0; padding:24px; background:#f4f4f6; color:var(--ink); font:14px/1.5 "Segoe UI",Roboto,Arial,sans-serif; }
.receipt { max-width:640px; margin:0 auto; background:#fff; border-radius:6px; padding:28px 30px; box-shadow:0 2px 14px rgba(0,0,0,.08); }
.brand { display:flex; justify-content:space-between; align-items:baseline; border-bottom:3px solid var(--violet); padding-bottom:10px; margin-bottom:16px; }
.brand strong { font-size:19px; letter-spacing:1.5px; color:var(--violet); text-transform:uppercase; }
.meta { display:grid; grid-template-columns:1fr 1fr; gap:4px 18px; font-size:13px; margin-bottom:14px; }
.meta span { color:var(--muted); }
table { width:100%; border-collapse:collapse; margin:8px 0 12px; }
th,td { padding:6px 4px; border-bottom:1px solid #ececf0; text-align:left; font-size:13px; }
th { font-size:11px; text-transform:uppercase; letter-spacing:.6px; color:var(--muted); }
.num { text-align:right; white-space:nowrap; }
.total { display:flex; justify-content:space-between; font-size:17px; font-weight:600; border-top:2px solid var(--ink); padding-top:10px; margin-top:6px; }
h2 { font-size:13px; text-transform:uppercase; letter-spacing:.8px; color:var(--muted); margin:18px 0 4px; }
.foot { margin-top:18px; font-size:11px; color:var(--muted); border-top:1px dashed #d9d9de; padding-top:10px; }
.toolbar { max-width:640px; margin:0 auto 12px; display:flex; gap:10px; }
button { border:0; border-radius:20px; background:var(--violet); color:#fff; padding:9px 18px; font:inherit; cursor:pointer; }
@media print {
  body { background:#fff; padding:0; }
  .receipt { box-shadow:none; border-radius:0; max-width:none; padding:0; }
  .toolbar { display:none; }
}
"""


def money(value) -> str:
    return f"{float(value or 0):,.2f}".replace(",", " ").replace(".", ",") + " €"


def line_rows(sale: dict) -> str:
    return "".join(f"<tr><td>{escape(str(line['nom']))}</td><td class='num'>{int(line['quantite'])}</td><td class='num'>{money(line['prix_unitaire'])}</td><td class='num'>{money(float(line['prix_unitaire']) * int(line['quantite']))}</td></tr>" for line in sale["lignes"])


def return_rows(retours: list[dict]) -> str:
    return "".join(f"<tr><td>{escape(str(item['ts'])[:16].replace('T', ' '))}</td><td>{escape(str(item['acteur']))}</td><td class='num'>{money(item['montant'])}</td></tr>" for item in retours)


def meta_block(sale: dict) -> str:
    return f"<div class='meta'><div><span>Аптека</span><br>{escape(str(sale['officine']))}</div><div><span>Город</span><br>{escape(str(sale['ville']))}</div><div><span>Дата</span><br>{escape(str(sale['date']))}</div><div><span>Чек</span><br>№ {int(sale['id'])}</div></div>"


def returns_block(retours: list[dict]) -> str:
    return f"<h2>Возвраты</h2><table><thead><tr><th>Дата</th><th>Кто</th><th class='num'>Сумма</th></tr></thead><tbody>{return_rows(retours)}</tbody></table>" if retours else ""


def page(sale: dict, retours: list[dict]) -> str:
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Чек №{int(sale['id'])}</title><style>{STYLE}</style></head>
<body>
<div class="toolbar"><button onclick="window.print()">Печать</button><a href="/#/sales">К архиву продаж</a></div>
<div class="receipt">
  <div class="brand"><strong>WinPharma</strong><span>Everys · officine</span></div>
  {meta_block(sale)}
  <table><thead><tr><th>Позиция</th><th class='num'>Кол-во</th><th class='num'>Цена</th><th class='num'>Сумма</th></tr></thead><tbody>{line_rows(sale)}</tbody></table>
  <div class="total"><span>Итого{'' if not sale.get('remise_pct') else f", скидка {sale['remise_pct']} %"}</span><span>{money(sale['montant_ttc'])}</span></div>
  {returns_block(retours)}
  <div class="foot">Статус: {'проведена' if sale['statut'] == 'validee' else 'отменена'} · канал {escape(str(sale.get('canal', '—')))}<br>
  Документ сформирован аналитическим прототипом Everys WinPharma и не является фискальным чеком.</div>
</div>
</body></html>"""


def receipt_html(sale_id: int) -> str:
    return page(logic.sale_detail(sale_id), returns.returns_of(sale_id))
