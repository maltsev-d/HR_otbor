# HR_otbor — Telegram HR Screening Bot

Telegram bot for automated candidate screening with a web admin panel. Portfolio project targeting Southeast Asian markets (Laos, Thailand) with 4-language support.

The bot guides candidates through a 12-step application form, analyzes resumes using AI, applies auto-reject rules, and notifies HR with a ready-made summary. HR manages the pipeline via the web panel or directly from Telegram.

---

## Stack

| Layer | Technologies |
|---|---|
| Bot | Python 3.12, aiogram 3.x, FSM MemoryStorage |
| Web panel | Flask, Jinja2, Blueprint |
| Database | PostgreSQL, SQLAlchemy (sync) |
| RAG search | ChromaDB, Cohere `embed-multilingual-v3.0` |
| LLM | Groq (primary) / OpenAI / Ollama — switched via `.env` |
| Resume analysis | pdfplumber (PDF), python-docx (DOCX) |
| Deploy | Render free tier |
| Languages | 4 languages: RU / EN / LO / TH — single codebase |

---

## Architecture

Flask and the bot run in one process: Flask in a daemon thread (`run_web`), bot in asyncio (`main()`). `rebuild_index()` is called as the first line in `main()` — re-indexes ChromaDB from Postgres on every start (Render file system is ephemeral).

**FSM application flow** (`bot/states/application.py`):
```
waiting_for_vacancy → waiting_for_vacancy_confirm →
waiting_for_full_name → waiting_for_consent →
waiting_for_resume → waiting_for_contact →
waiting_for_location → waiting_for_age →
waiting_for_languages → waiting_for_experience →
waiting_for_salary → waiting_for_start_date →
waiting_for_work_type → (complete)
```

Main bot screen: `is_featured` vacancies as buttons + "Search positions" button triggering semantic RAG search (`waiting_for_search_query`).

Two HR control channels: inline buttons under Telegram notifications and web panel on port 10000.

---

## Project Structure

```
HR_otbor/
├── bot/
│   ├── handlers/
│   │   ├── candidate.py     # Full application FSM
│   │   ├── hr_actions.py    # HR buttons: invite / reject / clarify
│   │   └── nudge.py         # Scheduler: draft reminders + invite nudges
│   ├── rag/
│   │   └── index.py         # ChromaDB: rebuild / upsert / search
│   ├── services/
│   │   ├── autoreject.py    # Auto-reject rule engine
│   │   └── llm_service.py   # AI summary + resume text extraction
│   ├── states/
│   │   └── application.py   # FSM states
│   └── main.py              # Entry point: bot + Flask in one process
├── admin/
│   ├── app.py               # Flask Blueprint, all routes
│   ├── telegram.py          # Bot API helpers (invite, send, forward resume)
│   └── templates/           # Jinja2 HTML templates
├── config/
│   ├── questions.py         # All bot strings in 4 languages + q() helper
│   ├── settings.py          # Env vars: BOT_TOKEN, BOT_LANG, ADMIN_IDS, etc.
│   └── llm.py               # LLM provider factory (Groq / OpenAI / Ollama)
└── db/
    ├── models.py            # SQLAlchemy models
    ├── session.py           # SessionLocal
    └── init_db.py           # Create all tables
```

---

## Database Schema

7 tables (normalized from the original monolithic Candidate model):

| Table | Purpose |
|---|---|
| `candidates` | Application + funnel status (`draft → new → invited → confirmed/declined/rejected`) + `ai_summary` |
| `vacancies` | `title`, `description`, `is_active`, `is_featured` — default/fallback fields |
| `vacancy_translations` | Translations per language: `(vacancy_id, lang, title, description)` |
| `applications` | Candidate ↔ vacancy link, `resume_file_id` (Telegram file_id) / `resume_url` |
| `interviews` | `scheduled_at`, `confirmed`, `declined`, `invite_nudge_sent` |
| `hr_messages` | HR ↔ candidate history, `answer=NULL` until replied |
| `auto_reject_rules` | Field / condition (`gt`/`lt`/`eq`/`contains`) / value |
| `hr_admins` | HR list by `tg_id` |

> `tg_id` and `hr_tg_id` are strictly `BigInteger` — Telegram IDs don't fit in int32.

Resumes are stored as Telegram `file_id`, not on disk — Render ephemeral FS would wipe files on restart.

---

## Multilingual Support

Single deploy = single language. Set `BOT_LANG` in `.env`:

```env
BOT_LANG=en   # en | lo | th | ru
```

All bot texts, buttons, HR notifications and error messages go through `config/questions.py` via the `q("key")` helper. No hardcoded strings in handlers.

Salary currency is derived automatically from language:

| BOT_LANG | Currency |
|---|---|
| `lo` | LAK |
| `th` | THB |
| `en` | USD |
| `ru` | RUB |

Vacancy translations are stored in `vacancy_translations`. When a vacancy is created in the admin panel, identical records are created for all 4 languages — HR updates translations manually as needed.

RAG indexes only the `BOT_LANG` translation from `vacancy_translations`. Cohere `embed-multilingual-v3.0` supports all 4 languages natively — no separate indexes needed.

---

## RAG Vacancy Search

Manual implementation without LangChain/LlamaIndex.

- `bot/rag/index.py`: `rebuild_index()`, `upsert_vacancy()`, `delete_vacancy()`, `search_vacancies(query, n_results)` — score cutoff at 0.5
- ChromaDB is a search index only, not the source of truth. Sync is one-way: Postgres → ChromaDB
- `upsert_vacancy`/`delete_vacancy` are called in Flask CRUD routes — when `is_active=False`, vacancy is removed from index
- Cold start guard: `n_results = min(n_results, collection.count())` prevents IndexError on empty index

---

## Auto-reject Rules

`bot/services/autoreject.py`: `check_autoreject(session, candidate)` loops through active `AutoRejectRule` records.

Supported fields: `salary_amount`, `age`, `languages`, `work_type`

Supported conditions:
- `gt` / `lt` — numeric comparison (salary, age)
- `eq` — exact string match
- `contains` — substring match (for languages, work_type)

`languages` and `work_type` string conditions are wired in but disabled in the admin form by default.

---

## AI Summary

Generated after application completion via `bot/services/llm_service.py`.

**Inputs:**
- Candidate application data (location, age, languages, experience, salary, start date, work type)
- Resume file text if PDF/DOCX was attached (extracted via pdfplumber / python-docx, truncated to 3000 chars)
- If resume is a URL link — only application data is analyzed

**Output language:** controlled by `BOT_LANG` via `Respond in {language}` directive in the prompt.

Provider switching is handled by `config/llm.py` factory — returns `(AsyncOpenAI client, model)`. Change provider with one line in `.env`:

```env
LLM_PROVIDER=groq        # groq | openai | ollama
LLM_MODEL=llama-3.3-70b-versatile
```

---

## Auto-reminders (Nudge Scheduler)

`bot/handlers/nudge.py` — `run_scheduler()`, infinite loop, checks every 30 minutes:

- **Abandoned applications** — `status=draft`, `created_at` older than 24h, `nudge_sent=False` → "Continue application" button
- **No response to invite** — `status=invited`, `Interview.scheduled_at` older than 2h, `invite_nudge_sent=False` → repeat confirm/decline keyboard

Resume recovery (`resume_application`) checks `RESUME_STEPS` list and returns candidate to the first unfilled step.

---

## Flask Admin Panel

Light theme, `#EEF0FA` background, purple gradient sidebar, Plus Jakarta Sans.

**Routes:**
```
GET  /dashboard
GET  /candidates                          ?status= filter
GET  /candidates/<id>
POST /candidates/<id>/request-resume      forward resume to HR via Telegram
GET  /resume/<candidate_id>              download resume — proxies Bot API, token stays server-side
POST /schedule/<id>
POST /reject/<id>
POST /clarify/<id>
GET  /vacancies
POST /vacancy/add                         + upsert into ChromaDB + create all 4 language translations
POST /vacancy/update-translation/<id>     update one language translation
POST /vacancy/toggle/<id>                 + upsert/delete in ChromaDB
POST /vacancy/toggle-featured/<id>
POST /vacancy/delete/<id>                 + delete from ChromaDB
GET  /autorules
POST /autorules/add
POST /autorules/toggle/<id>
POST /autorules/delete/<id>
GET  /hr-admins
POST /hr-admins/add
POST /hr-admins/delete/<id>
GET  /login  POST /login
GET  /logout
```

Status labels and auto-reject field names are localized via Jinja filters `status_ru`, `field_ru`, `cond_ru`.

Actions are accompanied by toast notifications (`flash()` + `showToast()` in `base.html`).

---

## Environment Variables

```env
BOT_TOKEN=
ADMIN_IDS=123456789,987654321
DATABASE_URL=postgresql://user:pass@host/db
BOT_LANG=en
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile
GROQ_API_KEY=
OPENAI_API_KEY=
COHERE_API_KEY=
ADMIN_LOGIN=admin
ADMIN_PASSWORD=changeme
FLASK_SECRET_KEY=your-secret-key
```

---

## Deploy

```
Render free tier
├── Bot + Flask in one process
├── Flask in daemon thread (port 10000)
├── Nudge scheduler as asyncio.gather with the bot
└── PostgreSQL — Render managed DB
```

UptimeRobot pings `/dashboard` every 14 minutes to prevent sleep.

**DB reset:**
```sql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```
Then run `python db/init_db.py`.

---

## Known Issues & Gotchas

- `HRAdmin` table and `ADMIN_IDS` env var are not synced — adding HR via web panel doesn't affect real notification routing
- No authentication scope per HR — all admins see all candidates
- `MemoryStorage` for FSM — resets on Render restart; Redis needed for production
- Duplicate `Application` records possible if candidate submits twice
- AI summary occasionally empty if LLM API times out — no retry logic yet

---

## Test Data

**Vacancies (seed_vacancies.sql):** 6 positions — 3 standard (Restaurant Manager, Sales Manager, Accountant) + 3 unusual for RAG demo (Cat Café Host, Night Market Coordinator, Corporate Wellness Consultant). Unusual vacancies make semantic search visually impressive in demos.

**Candidates (seed_candidates.sql):** 25 candidates — English, Thai, Lao languages; all statuses (new / invited / confirmed / declined / rejected / draft); realistic names, contacts, experience.