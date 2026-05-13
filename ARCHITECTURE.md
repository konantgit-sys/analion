# Архитектура Analion

## Общая схема

```
┌─────────────────────────────────────────────────────┐
│                   Клиент (curl / bot / app)          │
└──────────────────┬──────────────────────────────────┘
                   │ HTTPS
                   ▼
┌─────────────────────────────────────────────────────┐
│              analysis-prompts.v2.site                │
│                (Ingress → site-router)               │
└──────────────────┬──────────────────────────────────┘
                   │ full:8101 (прокси ALL)
                   ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI (engine/main.py)                │
│                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │ /analyze │ │ /matcher │ │ /billing/*           │ │
│  │ /compare │ │ /graph   │ │ /my/status           │ │
│  │ /report  │ │ /history │ │ /my/usage            │ │
│  └─────┬────┘ └────┬─────┘ └──────────────────────┘ │
│        │           │                                 │
└────────┼───────────┼─────────────────────────────────┘
         │           │
         ▼           ▼
┌─────────────────────────────────────────────────────┐
│              Runner (выбор бэкенда)                  │
│                                                      │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ template   │  │ mistral      │  │ openai_compat│ │
│  │ (шаблоны)  │  │ (наш ключ)   │  │ (BYO key)   │ │
│  └────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────┘
         │           │
         ▼           ▼
┌─────────────────────────────────────────────────────┐
│  Mistral API    OpenAI API    DeepSeek API          │
│  Groq API       SambaNova     Custom endpoint       │
└─────────────────────────────────────────────────────┘
```

## Компоненты

### 1. FastAPI сервер (`engine/main.py`)
- Одна точка входа на порту 8101
- Все эндпоинты — в одном файле (~1100 строк)
- Pydantic models для валидации запросов
- SQLite через `get_db()` для истории, биллинга

### 2. Matcher (`engine/matcher.py`)
- Поиск подходящих методологий по тексту проблемы
- Алгоритм: difflib.SequenceMatcher + взвешенные метрики из `frameworks_metrics.json`
- Топ-5 с рейтингом и обоснованием

### 3. AI Runner (`runner/`)
- `adapter.py` — выбор бэкенда по `ANALION_BACKEND` env
- `backends/template.py` — шаблонный генератор (без AI, бесплатно)
- `backends/mistral.py` — вызов Mistral API
- `backends/openai_compat.py` — универсальный OpenAI-совместимый адаптер

### 4. Billing (`engine/billing/`)
- `plans.py` — 4 тарифа с параметрами
- `limits.py` — лимиты в SQLite (таблица usage_log)
- `payments.py` — платёжные интеграции (Telegram Stars)
- `subscriptions.py` — управление подписками

### 5. Данные (`data/`)
- `frameworks_meta.json` — 69 методологий с полным описанием
- `frameworks_metrics.json` — метрики совместимости
- `graph.json` — граф связей (340+ рёбер)
- `examples.json` — 10 готовых примеров анализа
- `analion.db` — SQLite (история, лимиты, юзеры)

## Поток запроса (analyze)

1. POST /api/v1/analyze → FastAPI
2. Проверка лимитов (billing/limits.py)
3. Если frameworks не указаны → matcher подбирает
4. Для каждого framework: build_prompt → run_analysis
5. Выбор бэкенда по `backend` параметру
6. Парсинг ответа → summary + steps + recommendations
7. Логирование в usage_log и analysis_history
8. JSON-ответ

## Безопасность
- API-ключи в `.env` (не в коде)
- Свои ключи пользователей — только в памяти запроса (не сохраняются в БД без явного POST /backends)
- SQLite — без инъекций (параметризованные запросы)

## Масштабирование
- Один процесс FastAPI (uvicorn) на порту 8101
- SQLite — до ~1000 запросов/день без проблем
- Для роста: SQLite → PostgreSQL, очередь через Redis
