> Историческое описание генератора. Неподтверждённые реализации и команды не означают готовность. Проверенный запуск: [README.md](../README.md); результаты и пробелы: [AUDIT.md](AUDIT.md).

# Архитектура проекта «Контур»

## Стек технологий
- **Backend**: Python 3.12, FastAPI, SQLAlchemy (PostgreSQL), Alembic, Pydantic.
- **Frontend (Mini App & Admin)**: React, TypeScript, Vite, React Query, React Router.
- **Бот**: aiogram 3.x.
- **База данных**: PostgreSQL 16+.
- **Хранение состояния и кэш**: Redis (FSM бота, rate limits, queues).
- **Файловое хранилище**: S3-совместимое хранилище (MinIO для локальной разработки).
- **Фоновые задачи**: Celery или RQ / FastAPI Background Tasks + Redis (выбрано RQ/Celery для сложных задач загрузки/экспорта).
- **Деплой и инфраструктура**: Docker, Docker Compose.

## Структура монорепозитория
- `apps/mini-app`: React SPA для Mini App.
- `apps/admin`: React SPA для админ-панели модераторов.
- `services/api`: FastAPI REST API для фронтенда и бота.
- `services/bot`: aiogram бот, работающий через Webhook или Polling, обращающийся к БД или API напрямую.
- `services/worker`: Обработчик фоновых задач (модерация файлов, экспорт, отправка уведомлений).
- `packages/contracts`: Общие DTO и OpenAPI схемы (для генерации типов фронтенда).
- `infra`: Конфиги Docker Compose, Nginx, и прочее.

## Паттерны
- Разделение на layers: Transport (Routers), Services (Domain Logic), Persistence (Repositories).
- Идемпотентность для критических мутаций (создание заявки, модерация) через idempotency key.
- Soft Delete для важных сущностей.
- Транзакционный Outbox для надежной отправки уведомлений.
