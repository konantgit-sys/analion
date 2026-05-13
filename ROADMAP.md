# Roadmap

## ✅ Done

### Phase 0 — Core Engine
- [x] FastAPI сервер (8101) с автостартом
- [x] 69 методологий анализа (txt + JSON)
- [x] Template Backend (бесплатно, без AI)
- [x] Swagger UI (/docs)
- [x] Работающий поддомен analysis-prompts.v2.site

### Phase 1 — 5 Core Features
- [x] F1: Матчер проблем — difflib, топ-5 методов
- [x] F2: Примеры анализа — 10 готовых разборов
- [x] F3: Граф связей — 340+ соединений
- [x] F4: Сравнение методов — 2-3 side-by-side
- [x] F5: PDF-отчёт — reportlab на лету

### Phase 2 — AI Enhanced
- [x] F8: История анализов (SQLite)
- [x] F9: Deep Analyze — матчер + 3 метода + синтез
- [x] F10: Резюме анализа
- [x] F11: Чек-лист по методологии
- [x] F12: Оценка проблемы (0-10)
- [x] F13: Брейншторм гипотез
- [x] F14: Анализ текста/URL
- [x] Mistral AI интеграция (primary)

### Phase 3 — Multi-Provider
- [x] 9 AI-провайдеров (Mistral, OpenAI, DeepSeek, Novita, Groq, Together, SambaNova, OpenRouter, Custom)
- [x] BYO key — свой API-ключ через запрос
- [x] openai_compat — универсальный адаптер
- [x] Тестирование ключей (POST /backends/test)

### Phase 4 — Billing
- [x] 4 тарифа (Free / Starter / Pro / Unlimited)
- [x] Лимиты и квоты в SQLite
- [x] Трекинг использования
- [x] API статуса /my/status, /my/usage
- [x] Подписки (апгрейд, сроки)
- [x] Инвойсы (Telegram Stars заглушка)

## 🔄 In Progress

- **GitHub Pages витрина** — обновить карточки для новых фич (Phase 2-4)
- **Документация** — README, CHANGELOG, ARCHITECTURE, API docs

## 📋 Planned

### Phase 5 — Telegram Bot
- [ ] Интеграция с Telegram: анализировать через бота
- [ ] Оплата через Telegram Stars (реальная)
- [ ] Подписка прямо в боте
- [ ] Команды: /analyze, /history, /plan

### Phase 6 — Production
- [ ] ЮKassa / Stripe интеграция для РФ/мира
- [ ] Rate limiting (redis or in-memory)
- [ ] Логирование и мониторинг (healthcheck + алерты)
- [ ] Кэширование частых запросов
- [ ] Асинхронный queue для длинных анализов

### Phase 7 — Enterprise
- [ ] White label API
- [ ] Интеграция с Jira / Notion / Slack
- [ ] Кастомные методологии под бизнес
- [ ] Team management (аккаунты на несколько пользователей)
- [ ] Audit log для корпоративных клиентов

### Backlog
- [ ] Английская версия (все методологии + промпты)
- [ ] i18n — поддержка других языков
- [ ] WebSocket для live-анализов
- [ ] Мобильное PWA приложение
- [ ] Экспорт в Notion / Obsidian / Markdown
