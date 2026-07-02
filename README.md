# HR_podbor

Telegram-бот для скрининга кандидатов + Flask-админка для HR. Портфолио-проект: рабочая функциональность важнее идеальной архитектуры.

## Стек

| | |
|---|---|
| Python | 3.12 |
| Бот | aiogram 3.x, FSM MemoryStorage |
| Веб | Flask, Jinja2, Blueprint |
| БД | PostgreSQL, SQLAlchemy (sync) |
| RAG | ChromaDB + sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`, 384-dim, cosine) |
| LLM | Ollama/Mistral (dev) ↔ OpenAI (prod), фабрика в `config/llm.py` |
| Деплой | Render free tier, UptimeRobot (анти-сон) |
| IDE | PyCharm на Windows |

## Архитектура

Flask и бот работают в одном процессе: Flask в daemon-треде (`run_web`), бот в asyncio (`main()`). `rebuild_index()` вызывается первой строкой в `main()` — переиндексация ChromaDB из Postgres при каждом старте (файловая система на Render эфемерная).

**FSM-флоу анкеты** (`bot/states/application.py`):
```
waiting_for_vacancy → waiting_for_full_name → waiting_for_consent →
waiting_for_resume → waiting_for_contact → waiting_for_location →
waiting_for_age → waiting_for_english → waiting_for_salary →
waiting_for_start_date → waiting_for_contract_type → (завершение)
```

Главный экран бота — гибридный: `is_featured` вакансии кнопками + кнопка «Найти другую вакансию», запускающая семантический RAG-поиск (`waiting_for_search_query`).

Два канала управления для HR: кнопки под уведомлением в Telegram и веб-панель на порту 10000.

## Структура проекта



## Схема БД

Нормализована в шесть таблиц (актуальная версия, заменила старую монолитную модель):

| Таблица | Назначение |
|---|---|
| `Candidate` | Анкета + статус воронки (`draft → new → invited → confirmed/declined/rejected`) + `ai_summary` |
| `Vacancy` | `title`, `description`, `is_active`, `is_featured` |
| `Application` | Связка candidate↔vacancy, `resume_file_id` (Telegram file_id) / `resume_url` |
| `Interview` | `scheduled_at`, `confirmed`, `declined`, `invite_nudge_sent` |
| `HRMessage` | История HR↔кандидат, `answer=NULL` до ответа |
| `AutoRejectRule` | Правила автоотсева: поле / условие (`gt`/`lt`) / значение |
| `HRAdmin` | Список HR по `tg_id` |

Важно: `tg_id` и `hr_tg_id` — строго `BigInteger`, не `Integer` (Telegram ID не влезает в int32, был баг).

Резюме хранится как Telegram `file_id`, не на диске — эфемерная FS Render сбрасывала бы файлы при рестарте.

## RAG-поиск вакансий

Ручная реализация без LangChain/LlamaIndex (осознанный выбор — сначала понять механику, абстракции потом).

- `bot/rag/index.py`: `rebuild_index()` (полная переиндексация), `upsert_vacancy()`, `delete_vacancy()`, `search_vacancies(query, n_results)` — отсечка по score < 0.4
- ChromaDB — только поисковый индекс, не источник истины. Синхронизация одностороняя: Postgres → ChromaDB
- `upsert_vacancy`/`delete_vacancy` подключены к Flask CRUD-роутам вакансий (`vacancy_add`, `vacancy_toggle`, `vacancy_delete`) — при `is_active=False` вакансия убирается из индекса

## Автоотсев кандидатов

`services/autoreject.py`: `check_autoreject(session, candidate)` проходит активные `AutoRejectRule`, сравнивает `salary_expectation`/`age` через `gt`/`lt`.

Подключено в `bot/handlers/candidate.py`, `handle_contract_type` — inline-логика вместо `save_partial_candidate`, чтобы вставить проверку между записью полей и коммитом статуса. При срабатывании кандидат сразу получает `rejected`, уведомление HR не отправляется.

Управление правилами — `admin/templates/autorules.html`, CRUD через `/autorules/*`.

## Автонапоминания

`bot/handlers/nudge.py` — `run_scheduler()`, бесконечный цикл, проверка каждые 30 минут:

- **Брошенные анкеты** — `status=draft`, `created_at` старше 24ч, `nudge_sent=False` → кнопка «Продолжить заполнение»
- **Нет ответа на приглашение** — `status=invited`, `Interview.scheduled_at` старше 2ч, `invite_nudge_sent=False` → повторная клавиатура подтвердить/отказаться

Восстановление анкеты (`resume_application`) идёт по списку `RESUME_STEPS`, который сверяет заполненные поля кандидата и возвращает на первый пустой шаг.

## AI-саммари кандидатов

После завершения анкеты генерируется через `bot/services/llm_service.py`, провайдер переключается через `.env` (`LLM_PROVIDER=ollama|openai`). Саммари сохраняется в `Candidate.ai_summary` и уходит HR вместе с уведомлением о новом кандидате.

## Flask-админка

Светлая тема, `#EEF0FA` фон, фиолетовый градиентный сайдбар, Plus Jakarta Sans, gradient stat-карточки, `fadeSlideUp`-анимации.

**Роуты:**
```
GET  /dashboard
GET  /candidates                          ?status= фильтр
GET  /candidates/<id>
POST /candidates/<id>/request-resume      пересылка резюме HR в Telegram
GET  /resume/<candidate_id>               скачивание резюме — проксирует Bot API, не светит токен
POST /schedule/<id>
POST /reject/<id>
POST /clarify/<id>
GET  /vacancies
POST /vacancy/add                         + upsert в ChromaDB
POST /vacancy/toggle/<id>                 + upsert/delete в ChromaDB
POST /vacancy/toggle-featured/<id>
POST /vacancy/delete/<id>                 + delete из ChromaDB
GET  /autorules
POST /autorules/add
POST /autorules/toggle/<id>
POST /autorules/delete/<id>
GET  /hr-admins
POST /hr-admins/add
POST /hr-admins/delete/<id>
```

Статусы (`draft`/`new`/`invited`/`confirmed`/`declined`/`rejected`) и поля автоправил локализованы через jinja-фильтры `status_ru`, `field_ru`, `cond_ru` (`admin_bp.app_template_filter`).

Действия сопровождаются toast-уведомлениями (`flash()` + `showToast()` в `base.html`, обёрнуто в `DOMContentLoaded`).

## Известные баги и грабли (для памяти)

- `TemplateNotFound` может возникать из-за пустой строки между декоратором роута и `def` — Python это не ломает, а Flask/Jinja иногда путается в стек-трейсе, ищи реальную причину в самом тексте ошибки
- Jinja template-фильтры (`app_template_filter`) нужно физически вставлять в файл — обсуждение в чате не равно правке кода
- `flash()` требует `app.secret_key`, иначе сообщения тихо теряются без исключений
- Скрипт, рендерящий flash-сообщения в DOM, должен ждать `DOMContentLoaded` — иначе контейнер может быть ещё не готов
- Смешение sync SQLAlchemy с `async`/`await` даёт `ImportError`/сессионные баги — весь `db/session.py` синхронный, RAG-слой писался под это же
- `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` — рабочий способ сбросить БД при блокирующих FK
- **Требует проверки:** `nudge.py`, `resume_application` — обращение `QUESTION_FLOW[q_idx]["text"]` по индексу вместо `q("ключ")`. Это тот самый баг с съехавшими индексами из-за `full_name`, который чинили в основном флоу анкеты (см. секцию FSM) — здесь фикс не подтянут. Если функция реально используется, кнопка «Продолжить заполнение» отдаёт не тот вопрос
- **Требует проверки:** `hr_actions.py`, `handle_resume` — `Application.filter_by(candidate_id=...).first()` без фильтра по конкретной заявке. При нескольких откликах одного кандидата на разные вакансии вернёт произвольную первую

## Открытые задачи

🔴 Критично:
- `HRAdmin` (таблица) и `ADMIN_IDS` (`.env`) не синхронизированы — добавление HR через веб-панель не влияет на реальную рассылку уведомлений
- Авторизации в Flask-админке нет вообще — открыта всем, кто знает URL
- Атрибуция HR-сообщений захардкожена на первый `ADMIN_IDS`, не на реального автора из веб-панели (зависит от решения авторизации)

🟡 Средний приоритет:
- AI-summary иногда не приходит вместе с уведомлением — вероятно `generate_candidate_summary` возвращает пусто, причина не диагностирована
- `is_active` фильтр не хранится в metadata ChromaDB, фильтрация только на уровне Postgres при rebuild — при росте числа вакансий стоит вынести в индекс
- Нет обработки кейса, когда ChromaDB пуста и `n_results` больше числа записей

🟢 Низкий приоритет / не критично для демо:
- Дублирующиеся записи `Application` при повторной подаче кандидата
- `MemoryStorage` для FSM — сбрасывается при рестарте Render, нужен Redis для продакшена
- Экспорт кандидатов в Excel
- Мультитенантность (`company_id` в моделях) — сейчас один деплой = один клиент
- Динамическое редактирование FSM-вопросов через админку — осознанно вне скоупа, слишком сложно для портфолио-демо

## Тестовые данные

20 вакансий: 5 featured стандартных, 5 обычных стандартных, 10 через RAG-only с нарочито нестандартными названиями (грумер котят, сомелье, дегустатор мороженого, астролог корпоративных решений) — демонстрируют семантический поиск, не keyword-based.

## Принципы разработки

- Демо-портфолио — рабочий функционал важнее чистой архитектуры
- Понять механику RAG вручную до перехода на фреймворки
- ChromaDB — не источник истины, только поисковый индекс
- FSM-стейт обязан нести `app_id` явно, чтобы не путать параллельные заявки
- Резюме через Telegram `file_id`, браузерный доступ — только через серверный прокси (токен бота не должен попадать в клиент)