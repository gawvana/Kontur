# Проверенный API «Контур»

Полные результаты и ограничения: [AUDIT.md](AUDIT.md). OpenAPI выдаётся работающим FastAPI на `/openapi.json`. Отсутствующие маршруты здесь не объявляются реализованными.

Все защищённые операции используют `Authorization: Bearer <access_token>`; токен выдаётся только после подписи и свежести Telegram initData. Бизнес-ответы имеют Cache-Control: no-store.

| Метод и путь | Фактическое поведение |
|---|---|
| POST /api/v1/auth/telegram | JSON initData; HMAC, auth_date 5 минут, допуск будущего 30 секунд; JWT + серверная сессия 60 минут |
| GET /api/v1/auth/me | Текущий пользователь из действующей серверной сессии |
| POST /api/v1/auth/logout | Немедленный отзыв текущей сессии, 204 |
| GET /api/v1/subjects/search?q= | Точный username/@username/HTTPS-профиль t.me или telegram.me; только связанные приватные записи/свой аккаунт; телефон исключён |
| GET /api/v1/subjects/{id} | Те же объектные права; чужая и неизвестная запись дают одинаковый 404 |
| GET /api/v1/catalogs | Каталоги владельца; limit 1..100 (50 по умолчанию), offset >=0 |
| POST /api/v1/catalogs | name, is_private (true по умолчанию); обязательный Idempotency-Key, повтор с иным содержимым 409 |
| GET /api/v1/catalogs/{id}/contacts | Только владелец; limit/offset как выше |
| POST /api/v1/catalogs/{id}/contacts | subject_id, note, is_private; только доступный контакт; повтор членства с тем же содержимым возвращает прежний результат, иной текст 409 |
| POST /api/v1/cases | subject_id, description; автор из сессии, самообращение запрещено; обязательный Idempotency-Key; только PENDING |
| GET /api/v1/cases/my | Обращения автора; limit/offset как выше |
| GET /api/v1/admin/cases | 403 обычному пользователю; 503 сотруднику до реализации второго фактора |
| GET /health | Проверка процесса |
| GET /ready | Проверка подключения и таблицы sessions; 503 при недоступности |

Нет API создания subject, редактирования/удаления заметки, тегов, файлов, совместных ролей/приглашений, drafts/versions, публичных отзывов/счётчиков, decisions, responses, appeals, подписок/уведомлений, событий, импорта/экспорта и удаления аккаунта. Контракта ошибок с request_id пока нет. При обновлении потребуется повторный вход: старые JWT не имеют серверной сессии.
