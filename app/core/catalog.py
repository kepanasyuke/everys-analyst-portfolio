"""Каталог проектов портфолио: единый источник для UI, README и API /api/catalog."""

from __future__ import annotations

PROJECTS = [
    {
        "code": "P01",
        "slug": "requirements",
        "title_ru": "Требования → критерии приёмки",
        "title_fr": "Exigences → critères d'acceptation",
        "problem": "Входящая user story без критериев приёмки: разработка ждёт уточнений, релиз сдвигается.",
        "ai": "RAG по корпусу спецификаций (BM25) + извлечение ограничений + критическая валидация каждого критерия.",
        "stack": ["RAG", "BM25", "Acceptance Criteria", "GWT"],
        "endpoint": "POST /api/p01/generate",
        "business": "Сокращает цикл уточнений между аналитиком и разработкой, снижает число возвратов с ревью.",
        "kpi": "Время подготовки AC на фичу",
    },
    {
        "code": "P02",
        "slug": "sql-lab",
        "title_ru": "SQL Lab: вопрос на бизнес-языке → SQL",
        "title_fr": "SQL Lab : question métier → requête SQL",
        "problem": "Аналитику нужны цифры по продажам, но писать JOIN и GROUP BY каждый раз долго.",
        "ai": "Разбор интента, генерация шаблонного SELECT, защита SELECT-only и обязательный LIMIT.",
        "stack": ["SQL", "JOIN", "GROUP BY", "SQLite read-only"],
        "endpoint": "POST /api/p02/query",
        "business": "Самодостаточное исследование данных без тикета в BI-команду.",
        "kpi": "Доля ad-hoc вопросов, закрытых аналитиком самостоятельно",
    },
    {
        "code": "P03",
        "slug": "conflicts",
        "title_ru": "Радар противоречий в документации",
        "title_fr": "Radar de contradictions documentaires",
        "problem": "Спецификации живут в 9 файлах: порог скидки 30 % и 20 %, TLS 1.2 и 1.3, 24 и 48 часов.",
        "ai": "Нормализация утверждений, сравнение числовых и модальных значений между документами.",
        "stack": ["NLP-эвристики", "Diff утверждений", "Traceability"],
        "endpoint": "POST /api/p03/scan",
        "business": "Противоречия находятся до разработки, а не на приёмке и не в проде.",
        "kpi": "Число дефектов, вызванных неоднозначным требованием",
    },
    {
        "code": "P04",
        "slug": "edge-cases",
        "title_ru": "Генератор граничных сценариев",
        "title_fr": "Générateur de cas limites",
        "problem": "На приёмке проверяют happy path, а последний товар на двух кассах ломает склад.",
        "ai": "Извлечение диапазонов и правил из спеки, порождение границ, прав доступа, гонок и форматов.",
        "stack": ["Тест-анализ", "Граничные значения", "Риск-приоритизация"],
        "endpoint": "POST /api/p04/generate",
        "business": "Граничные кейсы попадают в тест-план до релиза, а не в инциденты после.",
        "kpi": "Покрытие граничных сценариев на приёмке",
    },
    {
        "code": "P05",
        "slug": "ab-lab",
        "title_ru": "A/B Lab: проверка гипотез",
        "title_fr": "A/B Lab : validation d'hypothèses",
        "problem": "Гипотеза «скидка 20 % поднимет чек» принимается на глаз по двум неделям данных.",
        "ai": "Двухпропорциональный z-тест, доверительный интервал, расчёт размера выборки без scipy.",
        "stack": ["Статистика", "z-тест", "Power analysis"],
        "endpoint": "POST /api/p05/test",
        "business": "Решение о раскатке фичи на 7000 аптек принимается по числу, а не по интуиции.",
        "kpi": "Доля продуктовых гипотез, проверенных статистически",
    },
    {
        "code": "P06",
        "slug": "integration-watch",
        "title_ru": "Integration Watch: API, TLS, SOAP",
        "title_fr": "Integration Watch : API, TLS, SOAP",
        "problem": "Теледетрансмиссия падает из-за истёкшего сертификата или таймаута в 30 секунд.",
        "ai": "Проба endpoint-ов, срок жизни сертификата, версия TLS, валидация SOAP-конверта по контракту.",
        "stack": ["HTTP", "TLS", "SOAP 1.2", "SLA"],
        "endpoint": "POST /api/p06/probe",
        "business": "Интеграционные риски видны заранее, а не в момент закрытия смены.",
        "kpi": "Доступность канала теледетрансмиссии",
    },
    {
        "code": "P07",
        "slug": "release-gate",
        "title_ru": "Release Gate: контроль стабильности выпуска",
        "title_fr": "Release Gate : stabilité de version",
        "problem": "Релиз 2026.1 уходит в прод с непроверенной миграцией и без плана отката.",
        "ai": "Взвешенная оценка готовности, поиск блокеров, генерация протокола приёмки на RU/FR.",
        "stack": ["Release management", "Risk scoring", "Checklist"],
        "endpoint": "POST /api/p07/assess",
        "business": "Единый критерий «идём в прод или нет» вместо спора на планёрке.",
        "kpi": "Число откатов после релиза",
    },
    {
        "code": "P08",
        "slug": "glossary",
        "title_ru": "Глоссарий аптечного домена FR↔RU",
        "title_fr": "Glossaire métier officine FR↔RU",
        "problem": "Аналитик в Москве читает французскую спеку: ordonnance, tiers payant, rupture.",
        "ai": "Двуязычный поиск по глоссарию, примеры употребления, поиск пробелов в терминологии корпуса.",
        "stack": ["Домен", "FR/RU", "Term drift"],
        "endpoint": "POST /api/p08/lookup",
        "business": "Снимает языковой барьер между московской разработкой и французскими продуктологами.",
        "kpi": "Время ввода в домен нового аналитика",
    },
]


def by_slug(slug: str) -> dict:
    return next((p for p in PROJECTS if p["slug"] == slug), {})


def codes() -> list[str]:
    return [p["code"] for p in PROJECTS]
