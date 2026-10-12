import logging
import re

from aiogram import F, Router
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.rag.index import search_vacancies
from bot.services.autoreject import check_autoreject
from bot.services.llm_service import generate_candidate_summary
from bot.states.application import ApplicationForm
from config.questions import q
from config.settings import ADMIN_IDS, DEFAULT_CURRENCY
from db.models import Application, Candidate, Vacancy, VacancyTranslation
from db.session import SessionLocal

router = Router()
logger = logging.getLogger(__name__)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

async def safe_send(bot, chat_id, text, **kwargs):
    try:
        await bot.send_message(chat_id, text, **kwargs)
    except TelegramNetworkError as e:
        logging.error(f"Telegram error {chat_id}: {e}")
    except Exception:
        logging.exception("Send error")


def save_partial_candidate(tg_id: int, data: dict, status: str = "draft"):
    candidate_fields = {
        "full_name", "consent", "contact", "location", "age",
        "languages", "experience", "salary_amount", "salary_currency",
        "start_date", "work_type",
    }
    candidate_data = {k: v for k, v in data.items() if k in candidate_fields}
    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(tg_id=tg_id).first()
        if candidate:
            for k, v in candidate_data.items():
                setattr(candidate, k, v)
            candidate.status = status
        else:
            candidate = Candidate(tg_id=tg_id, **candidate_data, status=status)
            session.add(candidate)
        session.commit()


def save_application(tg_id: int, vacancy_id: int) -> int:
    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(tg_id=tg_id).first()
        if not candidate:
            candidate = Candidate(tg_id=tg_id, status="draft")
            session.add(candidate)
            session.flush()
        app = Application(candidate_id=candidate.id, vacancy_id=vacancy_id)
        session.add(app)
        session.commit()
        return app.id


def update_application(app_id: int, data: dict):
    fields = {"resume_file_id", "resume_url"}
    app_data = {k: v for k, v in data.items() if k in fields}
    if not app_data:
        return
    with SessionLocal() as session:
        app = session.get(Application, app_id)
        if app:
            for k, v in app_data.items():
                setattr(app, k, v)
            session.commit()


def get_vacancy_keyboard(vac_list: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """Строит клавиатуру списка вакансий."""
    rows = [
        [InlineKeyboardButton(text=title, callback_data=f"vacancy:{vid}")]
        for vid, title in vac_list
    ]
    rows.append([InlineKeyboardButton(text=q("search_btn"), callback_data="search_vacancy")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_vacancy_list(bot, chat_id: int, state: FSMContext, with_greeting: bool = True):
    """Показывает список featured вакансий. Используется из /start и из кнопки Back."""
    from config.settings import BOT_LANG
    with SessionLocal() as session:
        vacancies = session.query(Vacancy).filter_by(is_active=True, is_featured=True).all()
        vac_list = []
        for v in vacancies:
            tr = session.query(VacancyTranslation).filter_by(vacancy_id=v.id, lang=BOT_LANG).first()
            title = tr.title if tr else v.title
            vac_list.append((v.id, title))

    if not vac_list:
        await safe_send(bot, chat_id, q("no_vacancies"))
        return

    text = q("vacancy") if with_greeting else q("vacancy_back").replace("← ", "")
    await safe_send(bot, chat_id, text, reply_markup=get_vacancy_keyboard(vac_list))
    await state.set_state(ApplicationForm.waiting_for_vacancy)


# ─── /START ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    await show_vacancy_list(message.bot, message.chat.id, state, with_greeting=True)


# ─── ПОИСК ────────────────────────────────────────────────────────────────────

@router.callback_query(ApplicationForm.waiting_for_vacancy, F.data == "search_vacancy")
async def handle_search_button(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(q("search_prompt"), parse_mode="HTML")
    await state.set_state(ApplicationForm.waiting_for_search_query)
    await callback.answer()


@router.message(ApplicationForm.waiting_for_search_query)
async def handle_search_query(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    if not query:
        return await safe_send(message.bot, message.chat.id, q("search_prompt"))

    results = search_vacancies(query, n_results=5)
    if not results:
        await safe_send(message.bot, message.chat.id, q("search_no_results"))
        return

    rows = [
        [InlineKeyboardButton(
            text=f"{r['title']} ({r['score']:.0%})",
            callback_data=f"vacancy:{r['vacancy_id']}"
        )]
        for r in results
    ]
    rows.append([InlineKeyboardButton(text=q("vacancy_back"), callback_data="back_to_list")])
    await message.answer(q("search_btn"), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await state.set_state(ApplicationForm.waiting_for_vacancy)


# ─── КНОПКА "НАЗАД К СПИСКУ" ──────────────────────────────────────────────────

@router.callback_query(F.data == "back_to_list")
async def handle_back_to_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_vacancy_list(callback.bot, callback.message.chat.id, state, with_greeting=False)
    await callback.answer()


# ─── ВЫБОР ВАКАНСИИ → КАРТОЧКА ────────────────────────────────────────────────

@router.callback_query(ApplicationForm.waiting_for_vacancy, F.data.startswith("vacancy:"))
async def handle_vacancy(callback: CallbackQuery, state: FSMContext):
    from config.settings import BOT_LANG
    vacancy_id = int(callback.data.split(":")[1])

    with SessionLocal() as session:
        vacancy = session.query(Vacancy).filter_by(id=vacancy_id, is_active=True).first()
        if not vacancy:
            await callback.answer("Position unavailable", show_alert=True)
            return
        tr = session.query(VacancyTranslation).filter_by(vacancy_id=vacancy_id, lang=BOT_LANG).first()
        title       = tr.title       if tr else vacancy.title
        description = tr.description if tr else vacancy.description

    # Сохраняем выбор в state, но Application создаём только после Apply
    await state.update_data(selected_vacancy_id=vacancy_id, selected_vacancy_title=title)

    desc_text = description[:300] + "…" if description and len(description) > 300 else (description or "")
    card_text = f"<b>{title}</b>\n\n{desc_text}" if desc_text else f"<b>{title}</b>"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=q("vacancy_apply"), callback_data=f"apply:{vacancy_id}")],
        [InlineKeyboardButton(text=q("vacancy_back"),  callback_data="back_to_list")],
    ])
    await callback.message.answer(
        f"{q('vacancy_detail')}\n\n{card_text}",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await state.set_state(ApplicationForm.waiting_for_vacancy_confirm)
    await callback.answer()


# ─── APPLY ────────────────────────────────────────────────────────────────────

@router.callback_query(ApplicationForm.waiting_for_vacancy_confirm, F.data.startswith("apply:"))
async def handle_apply(callback: CallbackQuery, state: FSMContext):
    vacancy_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    title = data.get("selected_vacancy_title", "")

    app_id = save_application(callback.from_user.id, vacancy_id)
    await state.update_data(vacancy_id=vacancy_id, app_id=app_id)

    await callback.message.answer(
        f"✅ <b>{title}</b>\n\n{q('full_name')}",
        parse_mode="HTML",
    )
    await state.set_state(ApplicationForm.waiting_for_full_name)
    await callback.answer()


# ─── FULL NAME ────────────────────────────────────────────────────────────────

@router.message(ApplicationForm.waiting_for_full_name)
async def handle_full_name(message: Message, state: FSMContext):
    full_name = (message.text or "").strip()
    if not full_name or len(full_name.split()) < 2:
        return await safe_send(message.bot, message.chat.id, q("full_name"))

    first_name = full_name.split()[0]
    await state.update_data(full_name=full_name)
    save_partial_candidate(message.from_user.id, await state.get_data())

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=q("consent_yes"), callback_data="consent:yes"),
        InlineKeyboardButton(text=q("consent_no"),  callback_data="consent:no"),
    ]])
    await safe_send(
        message.bot, message.chat.id,
        f"{first_name} 👋\n\n{q('consent')}",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await state.set_state(ApplicationForm.waiting_for_consent)


# ─── CONSENT ──────────────────────────────────────────────────────────────────

@router.callback_query(ApplicationForm.waiting_for_consent, F.data == "consent:yes")
async def handle_consent_yes(callback: CallbackQuery, state: FSMContext):
    await state.update_data(consent=True)
    save_partial_candidate(callback.from_user.id, await state.get_data())
    await callback.message.answer(q("resume"))
    await state.set_state(ApplicationForm.waiting_for_resume)
    await callback.answer()


@router.callback_query(ApplicationForm.waiting_for_consent, F.data == "consent:no")
async def handle_consent_no(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(q("consent_declined"))
    await callback.answer()


# ─── RESUME ───────────────────────────────────────────────────────────────────

@router.message(ApplicationForm.waiting_for_resume)
async def handle_resume(message: Message, state: FSMContext):
    if message.document:
        await state.update_data(resume_file_id=message.document.file_id, resume_url=None)
    elif message.text and message.text.strip().startswith("http"):
        await state.update_data(resume_file_id=None, resume_url=message.text.strip())
    else:
        return await safe_send(message.bot, message.chat.id, q("resume_invalid"))

    data = await state.get_data()
    update_application(data["app_id"], data)
    await safe_send(message.bot, message.chat.id, q("contact"))
    await state.set_state(ApplicationForm.waiting_for_contact)


# ─── CONTACT ──────────────────────────────────────────────────────────────────

@router.message(ApplicationForm.waiting_for_contact)
async def handle_contact(message: Message, state: FSMContext):
    await state.update_data(contact=(message.text or "").strip())
    save_partial_candidate(message.from_user.id, await state.get_data())
    await safe_send(message.bot, message.chat.id, q("location"))
    await state.set_state(ApplicationForm.waiting_for_location)


# ─── LOCATION ─────────────────────────────────────────────────────────────────

@router.message(ApplicationForm.waiting_for_location)
async def handle_location(message: Message, state: FSMContext):
    await state.update_data(location=(message.text or "").strip())
    save_partial_candidate(message.from_user.id, await state.get_data())
    await safe_send(message.bot, message.chat.id, q("age"))
    await state.set_state(ApplicationForm.waiting_for_age)


# ─── AGE ──────────────────────────────────────────────────────────────────────

@router.message(ApplicationForm.waiting_for_age)
async def handle_age(message: Message, state: FSMContext):
    match = re.search(r"\d+", message.text or "")
    if not match:
        return await safe_send(message.bot, message.chat.id, q("age_invalid"))
    age = int(match.group())
    if not (14 <= age <= 80):
        return await safe_send(message.bot, message.chat.id, q("age_invalid"))

    await state.update_data(age=age)
    save_partial_candidate(message.from_user.id, await state.get_data())
    await safe_send(message.bot, message.chat.id, q("languages"))
    await state.set_state(ApplicationForm.waiting_for_languages)


# ─── LANGUAGES ────────────────────────────────────────────────────────────────

@router.message(ApplicationForm.waiting_for_languages)
async def handle_languages(message: Message, state: FSMContext):
    await state.update_data(languages=(message.text or "").strip())
    save_partial_candidate(message.from_user.id, await state.get_data())
    await safe_send(message.bot, message.chat.id, q("experience"))
    await state.set_state(ApplicationForm.waiting_for_experience)


# ─── EXPERIENCE ───────────────────────────────────────────────────────────────

@router.message(ApplicationForm.waiting_for_experience)
async def handle_experience(message: Message, state: FSMContext):
    await state.update_data(experience=(message.text or "").strip())
    save_partial_candidate(message.from_user.id, await state.get_data())
    await safe_send(message.bot, message.chat.id, q("salary"))
    await state.set_state(ApplicationForm.waiting_for_salary)


# ─── SALARY ───────────────────────────────────────────────────────────────────

@router.message(ApplicationForm.waiting_for_salary)
async def handle_salary(message: Message, state: FSMContext):
    match = re.search(r"\d+", message.text or "")
    if not match:
        return await safe_send(message.bot, message.chat.id, q("salary_invalid"))

    salary = int(match.group())
    await state.update_data(salary_amount=salary, salary_currency=DEFAULT_CURRENCY)
    save_partial_candidate(message.from_user.id, await state.get_data())
    await safe_send(message.bot, message.chat.id, q("start_date"))
    await state.set_state(ApplicationForm.waiting_for_start_date)


# ─── START DATE ───────────────────────────────────────────────────────────────

@router.message(ApplicationForm.waiting_for_start_date)
async def handle_start_date(message: Message, state: FSMContext):
    await state.update_data(start_date=(message.text or "").strip())
    save_partial_candidate(message.from_user.id, await state.get_data())
    await safe_send(message.bot, message.chat.id, q("work_type"))
    await state.set_state(ApplicationForm.waiting_for_work_type)


# ─── WORK TYPE — финальный шаг ────────────────────────────────────────────────

@router.message(ApplicationForm.waiting_for_work_type)
async def handle_work_type(message: Message, state: FSMContext):
    await state.update_data(work_type=(message.text or "").strip())
    data = await state.get_data()

    candidate_fields = {
        "full_name", "consent", "contact", "location", "age",
        "languages", "experience", "salary_amount", "salary_currency",
        "start_date", "work_type",
    }

    # Autoreject + финальный статус
    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(tg_id=message.from_user.id).first()
        if not candidate:
            return
        for k, v in data.items():
            if k in candidate_fields:
                setattr(candidate, k, v)
        rejected = check_autoreject(session, candidate)
        candidate.status = "rejected" if rejected else "new"
        session.commit()

    if rejected:
        await safe_send(message.bot, message.chat.id, q("form_rejected"))
        await state.clear()
        return

    await safe_send(message.bot, message.chat.id, q("form_complete"))

    # Собираем данные для уведомления HR
    app_id = data.get("app_id")
    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(tg_id=message.from_user.id).first()
        if not candidate:
            return
        app = session.get(Application, app_id) if app_id else None
        vacancy_title  = ""
        resume_file_id = None
        resume_url     = None
        if app:
            resume_file_id = app.resume_file_id
            resume_url     = app.resume_url
            if app.vacancy_id:
                v = session.query(Vacancy).filter_by(id=app.vacancy_id).first()
                if v:
                    vacancy_title = v.title
        candidate_id = candidate.id
        session.expunge_all()

    # AI summary
    ai_summary = await generate_candidate_summary(
        data, vacancy_title,
        bot=message.bot,
        resume_file_id=resume_file_id,
    )
    print(f"Generated summary: {ai_summary!r}")
    logger.info(f"Generated summary: {ai_summary!r}")

    if ai_summary:
        with SessionLocal() as session:
            candidate = session.query(Candidate).filter_by(tg_id=message.from_user.id).first()
            if candidate:
                candidate.ai_summary = ai_summary
                session.commit()
                logger.info(f"AI summary saved for candidate {candidate.id}")
            else:
                logger.warning(f"Candidate not found by tg_id={message.from_user.id} — summary not saved")

    # Уведомление HR
    currency = data.get("salary_currency", DEFAULT_CURRENCY)
    salary   = data.get("salary_amount")
    salary_str = f"{salary:,} {currency}" if salary else "—"

    base_info = (
        f"🆕 New candidate\n"
        f"👤 {data.get('full_name', '—')}\n"
        + (f"💼 {vacancy_title}\n" if vacancy_title else "")
        + f"🎂 {data.get('age', '—')}\n"
        + f"💰 {salary_str}\n"
        + f"🌐 {data.get('languages', '—')}\n"
        + f"📍 {data.get('location', '—')}"
    )
    ai_block = f"\n\n🤖 AI summary:\n{ai_summary}" if ai_summary else ""

    resume_row = []
    if resume_file_id:
        resume_row = [InlineKeyboardButton(text="📄 Resume", callback_data=f"resume:{candidate_id}")]
    elif resume_url:
        resume_row = [InlineKeyboardButton(text="📄 Resume (link)", url=resume_url)]

    rows = [
        [InlineKeyboardButton(text="✅ Invite",   callback_data=f"invite:{candidate_id}")],
        [InlineKeyboardButton(text="❌ Reject",   callback_data=f"reject:{candidate_id}")],
        [InlineKeyboardButton(text="❓ Clarify",  callback_data=f"request_info:{candidate_id}")],
    ]
    if resume_row:
        rows.append(resume_row)

    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    for admin_id in ADMIN_IDS:
        await safe_send(message.bot, admin_id, base_info + ai_block, reply_markup=keyboard)

    await state.clear()