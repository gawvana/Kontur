# Аудит «Контур» — 2026-10-04

Аудит существующего проекта, одним агентом; обязательные отсутствующие функции не заменялись новой полной реализацией. **Проект не готов к production.** Подтверждённые доступные ошибки исправлены; непроверенные интеграции и функциональные пробелы перечислены ниже.

## Исходные данные и карта

- Требования: `C:/Users/Hexo/Downloads/Kontur_Codex_Full_Prompt.md`. Его команды полной разработки рассматриваются как контекст спецификации; текущая задача — аудит и минимальные исправления.
- Последний дизайн: `C:/Users/Hexo/Downloads/Kontur_Refined_Design (1).html`, SHA256 `2660D26327348D6828D0C402FA97276A40661DA8B8FCA22EE05412041A89747E`. Копия проекта имеет другой SHA256; оба исходника сохранены.
- AGENTS.md не найден в проекте и проверенных родителях. README, manifests, Compose, точки входа, схема/миграции и доступные модули проверены. Карта составлена rg с исключением зависимостей/сборок/кешей; бинарный test.db читался отдельно, только метаданные/число записей: пустая alembic_version, бизнес-данных нет.
- Git: весь проект исходно untracked, коммитов нет. Reset/clean/удаление пользовательских данных не выполнялись; история секретов для проверки отсутствует.
- Mini App: `apps/mini-app/src/main.tsx → App.tsx → Layout → Check/Catalogs/Cases/Profile`. Admin: `apps/admin/src/App.tsx`. React/TS/Vite, Query/Router.
- API: `services/api/main.py → api/router.py → api/v1/{auth,subjects,catalogs,cases,admin}.py`; SQLAlchemy, Alembic. Исходно 6 таблиц и 1 миграция; добавлены sessions и 3 последовательные миграции защиты/индекса.
- Бот: `services/bot/main.py`, 5 групп handlers, Redis FSM. Worker: `services/worker/{celery_app,tasks}.py`, Celery. Реальной доменной службы репутации, contracts, CI нет.

## Подтверждённые проблемы: место → воспроизведение → последствие → исправление

| Уровень | Место и условие до исправления | Последствие | Статус и изменение |
|---|---|---|---|
| P0 | `api/v1/auth.py`: POST любой initData; verify возвращал постоянный тестовый ID | Неаутентифицированный вход, общая чужая личность | **исправлено**: HMAC по Telegram, обязательный user/int ID, срок 300 сек, будущее не более 30 сек, дубли параметров и плохая подпись 401 |
| P0 | `core/security.py`: JWT подписан встроенным известным секретом, .env называл его иначе | Возможность подделать личность существующего пользователя/сотрудника | **исправлено**: обязательный JWT_SECRET >=32 символов, PyJWT HS256 с обязательными claims, серверная sessions и отзыв; старые JWT не принимаются |
| P1 | `subjects.py`, DTO: поиск по телефону/% и GET известного ID без права | Чтение чужих приватных сведений и телефонов | **исправлено**: только связанные с текущим пользователем записи/свой аккаунт; телефон исключён; одинаковый 404 для чужого/неизвестного ID; URL не скачивается |
| P1 | `admin.py`: одной DB-роли достаточно без второго фактора | Незащищённый доступ сотрудников к материалам | **исправлено безопасным закрытием**: user 403, staff 503. Второй фактор и полноценная панель **отсутствуют**, это не завершённая административная авторизация |
| P1 | `cases.py`: повтор/гонка POST, свой telegram_id или отсутствующий subject | Дополнительные записи, самообращение, FK/500 вместо корректного отказа | **исправлено**: права/subject/self-check; ключ пользователя + уникальное ограничение, повтор результата, иной payload 409; author из сессии, лишние поля запрещены |
| P1 | `catalogs.py`: повтор/гонка создания каталога/членства | Дубли и риск неоднозначных приватных заметок | **исправлено**: обязательный ключ каталога, unique(owner,key), unique(catalog,subject); повтор одинакового контакта возвращает запись, иной текст 409 без перезаписи |
| P1 | UI Check возвращал John Doe/Safe на произвольный ввод; списки/профиль/admin-статистика вымышлены | Ложное представление о безопасности аккаунта и сохранённых данных | **исправлено**: доступный API подключён, реальные /me/списки/поиск, честные empty/error/недоступные функции, «Safe» убран |
| P1 | bot handlers и worker tasks: yes/support/appeal либо вызов task → success без записи/доставки | Потеря обращения/материалов при ложном подтверждении | **исправлено**: нет вымышленных успехов/inline-результатов; задачи явно fail; отсутствующая интеграция остаётся **отсутствующей** |
| P1 | requirements: устаревшие crypto/upload/Starlette-зависимости; pip-audit находил уязвимые версии | Небезопасный набор библиотек; применимость каждой CVE не выдаётся за доказанный exploit | **исправлено**: patched FastAPI/Starlette/PyJWT, неиспользуемые библиотеки убраны из runtime; отдельные точные lock-файлы; все три runtime audit без известных находок |
| P2 | manifests/Vite: недоустановленные router/query/icons и не объявленный Tailwind plugin | Обе сборки не выполнялись | **исправлено**: зависимости/locks и Tailwind подключены; финальные lint/tsc/build проходят |
| P2 | Compose: нет Dockerfile бота/frontend, неверные API_URL/package bind mount, нет BOT_TOKEN/JWT_SECRET у API, встроенные пароли | Стек не собирается/не запускается корректно; небезопасные defaults | **исправлено по коду**: Dockerfiles, runtime locks, правильные mounts/URL/env, обязательные secrets и loopback-порты; **проверка Docker заблокирована** |
| P2 | `db/database.py`: SQL echo=True | Приватные параметры запросов могли попадать в логи | **исправлено**: echo=False, парольный fallback убран; worker не печатает пользовательские материалы |
| P2 | Нормализованный поиск lower(username), прежний обычный индекс | План SQLite SCAN (полное сканирование индекса) | **исправлено**: functional index lower(username); миграционный тест требует SEARCH через новый индекс. PG нагрузка отдельно заблокирована |
| P2 | Неконстрейненные списки, FK-фильтры без индексов; отсутствует GET contacts | Неограниченная выборка/нет чтения сохранённых заметок | **исправлено**: limit 1..100, offset, стабильный ID, индексы owner/creator/status/catalog; scoped чтение contacts. UI contacts показывает первые 50 с явной подписью |
| P2 | Bot `/help` отсутствовал, нет `/cancel`, confirm message.text мог быть None; HTTP-клиент создавался при импорте | Нельзя отменить диалог; падение на нетекстовом сообщении; лишний клиент | **исправлено**: help/cancel до FSM catch-all, безопасный None, убрано создание неиспользуемого клиента, storage закрывается |
| P2 | Alembic URL с %; downgrade начальной PG-схемы не удалял enum-типы | Ошибка конфигурации/повторного upgrade | **исправлено**: escaping %, enum drop при PG downgrade; offline PG SQL проверен, live downgrade PG заблокирован |
| P2 | Генератор и docs заявляли Done, интеграции и p95 без соответствующих тестов; README ссылался на отсутствующий bootstrap | Ошибочная оценка готовности/невыполнимые команды | **исправлено**: генератор не перезаписывает код; README/API актуализированы, исторические отчёты явно помечены неподтверждёнными |

## Матрица всех областей: проверка → результат → статус

| Область | Проверка / результат | Статус |
|---|---|---|
| Запуск API/frontend | Реальные uvicorn/Vite и HTTP health/ready 200; обе apps build/lint, TS внутри build | **проверено, исправлено**; полный Compose **проверка заблокирована** |
| Установка/зависимости | npm install (+ Tailwind), pip install исходных pins и затем исправленных pins; runtime locks API 20, bot 26, worker 17 пакетов | **проверено, исправлено**; Linux-образы не запускались |
| Миграции/данные | Upgrade старой схемы с заметкой/обращением, schema check, downgrade/upgrade, отказ при дублирующих заметках без удаления | **проверено на SQLite, исправлено**; live PG **проверка заблокирована** |
| Auth/сессии/автор | Подпись, просроченное/будущее/подменённое user, отсутствующий BOT_TOKEN, forged/none/expired/sessionless JWT, logout/revoke, spoof creator | **проверено, исправлено**; configurable сроки/все сессии/renew/re-auth/rate limits **отсутствуют** |
| Объектные/полевые права | Чужой subject/catalog/contacts/cases и известный ID; телефоны не сериализуются; поле creator/owner запрещено | **проверено, исправлено**; файлы/экспорты/events/membership endpoints **отсутствуют** |
| Роли сотрудников/2FA | Роль читается из БД на запрос, user 403/staff 503; нет открытой регистрации admin | **проверено, исправлено закрытием**; 2FA/recovery/bootstrap/audit **отсутствуют** |
| Секреты/production | Встроенные defaults удалены, SQL echo выключен; в final JS нет маркеров тестовых/старых секретов и BOT_TOKEN; test wrapper не входит в dist | **проверено, исправлено**; git history отсутствует; production TLS/webhook/разделение конфигураций **отсутствуют** |
| XSS/SQL/SSRF/uploads | React выводит `<script>` заметки текстом, bot plain text; SQLAlchemy bind params; неподходящие URL отклонены без сетевого скачивания | **проверено для существующих путей**; загрузка/квоты/антивирус/изоляция **отсутствуют** |
| Username/идентификация | Точный нормализованный поиск; нет getChat-resolution, авто-слияния или переноса оценок по нику | **проверено**; observations/verified bindings/исторический владелец/merge-split/BigInt вместо String **отсутствуют** |
| Поиск и карточка | Только собственные связанные приватные данные; публичной карточки/истории/аватара/счётчиков нет | **проверено, исправлено**; полноценная публичная карточка **отсутствует** |
| Личные каталоги | Создание/list, добавление существующего доступного subject, чтение notes; default private и owner ACL | **проверено, исправлено**; создание новых contacts, rename/archive/delete/перенос/массовые операции **отсутствуют** |
| Контакты/заметки/теги/вложения | Note хранится на сервере CatalogItem, ограничения длины, чтение владельцем | **проверено**; редактор заметки, tags, избранное, файлы, история/корзина **отсутствуют** |
| Совместные каталоги/приглашения | Нет CatalogMember/Invite/SharedProjection и соответствующих API/UI | **отсутствуют**: роли, вступление, отзыв, передача владельца, safe sharing |
| Импорт/экспорт/удаление | Нет endpoints/models/jobs | **отсутствуют**: preview/дубли, CSV injection protection, re-auth, ACL при скачивании, account deletion/retention |
| Черновики/обращения/версии | Case только description/subject/PENDING, list mine, серверный author/key | **проверено, исправлено**; обязательная пошаговая форма, знак опыта, дата/сумма/основание, drafts/autosave/versions/withdraw **отсутствуют** |
| Репутация обоих знаков | Review есть только как неподключённая таблица; нет маршрута публикации/голоса | **отсутствует**: premoderation обоих знаков, одна активная оценка на пару, агрегаты и пересчёт hide/revoke/appeal/cancel. Self-case guard не заменяет эти правила |
| Доказательства/публикационные копии | Нет Evidence/upload/storage ACL/processing pipeline | **отсутствуют**: все форматы/квоты/карантин/redaction/preview; нельзя подтвердить безопасное скрытие и доступ к оригиналам; fake worker устранён |
| Модерация/ответы/апелляции | Нет Decision/Response/Appeal/ContentVersion или серверных переходов | **отсутствуют**: решение по фиксированной версии, отвод/независимый сотрудник, безопасные материалы второй стороне, исправление счётчиков |
| Подписки/уведомления/задачи | Celery импортируется; 2 task честно падают, обработка отсутствует; Redis FSM сконфигурирован | Fake success **исправлено**; subscriptions/notifications/outbox/retry/delivery/events **отсутствуют**; live очередь **проверка заблокирована** |
| Полноценный бот/перезапуск | 5 изолированных handler-тестов; help/cancel/None/inline; state Redis выбран, HTTP auth exchange не реализован | **проверено, исправлено** для доступных handlers; основные доменные сценарии/back/resume/dedup Update/webhook **отсутствуют**; Redis restart/Telegram **проверка заблокирована** |
| Mini App/админ согласованность | Mini App теперь читает текущий API; admin показывает честное закрытие, fake dashboard удалён | **проверено, исправлено**; сквозная согласованность всех трёх интерфейсов **отсутствует** из-за отсутствующего bot/domain/admin |
| UI/дизайн | Мобильный 360×740, обе темы, nav/back, формы/click/Enter, scroll и длинная note; base dark #101015/#1c1923, кастомные SVG из последнего reference, opaque surfaces, dock-only blur, no FAB | **проверено, исправлено**; сложные sheets/gestures, Uzbek, Onest self-host/license, logo, динамический dock/полный SDK/сохранение позиции **отсутствуют** |
| UI состояния | Browser: loading login, ordinary-browser отказ, bad URL error, empty contacts, admin forbidden, expired-initData error, logout; React Query pending/retry и серверная инвалидация создания | **проверено** для доступных сценариев; все состояния отсутствующих экранов **отсутствуют** |
| Performance/ресурсы | Ручной submit вместо запроса на каждую букву, AbortController, отсутствие бесконечных timers/SSE, BackButton cleanup, pagination, DB indexes; CSS reduced-motion, blur только dock | **проверено, исправлено** в существующем коде; p95 10k/100 users PG **проверка заблокирована**; N+1 не найден в доступных scalar-DTO путях |
| Кеш новой сборки | Vite hashed JS/CSS; API no-store; подготовлен nginx HTML revalidation/assets cache/CSP; service worker в коде отсутствует | **проверено, исправлено** по коду; nginx/реальный Telegram кеш **проверка заблокирована**; build_id/version endpoint/update notice **отсутствуют** |
| Эксплуатация/backup/CI | README исправлен; генераторский restore не соответствует именам Compose, journal deletion/реального restore/CI нет | **отсутствуют**: проверенное восстановление, CI, метрики/request_id, retention; live infra **проверка заблокирована** |

## Выполненные команды и доказательства

- Исходно `python -m pytest -q` в services/api: **1 passed**, проверял только `/health`. Frontend build падал на отсутствующих пакетах; старый lint ничего не доказывал о функциях.
- `npm.cmd install` и `npm.cmd install --save-dev tailwindcss @tailwindcss/vite` в обеих apps: успешно; npm audit при установке **0 известных уязвимостей**, locks сохранены.
- `python -m venv .audit-venv`; `pip install -r services/api/requirements.txt pytest==9.1.1 httpx==0.27.2 aiosqlite==0.22.1`: исходные pins устанавливаются, ранние 46 API-regressions passed. Затем `pip install -r services/api/requirements-dev.txt --upgrade pip`, worker requirements и bot requirements: успешно, с patched pins. Старые неиспользуемые пакеты в тестовом venv не являются runtime-контрактом.
- При последнем повторе обнаружена нестабильность собственного теста будущего auth_date: данные создавались при collection и становились допустимыми за время миграций. Исправлено: подписанные данные теперь создаются непосредственно перед запросом; повторный полный API-набор: **55 passed**, 50.04 сек.
- Финальные `../../.audit-venv/Scripts/python.exe -m pytest tests -q -p no:cacheprovider --disable-warnings` из API: **55 passed** (3 миграционных теста внутри); из bot: **5 passed**. `../.audit-venv/Scripts/python.exe -m pytest worker/tests -q -p no:cacheprovider --disable-warnings` из services: **2 passed**. API имеет предупреждения deprecated UTC/httpx-adapter; это не ошибки проверок. Конкурентные тесты SQLite не доказывают PG isolation.
- Финальные `npm.cmd run lint` и `npm.cmd run build` из обеих apps: **успешно**, build включает `tsc -b` + `vite build`. После выявленной собственной ошибки перекодирования Catalogs UTF-8 восстановлен, React lint warnings устранены, повторены только изменённые lint/build и UI. Final Mini App JS ~305.64 kB (gzip ~95.97), admin ~284.60 kB (gzip ~89.95).
- `pip_audit -r <runtime requirements.lock> --no-deps --disable-pip`: **API/bot/worker — 0 известных находок**. Исходный широкий venv-report находил уязвимые версии в 6 пакетах (повторы advisory ID не считаются уникальными багами); финально проверены именно отдельные production locks, не тестовый инструментарий. Lock-файлы точные, пока без wheel hashes.
- `alembic upgrade head` на новой `.audit/ui.db`: успешно; тесты отдельно создают одноразовые БД и сохраняют старые note/case при upgrade/downgrade/upgrade, проверяют schema check и безопасный отказ на дубликатах. PostgreSQL `upgrade head --sql` проверяет enum/сессии/constraints/%-пароль; **live PG не проверен**.
- `uvicorn main:app --host 127.0.0.1 --port 8000`, `npm run dev -- --host 127.0.0.1 --port 5173/5174 --strictPort`: реально запускались. HTTP `/health` 200, `/ready` 200 и no-store. Python AST: **39 модулей прошли** до финальной индексной миграции (она дополнительно исполняется миграционными тестами).
- Браузерные действия выполнялись в Codex Browser. Обычный URL требует Telegram; `.audit/test.html` использует подписанную синтетическую initData, одноразовую БД, исключён из dist и Docker context. В bundle нет маркеров синтетических/прежних секретов или BOT_TOKEN. Никаких рассылок/публикаций/реальной Telegram-авторизации не выполнялось.
- Ограничения среды: sandbox EPERM при Vite child process и pytest cache/venv; нужные повторные команды выполнялись с разрешённой эскалацией. Python testpaths исключает временные pytest-cache-files. Docker, psql/pg_ctl, PostgreSQL/Redis service и реальные токены отсутствуют.

## Сквозные сценарии и блокеры

1. **Доступная цепочка проверена**: подписанный тестовый вход → создать приватный каталог → читать принадлежащий каталог/контакт/длинную заметку → GET своих PENDING cases → logout, плюс серверные POST case/contact и конкурентные повторы в тестах. Новые subjects через интерфейс создать нельзя. Контакт/note в браузерной цепочке подготовлены тестовой фикстурой — это не создание их через UI.
2. **Полная цепочка** вход → каталог → новый контакт → заметка → обращение с доказательством → решение → карточка → ответ → апелляция → исправление **не прошла: обязательные функции отсутствуют**, а не только не хватает токена.
3. **Совместный каталог**: не существует реализация, сценарий не пройден. **Основной бот**: не существует API-интеграция, успешный доменный сценарий не пройден. Cancel/help и отсутствие ложных подтверждений тестированы отдельно.
4. Для live проверок нужны Docker/Linux или выделенные PostgreSQL+Redis+private S3, отдельная тестовая БД, реальный BOT_TOKEN, разрешённый HTTPS Mini App URL и тестовые Telegram-аккаунты. Сначала запустить Compose/migrations/readiness; затем PG races и bot FSM restart. Проверки Android/iOS/Telegram/WebView-клавиатуры, nginx cache/CSP, S3 ACL и доставки остаются **заблокированными**. Desktop/browser viewport — лишь эмуляция.
5. Перед новой миграцией существующей БД сделать backup. При старых дубликатах членства сначала согласовать перенос всех приватных note, не удалять их автоматически. Старые токены потребуют повторного входа. Архив тестового `.audit` и venv не входят в продукт.

## Состояние продолжения

Аудит всех перечисленных областей завершён классификацией выше; нет оснований заявлять, что найдены абсолютно все ошибки. Следующий шаг аудита при доступной инфраструктуре — live Docker/PG/Redis/Telegram и проверка deployment headers. Отдельная разработка нужна для перечисленных отсутствующих функций, особенно identity/evidence/versions/reputation/moderation/appeals/shared catalogs/full bot/admin 2FA. Не начинать продолжение с повторного чтения уже проверенных неизменённых модулей; использовать эту карту и новые результаты.

## Источники протокола и обновлений

- [Официальная проверка Telegram initData](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app).
- [PyJWT: опубликованные версии и API](https://pypi.org/project/PyJWT/), [FastAPI](https://pypi.org/project/fastapi/), [Starlette advisories](https://github.com/Kludex/starlette/security/advisories).

Заключительный результат: API 55 + bot 5 + worker 2 = **62 passed**; final frontend lint/tsc/build успешно, runtime audits 0 известных находок. Тестовые API/Vite-серверы после проверки остановлены; одноразовые фикстуры и окружение оставлены в игнорируемых `.audit`/`.audit-venv` для воспроизведения.
