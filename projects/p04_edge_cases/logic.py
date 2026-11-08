"""P04 — генератор граничных сценариев и побочных эффектов из текста спецификации."""

from __future__ import annotations

import re

from app.ai.text import numbers, sentences, shorten

NUM_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(%|°C|heures|jours|mois|minutes|€|mg|ml)", re.I)
SMALL_UNITS = ("%", "°C")

PRESETS = [
    {"keys": ("stock", "остат", "rupture", "дефицит"), "category": "конкурентность", "title": "Последняя единица товара продаётся с двух касс одновременно", "precondition": "Остаток равен 1, два поста ввода", "steps": "Одновременно подтвердить продажу на двух кассах", "expected": "Одна транзакция успешна, вторая отклонена с сообщением «stock insuffisant», отрицательного остатка нет", "priority": "P1"},
    {"keys": ("stock", "остат", "seuil", "порог"), "category": "граница", "title": "Остаток ровно равен порогу пополнения", "precondition": "Доступный остаток = порог", "steps": "Открыть карточку товара и дождаться пересчёта алертов", "expected": "Алерт пополнения формируется, так как условие «меньше или равно»", "priority": "P2"},
    {"keys": ("remise", "скидк", "discount"), "category": "граница", "title": "Скидка 100 % и отрицательная скидка", "precondition": "Позиция с ценой 10,00 €", "steps": "Ввести скидку 100 %, затем −5 %", "expected": "100 % допускается только с подтверждением владельца, отрицательное значение отклоняется валидацией", "priority": "P1"},
    {"keys": ("remise", "скидк", "tva", "ндс"), "category": "округление", "title": "Округление НДС на сумме 0,03 €", "precondition": "Минимальная цена позиции", "steps": "Продать 2 позиции по 0,01 € со скидкой 3 %", "expected": "Сумма НДС округляется до копейки один раз на документ, итог совпадает с бухгалтерским расчётом", "priority": "P2"},
    {"keys": ("caisse", "чек", "encaiss", "оплат"), "category": "инвариант", "title": "Сумма оплат не равна сумме к оплате", "precondition": "Продажа на 25,00 €", "steps": "Ввести оплату 24,99 € и закрыть чек", "expected": "Чек не закрывается, показывается остаток 0,01 €, данные не теряются", "priority": "P1"},
    {"keys": ("annul", "отмен", "avoir", "сторно"), "category": "состояние", "title": "Отмена уже переданной продажи", "precondition": "Продажа в статусе «передана»", "steps": "Нажать «отменить» на следующий день", "expected": "Отмена недоступна, предлагается сторно; исходная запись остаётся неизменной в журнале", "priority": "P1"},
    {"keys": ("ordonnance", "рецепт"), "category": "время", "title": "Рецепт на границе срока действия", "precondition": "Три рецепта: 11 мес 29 дн, ровно 12 мес, 12 мес 1 дн", "steps": "Провести выдачу по каждому", "expected": "Первые два принимаются, третий блокируется с указанием причины", "priority": "P1"},
    {"keys": ("ordonnance", "рецепт", "cip"), "category": "данные", "title": "Отсутствующий или некорректный код CIP13", "precondition": "Рецепт с пустым CIP и с CIP из 12 цифр", "steps": "Сохранить рецепт", "expected": "Валидация отклоняет обе строки, поле подсвечено, частичное сохранение невозможно", "priority": "P2"},
    {"keys": ("stupéfiant", "наркот", "двойн", "контрол"), "category": "права", "title": "Второй контроль выполняет тот же пользователь", "precondition": "Один фармацевт в смене", "steps": "Подтвердить контроль своей же учётной записью", "expected": "Контроль не засчитывается: требуется другая учётная запись, действие в журнале аудита", "priority": "P1"},
    {"keys": ("tiers", "возмещ", "créance", "требован"), "category": "интеграция", "title": "Повторная передача отклонённого требования", "precondition": "Требование отклонено, срок 47 ч 59 мин", "steps": "Передать повторно, затем повторить через 48 ч 01 мин", "expected": "Первый повтор проходит, второй переводит требование в «неоплачено» с уведомлением", "priority": "P2"},
    {"keys": ("flux", "soap", "idflux"), "category": "идемпотентность", "title": "Повторный вызов с тем же idFlux", "precondition": "Флюс уже принят", "steps": "Отправить тот же idFlux с тем же содержимым и с изменённым содержимым", "expected": "Первый повтор возвращает исходный код без дубля, второй отклоняется с кодом 4092", "priority": "P1"},
    {"keys": ("tls", "сертификат", "интеграц"), "category": "безопасность", "title": "Истёкший сертификат и TLS ниже минимума", "precondition": "Тестовый endpoint с сертификатом −1 день и TLS 1.1", "steps": "Выполнить теледетрансмиссию", "expected": "Соединение блокируется до отправки данных, в журнале причина «certificat expiré / protocole refusé»", "priority": "P1"},
    {"keys": ("temp", "холод", "°c", "conserv"), "category": "время", "title": "Отклонение температуры на 2,1 °C в течение 31 минуты", "precondition": "Датчик refrigerated enclosure", "steps": "Смоделировать скачок и восстановление", "expected": "Партия уходит в карантин, формируется инцидент, продажа заблокирована", "priority": "P1"},
    {"keys": ("rembours", "возмещ", "taux"), "category": "данные", "title": "Ставка возмещения изменена после продажи", "precondition": "Продажа с taux 65 %", "steps": "Изменить ставку справочника на 30 % и переоткрыть продажу", "expected": "Историческая ставка не меняется, пересчёт не выполняется", "priority": "P2"},
    {"keys": ("connexion", "сеть", "offline", "офлайн", "panne"), "category": "отказоустойчивость", "title": "Разрыв связи в момент подтверждения продажи", "precondition": "Сервер недоступен 60 секунд", "steps": "Подтвердить продажу и восстановить связь", "expected": "Продажа не дублируется, повтор отправляется один раз, статус меняется на «передана»", "priority": "P1"},
    {"keys": ("nom", "текст", "коммент", "поле"), "category": "формат", "title": "Юникод, эмодзи и 255 символов в текстовом поле", "precondition": "Поле ввода с ограничением 255", "steps": "Ввести латиницу с диакритикой, кириллицу, эмодзи и строку из 256 символов", "expected": "Символы сохраняются без искажений, 256-й символ блокируется счётчиком", "priority": "P3"},
]

CATEGORY_ORDER = ["граница", "права", "конкурентность", "инвариант", "состояние", "время", "данные", "интеграция", "идемпотентность", "безопасность", "отказоустойчивость", "округление", "формат"]


def fr(num: float) -> str:
    return f"{num:g}".replace(".", ",")


def numbers_in(spec: str) -> list[tuple[float, str, str]]:
    return [(float(m[1].replace(",", ".")), m[2], context(spec, m.start())) for m in NUM_RE.finditer(spec)][:6]


def context(spec: str, position: int) -> str:
    window = spec[max(0, position - 60): position + 40]
    return shorten(window, 80)


def step(value: float, unit: str) -> float:
    return 0.1 if unit in SMALL_UNITS else 1.0


def expectation(value: float, limit: float, unit: str) -> str:
    return f"{fr(value)} {unit} принимается: значение на границе допустимого" if value == limit else f"{fr(value)} {unit} отклоняется с явным сообщением, данные не сохраняются"


def bound(index: int, delta: int, num: float, unit: str, ctx: str) -> dict:
    value = round(num + delta * step(num, unit), 2)
    return {"id": f"B{index + 1}-{delta + 2}", "category": "граница", "title": f"{fr(value)} {unit} · {ctx}", "precondition": "Подготовлены данные вокруг порога из спецификации", "steps": f"Ввести {fr(value)} {unit}, подтвердить операцию, проверить журнал", "expected": expectation(value, num, unit), "priority": "P1" if delta > 0 else "P2", "risk": f"Порог {fr(num)} {unit} без проверки границы ±1"}


def boundaries(spec: str) -> list[dict]:
    return [bound(i, delta, num, unit, ctx) for i, (num, unit, ctx) in enumerate(numbers_in(spec)) for delta in (-1, 0, 1)]


def preset_case(preset: dict) -> dict:
    return {"id": "R-" + preset["category"][:3].upper(), "category": preset["category"], "title": preset["title"], "precondition": preset["precondition"], "steps": preset["steps"], "expected": preset["expected"], "priority": preset["priority"], "risk": "Сценарий не покрыт типовым тест-планом"}


def presets(spec: str) -> list[dict]:
    low = spec.lower()
    return [preset_case(p) for p in PRESETS if any(k in low for k in p["keys"])]


def dedupe(items: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    return [seen.setdefault(i["title"], i) for i in items if i["title"] not in seen]


def order_key(case: dict) -> tuple[int, str]:
    return (CATEGORY_ORDER.index(case["category"]) if case["category"] in CATEGORY_ORDER else 99, case["id"])


def summary(cases: list[dict]) -> dict:
    return {"total": len(cases), "p1": sum(1 for c in cases if c["priority"] == "P1"), "p2": sum(1 for c in cases if c["priority"] == "P2"), "p3": sum(1 for c in cases if c["priority"] == "P3"), "categories": sorted({c["category"] for c in cases})}


def generate(spec: str) -> dict:
    ordered = sorted(dedupe([*presets(spec), *boundaries(spec)]), key=order_key)
    return {"spec": shorten(spec, 400), "cases": ordered, "summary": summary(ordered), "checklist": checklist(ordered), "numbers": [{"value": fr(n), "unit": u, "context": c} for n, u, c in numbers_in(spec)]}


def checklist(cases: list[dict]) -> list[str]:
    return [f"{c['priority']} · {c['category']} · {c['title']}" for c in cases if c["priority"] == "P1"][:6]


def presets_all() -> list[dict]:
    return [{"category": p["category"], "title": p["title"], "keys": p["keys"]} for p in PRESETS]


def sample_specs() -> list[dict]:
    return [
        {"label": "Скидка и касса", "text": "La remise maximale autorisée est de 30 % du prix public. Une vente de 100,00 € peut être réglée partiellement. Annulation possible le jour même."},
        {"label": "Склад и дефектура", "text": "Le stock disponible est égal au stock physique moins le stock réservé. Une rupture est déclarée quand le stock disponible est nul. Seuil de réapprovisionnement: 20 unités, réassort chaque jour à 18 h 00."},
        {"label": "Холодовая цепь", "text": "Les médicaments thermosensibles sont conservés entre +2 °C et +8 °C. La sonde relève la température toutes les 15 minutes. Un écart de plus de 2 °C pendant 30 minutes déclenche une alerte."},
        {"label": "Теледетрансмиссия", "text": "Le service expose TransmettreFlux en SOAP 1.2 sous TLS 1.2 minimum. Délai d'attente client: 30 secondes, 3 tentatives. Une créance rejetée doit être retransmise sous 48 heures."},
    ]
