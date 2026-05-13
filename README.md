# Analion

**69 методологий анализа. Полноценный REST API.  
5-фазная архитектура для всех бизнес-задач.**

> Не очередной AI-помощник.  
> 69 структурированных промптов × 8–12 КБ каждый = полный спектр аналитического мышления.  
> От TRIZ до QFD. От ПАРЕТО до Theory of Change.  
> Работает на **вашем** AI-провайдере или на нашем (Mistral).

**Сайт:** https://analysis-prompts.v2.site  
**Swagger:** https://analysis-prompts.v2.site/docs  
**GitHub Pages:** https://konantgit-sys.github.io/analion/

---

## Суть

Analion — это **интеллектуальный движок анализа**, упакованный в REST API.

Вы отправляете проблему. Analion:
1. Сам подбирает релевантные методологии (или вы выбираете)
2. Запускает анализ через AI (Mistral / OpenAI / DeepSeek / свой ключ)
3. Возвращает структурированный результат: вывод, пошаговый разбор, рекомендации

`POST /api/v1/analyze` → JSON.

---

## Ключевые возможности

### 69 методологий
18 направлений: стратегия, инновации, качество, риск, управление, процессы, IT, маркетинг, HR, финансы...

### Матчер проблем
Кидаешь описание → API подбирает 5 подходящих методов с обоснованием.

### Граф связей
69 методов → 340+ связей. Понимаешь как методы дополняют друг друга.

### Глубокий анализ
Матчер → 3 метода → синтез. Один запрос — комплексный разбор.

### Сравнение методов
Выбери 2-3 метода для одной проблемы → сравни результаты.

### PDF-отчёт
Любой анализ можно скачать в PDF.

### Мульти-провайдер (Фаза 2)
Используй любую AI-модель: Mistral (по умолчанию), OpenAI, DeepSeek, Groq, SambaNova, Together, OpenRouter — или свой кастомный endpoint.

### Свои ключи
Подключи свой API-ключ любого OpenAI-совместимого провайдера. Analion не тратит твои токены на лишнее.

### Система тарифов (Фаза 3)
Бесплатный тариф — 3 анализа/день. Платные — от 499₽.

---

## Быстрый старт

```bash
# Все методологии
curl https://analysis-prompts.v2.site/api/v1/frameworks

# Анализ (template — бесплатно, без ключей)
curl -X POST https://analysis-prompts.v2.site/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"problem":"Стартап теряет клиентов","backend":"template"}'

# Анализ через Mistral (работает из коробки)
curl -X POST https://analysis-prompts.v2.site/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"problem":"Стартап теряет клиентов","backend":"mistral"}'

# Анализ через OpenAI (своим ключом)
curl -X POST https://analysis-prompts.v2.site/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "problem":"High employee turnover in IT team",
    "frameworks":["24_SWOT","31_PORTER_FIVE"],
    "backend":"openai",
    "api_key":"sk-...",
    "model":"gpt-4o-mini"
  }'

# Матчер — подбор методологии по проблеме
curl -X POST https://analysis-prompts.v2.site/api/v1/matcher \
  -H "Content-Type: application/json" \
  -d '{"problem":"Сервер падает под нагрузкой","top_n":3}'
```

---

## API

### Основные эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/health` | Проверка сервера |
| GET | `/api/v1/frameworks` | Список всех 69 методологий |
| GET | `/api/v1/frameworks/{id}` | Полное описание методологии |
| POST | `/api/v1/analyze` | Анализ проблемы через AI |
| POST | `/api/v1/matcher` | Подбор методов по описанию проблемы |
| GET | `/api/v1/examples` | 10 готовых примеров анализа |
| GET | `/api/v1/graph` | Граф связей между методологиями |
| POST | `/api/v1/compare` | Сравнение методов |
| POST | `/api/v1/report` | PDF-отчёт по анализу |

### Фаза 2 (AI Enhanced)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/deep-analyze` | Матчер + 3 метода + синтез |
| POST | `/api/v1/summarize` | Резюме анализа |
| GET | `/api/v1/history` | История анализов |
| GET | `/api/v1/frameworks/{id}/checklist` | Чек-лист по методологии |
| POST | `/api/v1/problem-score` | Оценка проблемы (0-10) |
| POST | `/api/v1/brainstorm` | Генерация гипотез |
| POST | `/api/v1/analyze-file` | Анализ текста/URL |

### Провайдеры и биллинг (Фаза 3)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/providers` | Список поддерживаемых AI-провайдеров |
| POST | `/api/v1/backends/test` | Проверка API-ключа |
| POST | `/api/v1/backends` | Подключить свой ключ |
| GET | `/api/v1/backends` | Мои ключи |
| GET | `/api/v1/plans` | Тарифы и лимиты |
| GET | `/api/v1/my/status` | Моя подписка + статистика |
| GET | `/api/v1/my/usage` | Статистика использования |
| GET | `/api/v1/my/invoices` | История платежей |

---

## Провайдеры AI

| Провайдер | ID | Модель по умолчанию | Требует ключ |
|-----------|-----|--------------------|--------------|
| Mistral AI | `mistral` | `mistral-small-latest` | Нет (наш) |
| OpenAI | `openai` | `gpt-4o-mini` | Да |
| DeepSeek | `deepseek` | `deepseek-chat` | Да |
| Novita AI | `novita` | `deepseek/deepseek-v4-flash` | Да |
| Groq | `groq` | `llama-3.3-70b-versatile` | Да |
| Together AI | `together` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | Да |
| SambaNova | `sambanova` | `Meta-Llama-3.3-70B-Instruct` | Да |
| OpenRouter | `openrouter` | `openai/gpt-4o-mini` | Да |
| Custom | `custom` | любая | Да (+ base_url) |

---

## Архитектура

```
analysis-prompts.v2.site (full:8101)
│
├── engine/               # FastAPI сервер
│   ├── main.py           # Все эндпоинты + роутинг
│   ├── matcher.py        # Матчер проблем (difflib + семантика)
│   └── billing/          # Монетизация
│       ├── plans.py      # Тарифы (Free/Starter/Pro/Unlimited)
│       ├── limits.py     # Лимиты и квоты (БД)
│       ├── payments.py   # Платёжные интеграции
│       └── subscriptions.py  # Управление подписками
│
├── runner/               # AI-бэкенды
│   ├── adapter.py        # Выбор бэкенда по env
│   ├── runner.py         # Запуск анализа
│   └── backends/         # Провайдеры
│       ├── template.py   # Шаблонный (без AI)
│       ├── mistral.py    # Mistral API
│       ├── openai_compat.py  # Универсальный OpenAI-совместимый
│       └── sambanova.py  # SambaNova
│
├── selector/             # Индексация методологий
│   ├── selector.py       # Выбор методов по ключевым словам
│   └── keywords_index.json
│
├── builder/              # Генерация промптов
│   └── builder.py
│
└── data/                 # Статические данные
    ├── frameworks_meta.json  # 69 методологий
    ├── frameworks_metrics.json  # Метрики совместимости
    ├── graph.json         # Граф связей
    └── examples.json      # 10 примеров анализа
```

---

## Тарифы

| Тариф | Цена/мес | AI-анализов/день | Deep Analyze | PDF | Свой ключ | История |
|-------|----------|-----------------|-------------|-----|-----------|---------|
| Free | 0₽ | 3 | — | — | — | 7 дней |
| Starter | 499₽ | 20 | ✅ | ✅ | — | 30 дней |
| Pro | 1 490₽ | 100 | ✅ | ✅ | ✅ | 365 дней |
| Unlimited | 4 990₽ | ∞ | ✅ | ✅ | ✅ | 10 лет |

---

## Статус разработки

| Фаза | Статус | Что содержит |
|------|--------|-------------|
| Фаза 0 — Core | ✅ | FastAPI, 69 методологий, Template Backend, Swagger |
| Фаза 1 — 5 фич | ✅ | Матчер, Примеры, Граф, Сравнение, PDF |
| Фаза 2 — AI Enhanced | ✅ | 7 эндпоинтов, Mistral, Deep Analyze, Брейншторм |
| Фаза 3 — Мульти-провайдер | ✅ | 9 провайдеров, свои ключи, openai_compat |
| Фаза 4 — Биллинг | ✅ | Тарифы, лимиты, подписки, Telegram Stars |
| Фаза 5 — Telegram Bot | 📋 | Опционально |

---

## Лицензия

MIT. Делай что хочешь.
