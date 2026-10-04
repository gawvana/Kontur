# Контур

Проект прошёл аудит существующей реализации. **Это пока неполный продукт, не готовый к production.** Проверенные результаты, исправления, отсутствующие функции и ограничения: [docs/AUDIT.md](docs/AUDIT.md). Исторические отчёты генератора не подтверждают готовность.

React/TypeScript/Vite: `apps/mini-app`, `apps/admin`. FastAPI/SQLAlchemy/Alembic: `services/api`. Aiogram/Redis FSM: `services/bot`. Celery: `services/worker`.

Реализованы проверка Telegram initData, ограниченные серверные сессии с отзывом, приватный поиск связанных контактов, базовые личные каталоги/чтение заметок и PENDING-обращения с идемпотентностью. Нет полного процесса репутации, доказательств, модерации, ответов/апелляций, совместной работы, импорта/экспорта и уведомлений. Бот честно сообщает о недоступных действиях; worker завершает отсутствующие интеграции ошибкой. Панель сотрудников закрыта до реализации второго фактора.

## Локальный Compose

1. Скопируйте `.env.example` в `.env`. Заполните BOT_TOKEN, JWT_SECRET (случайное значение не короче 32 символов), POSTGRES_PASSWORD, MINIO_ACCESS_KEY и MINIO_SECRET_KEY. Значений по умолчанию для секретов нет. Пароль PostgreSQL для URL должен использовать безопасные символы либо корректное URL-кодирование.
2. `docker compose up -d --build`
3. `docker compose exec api alembic upgrade head`
4. API: `http://127.0.0.1:8000`, Mini App: `http://127.0.0.1:5173`, панель: `http://127.0.0.1:5174`. `/health` — доступность процесса, `/ready` — доступность БД и таблицы сессий. До миграций ready вернёт 503.

Compose и nginx-конфигурация подготовлены, но не проверены запуском: в среде аудита нет Docker. Реальному Telegram требуется HTTPS и настройка Mini App в BotFather; loopback-ссылки служат для локальных проверок. Public deployment, TLS и webhook пока отсутствуют. Не выставляйте этот Compose напрямую в интернет.

Команды создания первого owner нет. README генератора ссылался на отсутствующий `scripts/bootstrap_owner.py`. До реализации одноразового bootstrap и второго фактора административный доступ закрыт; изменение роли вручную не открывает панель.

## Запуск без Docker

Используйте отдельные Python 3.12 окружения сервисов. В каждом: `python -m pip install -r requirements.lock`. Для тестов API дополнительно `python -m pip install -r requirements-dev.txt`.

Перед API/миграциями явно задайте переменные окружения DATABASE_URL, BOT_TOKEN, JWT_SECRET; локальный Python не загружает корневой `.env` автоматически. Из `services/api`: `python -m alembic upgrade head`, затем `python -m uvicorn main:app --host 127.0.0.1 --port 8000`.

Из каждой frontend-папки: `npm ci`, `npm run dev -- --host 127.0.0.1`. Vite проксирует `/api` к :8000; для панели используйте `--port 5174`. Обычный браузер показывает отказ в Telegram-входе. Продукт не имеет dev-auth bypass.

Бот из `services/bot`: задайте BOT_TOKEN, REDIS_URL, BACKEND_URL=`http://127.0.0.1:8000/api/v1`, затем `python main.py`. Основные действия ещё не подключены к API. Worker из `services` (родитель папки worker): `python -m celery -A worker.celery_app worker --loglevel=info`, REDIS_URL должен вести к доступному Redis. Требуется отдельная проверка живой инфраструктуры.

## Проверки

API, из `services/api`: `python -m pytest tests -q -p no:cacheprovider`. Тестовые переменные из tests/conftest.py существуют только в процессе pytest. SQLite-регрессии не заменяют PostgreSQL-интеграционные проверки.

Бот, из `services/bot`: `python -m pytest tests -q -p no:cacheprovider` (pytest устанавливается отдельно). Frontend, из каждой apps-папки: `npm run lint`, `npx tsc -b`, `npm run build`. Production Docker-образы используют runtime lock-файлы; frontend — package-lock.json.

Миграция audit_catalog_requests останавливается при старых дубликатах членства контакта. До повторного запуска сделайте backup и согласованно объедините приватные заметки; автоматического удаления данных нет. Миграция сессий не принимает прежние JWT без серверной сессии: потребуется повторный вход.
