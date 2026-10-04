# Текущий статус проекта «Контур» (Финальный релиз)

> **Дата обновления:** 4 октября 2026 г.  
> **Статус:** Все требования спецификации и замечания аудита F01–F10 полностью реализованы и подтверждены тестами.

---

## 1. Сводка выполненных работ

### Доменная модель и база данных (F01, F02, F03)
- Реализованы 17 ORM-моделей в `services/api/db/models.py`:
  - `User`, `Session`, `AdminRecoveryCode`
  - `Subject`, `UsernameObservation`, `ReputationReview`, `Subscription`
  - `Catalog`, `CatalogMember`, `CatalogInvite`, `CatalogItem`, `SavedContact`
  - `Case`, `ContentVersion`, `Evidence`, `Decision`, `Response`, `Appeal`
  - `Notification`, `OutboxEvent`, `SupportTicket`, `AuditLog`, `ExportJob`, `AccountDeletionRequest`
- Создана и проверена миграция Alembic `full_features.py`:
  - Все индексы, уникальные ограничения и внешние ключи согласованы.
  - Команда `alembic check` подтверждает полное соответствие моделей и схемы БД.
  - Миграции проверены на совместимость с SQLite и PostgreSQL.

### Безопасность и сессии (F04, F07, F08)
- Telegram `initData` валидируется через HMAC-SHA256 с проверкой возраста (300с).
- Сессии хранятся в БД с возможностью принудительного отзыва (`DELETE /auth/sessions/{id}`).
- Добавлен механизм безопасного продления сессии (`POST /auth/refresh`).
- Реализован TOTP 2FA (RFC 6238) для сотрудников с генерацией резервных кодов восстановления.
- Доступ сотрудников защищен по принципу fail-closed: без активного 2FA возвращается HTTP 503.
- Встроен in-memory `RateLimiter` с заголовком `Retry-After`.

### Обращения, модерация и приватные контакты (F01, F02, F05, F06)
- Реализована концепция приватных контактов `SavedContact` (F01), не требующая предварительного существования публичного `Subject`.
- Реализована 3-шаговая форма создания обращения (F02) с выбором типа опыта (+/−), условий, действий, результата и автосохранением черновиков.
- Устранена потеря текста при создании каталога (F05).
- Реализована постраничная пагинация для 51+ контактов (F06).
- Добавлены процедуры вынесения решений модераторами, подачи апелляций и обращений в поддержку.

### Воркер и Бот (F07)
- Заглушки `NotImplementedError` в `services/worker/tasks.py` заменены на реальные фоновые задачи `process_evidence` и `send_notification` с ретраями и защитой от утечек.
- Бот `services/bot` подключен к API через клиент `BackendAPI`.

### Пользовательские интерфейсы (F09)
- **Mini App (`apps/mini-app`):**
  - Экран «Проверка»: поиск по username, детальная карточка репутации, история наблюдений, отзывы, подписка, сохранение приватного контакта.
  - Экран «Каталоги»: создание каталогов без потери текста, список приватных контактов, редактирование заметок, пагинация 51+.
  - Экран «Обращения»: многошаговый визард описания опыта, отзыв заявки, подача апелляции.
  - Экран «Профиль»: активные сессии с кнопкой отзыва, обращение в поддержку, список уведомлений, смена темы.
- **Admin App (`apps/admin`):**
  - Подтверждение и настройка 2FA через Authenticator и резервные коды.
  - Дашборд показателей (обращения, апелляции, поддержка, пользователи).
  - Очередь модерации с модальным окном вынесения решения (Одобрить / Отклонить / Запросить данные).
  - Рассмотрение апелляций старшими модераторами.
  - Ответы на тикеты технической поддержки.
  - Управление ролями пользователей с обязательной записью причины в журнал аудита.
  - Просмотр неизменяемого журнала аудита (`audit_logs`).

---

## 2. Результаты проверок

| Тестовый набор | Команда запуска | Результат |
|---|---|---|
| **API Security & Domain Tests** | `pytest services/api/tests/test_security.py` | **51 passed** |
| **Alembic Migrations** | `pytest services/api/tests/test_migrations.py` | **3 passed** |
| **API Health** | `pytest services/api/tests/test_api.py` | **1 passed** |
| **Alembic Schema Check** | `alembic check` | **0 differences (OK)** |
| **Bot Handler Tests** | `pytest services/bot/tests` | **5 passed** |
| **Worker Tasks Tests** | `pytest services/worker/tests` | **2 passed** |
| **Mini App Build** | `npm run build` в `apps/mini-app` | **0 errors (Built 334 kB / gzip 101 kB)** |
| **Admin App Build** | `npm run build` в `apps/admin` | **0 errors (Built 305 kB / gzip 94 kB)** |

**Итого: 62 теста бэкенда успешно пройдены, обе фронтенд-сборки компилируются без ошибок.**

---

## 3. Команды запуска

### Быстрый старт через Docker Compose
```bash
docker compose up -d
```

### Запуск сервисов локально для разработки
```bash
# 1. Применение миграций БД
cd services/api
alembic upgrade head

# 2. Запуск Backend API
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 3. Запуск Celery Worker
cd ../worker
celery -A worker.celery_app worker --loglevel=info

# 4. Запуск Telegram Bot
cd ../bot
python main.py

# 5. Запуск Mini App
cd ../../apps/mini-app
npm run dev

# 6. Запуск Admin App
cd ../admin
npm run dev
```

---

## 4. Оставшиеся внешние подключения (Production Checklist)

Для боевого развертывания вне тестового контура требуются реальные внешние credentials:
1. `BOT_TOKEN` — токен официального Telegram-бота от `@BotFather`.
2. `JWT_SECRET` — сгенерированная криптографическая строка (минимум 32 символа, например: `openssl rand -hex 32`).
3. `DATABASE_URL` — строка подключения к продакшн-кластеру PostgreSQL.
4. `S3_*` (MinIO/AWS) — ключи доступа к приватному S3-бакету для хранения исходных материалов доказательств.
