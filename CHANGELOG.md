# Changelog

## [3.0.0] — 2026-05-13 — Multi-Provider + Billing

### Added
- **9 AI-провайдеров:** Mistral, OpenAI, DeepSeek, Novita, Groq, Together, SambaNova, OpenRouter, Custom
- **openai_compat.py** — универсальный бэкенд для любого OpenAI-совместимого API
- **Система тарифов:** Free (3/день), Starter (499₽, 20/день), Pro (1 490₽, 100/день), Unlimited (4 990₽, ∞)
- **Лимиты и квоты:** трекинг использования в SQLite, блокировка при превышении
- **Подписки:** `subscriptions` таблица, апгрейд через API
- **Платежи:** Telegram Stars интеграция (заглушка), инвойсы
- **Эндпоинты биллинга:** `/api/v1/plans`, `/my/status`, `/my/usage`, `/my/invoices`, `/my/upgrade`
- **Проверка ключей:** `POST /api/v1/backends/test` — тест любого провайдера перед сохранением

### Changed
- AnalyzeRequest теперь принимает `backend`, `api_key`, `base_url`, `model`, `session_id`
- Все AI-анализы логируются в usage_log для биллинга
- Параметр `backend` в ответе анализа показывает какой провайдер использовался

---

## [2.0.0] — 2026-05-03 — AI Enhanced (Фаза 2)

### Added
- **Mistral API** — реальный AI-анализ (3344 токена, 30 шагов, 11 рекомендаций)
- **7 новых эндпоинтов Фазы 2:**
  - `POST /api/v1/deep-analyze` — матчер + 3 метода + синтез
  - `POST /api/v1/summarize` — резюме анализа
  - `GET /api/v1/history` — история анализов (SQLite)
  - `GET /api/v1/frameworks/{id}/checklist` — чек-лист по методологии
  - `POST /api/v1/problem-score` — оценка проблемы (0-10)
  - `POST /api/v1/brainstorm` — генерация гипотез
  - `POST /api/v1/analyze-file` — анализ текста/URL
- **Runner/adapter** — выбор бэкенда через переменную окружения `ANALION_BACKEND`
- **Ротация ключей** — 2 ключа Mistral с автофоллбэком
- **.env** — хранение API-ключей через load_dotenv

### Changed
- Backend по умолчанию: `template` → `mistral`
- Все Фаза-2 эндпоинты тестированы через curl

---

## [1.0.0] — 2026-05-02 — Фаза 1

### Added
- **FastAPI ядро** (engine/main.py, порт 8101)
- **69 методологий** в data/frameworks_meta.json
- **Template Backend** — анализ без AI (шаблонный)
- **Swagger UI** — `/docs`
- **JSON-навигация** по корню `/`
- **F1 — Матчер** `POST /api/v1/matcher` — difflib.SequenceMatcher
- **F2 — Примеры** `GET /api/v1/examples` — 10 разборов
- **F3 — Граф** `GET /api/v1/graph` — 340+ связей
- **F4 — Сравнение** `POST /api/v1/compare` — 2-3 метода
- **F5 — PDF** `POST /api/v1/report` — reportlab на лету
- **port.txt** — full:8101, автостарт через start.sh

---

## [0.1.0] — 2026-04-28 — MVP

### Added
- Первый прототип Analion
- Каталог 70+ методологий (txt-файлы)
- Базовый selector по ключевым словам
- builder промптов
