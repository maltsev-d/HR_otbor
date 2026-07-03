print("[CANDIDATE] import started", flush=True)
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from bot.states.application import ApplicationForm
from bot.services.llm_service import generate_candidate_summary
from config.questions import q
from config.settings import ADMIN_IDS
from db.models import Candidate, Vacancy, Application
from db.session import SessionLocal
import re
print("[CANDIDATE] re ok", flush=True)
import logging
print("[CANDIDATE] logging ok", flush=True)
from aiogram.exceptions import TelegramNetworkError
print("[CANDIDATE] aiogram.exceptions ok", flush=True)
from bot.rag.index import search_vacancies
print("[CANDIDATE] rag ok", flush=True)
from bot.services.autoreject import check_autoreject
print("[CANDIDATE] autoreject ok", flush=True)

router = Router()


# =========================
# DB SAVE
# =========================
def save_partial_candidate(tg_id: int, data: dict, status: str = "draft"):
    candidate_fields = {
        "full_name", "consent", "contact", "location", "age",
        "english_level", "salary_expectation", "start_date", "contract_type",
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
    application_fields = {"resume_file_id", "resume_url"}
    application_data = {k: v for k, v in data.items() if k in application_fields}
    if not application_data:
        return
    with SessionLocal() as session:
        app = session.get(Application, app_id)
        if app:
            for k, v in application_data.items():
                setattr(app, k, v)
            session.commit()


# =========================
# SAFE SEND
# =========================
async def safe_send(bot, chat_id, text, **kwargs):
    try:
        await bot.send_message(chat_id, text, **kwargs)
    except TelegramNetworkError as e:
        logging.error(f"Telegram error {chat_id}: {e}")
    except Exception:
        logging.exception("Send error")


# =========================
# START
# =========================
@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()

    with SessionLocal() as session:
        vacancies = session.query(Vacancy).filter_by(is_active=True, is_featured=True).all()
        vac_list = [(v.id, v.title) for v in vacancies]

    if not vac_list:
        await safe_send(message.bot, message.chat.id, "😔 Активных вакансий пока нет.")
        return

    rows = [
        [InlineKeyboardButton(text=title, callback_data=f"vacancy:{vid}")]
        for vid, title in vac_list
    ]
    rows.append([InlineKeyboardButton(text="🔍 Найти другую вакансию", callback_data="search_vacancy")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    await safe_send(message.bot, message.chat.id, q("vacancy"), reply_markup=keyboard)
    await state.set_state(ApplicationForm.waiting_for_vacancy)


# =========================
# ПОИСК
# =========================
@router.callback_query(ApplicationForm.waiting_for_vacancy, F.data == "search_vacancy")
async def handle_search_button(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "💬 Опишите что ищёте — должность, сферу или условия работы.\n\n"
        "<i>Например: «работа с животными» или «продажи без холодных звонков»</i>",
        parse_mode="HTML",
    )
    await state.set_state(ApplicationForm.waiting_for_search_query)
    await callback.answer()


@router.message(ApplicationForm.waiting_for_search_query)
async def handle_search_query(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    if not query:
        return await safe_send(message.bot, message.chat.id, "Введите текстовый запрос.")

    results = search_vacancies(query, n_results=5)
    if not results:
        await safe_send(message.bot, message.chat.id,
                        "😔 Ничего подходящего не нашлось. Попробуйте описать иначе.")
        return

    rows = [
        [InlineKeyboardButton(
            text=f"{r['title']} ({r['score']:.0%})",
            callback_data=f"vacancy:{r['vacancy_id']}"
        )]
        for r in results
    ]
    await message.answer("🎯 Вот что нашёл:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await state.set_state(ApplicationForm.waiting_for_vacancy)


# =========================
# VACANCY SELECTED
# =========================
@router.callback_query(ApplicationForm.waiting_for_vacancy, F.data.startswith("vacancy:"))
async def handle_vacancy(callback: CallbackQuery, state: FSMContext):
    vacancy_id = int(callback.data.split(":")[1])

    with SessionLocal() as session:
        vacancy = session.query(Vacancy).filter_by(id=vacancy_id, is_active=True).first()
        if not vacancy:
            await callback.answer("Вакансия недоступна", show_alert=True)
            return
        title = vacancy.title

    app_id = save_application(callback.from_user.id, vacancy_id)
    await state.update_data(vacancy_id=vacancy_id, app_id=app_id)

    await callback.message.answer(
        f"✅ Вакансия: <b>{title}</b>\n\n{q('full_name')}",
        parse_mode="HTML",
    )
    await state.set_state(ApplicationForm.waiting_for_full_name)
    await callback.answer()


# =========================
# FULL NAME
# =========================
@router.message(ApplicationForm.waiting_for_full_name)
async def handle_full_name(message: Message, state: FSMContext):
    full_name = (message.text or "").strip()
    if not full_name:
        return await safe_send(message.bot, message.chat.id, "Введите ФИО текстом.")

    first_name = full_name.split()[0]
    await state.update_data(full_name=full_name)
    data = await state.get_data()
    save_partial_candidate(message.from_user.id, data)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да, согласен(а)", callback_data="consent:yes"),
        InlineKeyboardButton(text="❌ Нет",             callback_data="consent:no"),
    ]])
    await safe_send(
        message.bot, message.chat.id,
        f"Приятно познакомиться, {first_name}! 👋\n\n{q('consent')}",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await state.set_state(ApplicationForm.waiting_for_consent)


# =========================
# CONSENT
# =========================
@router.callback_query(ApplicationForm.waiting_for_consent, F.data == "consent:yes")
async def handle_consent_yes(callback: CallbackQuery, state: FSMContext):
    await state.update_data(consent=True)
    data = await state.get_data()
    save_partial_candidate(callback.from_user.id, data)

    await callback.message.answer(q("resume"))
    await state.set_state(ApplicationForm.waiting_for_resume)
    await callback.answer()


@router.callback_query(ApplicationForm.waiting_for_consent, F.data == "consent:no")
async def handle_consent_no(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "😔 Без согласия на обработку персональных данных мы не можем принять вашу анкету.\n\n"
        "Если передумаете — нажмите /start и попробуйте снова."
    )
    await callback.answer()


# =========================
# RESUME
# =========================
@router.message(ApplicationForm.waiting_for_resume)
async def handle_resume(message: Message, state: FSMContext):
    if message.document:
        await state.update_data(resume_file_id=message.document.file_id, resume_url=None)
    elif message.text and message.text.startswith("http"):
        await state.update_data(resume_file_id=None, resume_url=message.text.strip())
    else:
        return await safe_send(message.bot, message.chat.id,
                                "Отправьте файл резюме или ссылку (начинается с http).")

    data = await state.get_data()
    update_application(data["app_id"], data)

    await safe_send(message.bot, message.chat.id, q("contact"))
    await state.set_state(ApplicationForm.waiting_for_contact)


# =========================
# CONTACT
# =========================
@router.message(ApplicationForm.waiting_for_contact)
async def handle_contact(message: Message, state: FSMContext):
    await state.update_data(contact=(message.text or "").strip())
    data = await state.get_data()
    save_partial_candidate(message.from_user.id, data)

    await safe_send(message.bot, message.chat.id, q("location"))
    await state.set_state(ApplicationForm.waiting_for_location)


# =========================
# LOCATION
# =========================
@router.message(ApplicationForm.waiting_for_location)
async def handle_location(message: Message, state: FSMContext):
    await state.update_data(location=(message.text or "").strip())
    data = await state.get_data()
    save_partial_candidate(message.from_user.id, data)

    await safe_send(message.bot, message.chat.id, q("age"))
    await state.set_state(ApplicationForm.waiting_for_age)


# =========================
# AGE
# =========================
@router.message(ApplicationForm.waiting_for_age)
async def handle_age(message: Message, state: FSMContext):
    text = message.text or ""
    match = re.search(r"\d+", text)
    if not match:
        return await safe_send(message.bot, message.chat.id,
                                "Введите возраст числом, например: 25")

    age = int(match.group())
    if not (14 <= age <= 80):
        return await safe_send(message.bot, message.chat.id,
                                "Похоже на опечатку — введите реальный возраст.")

    await state.update_data(age=age)
    data = await state.get_data()
    save_partial_candidate(message.from_user.id, data)

    await safe_send(message.bot, message.chat.id, q("english_level"))
    await state.set_state(ApplicationForm.waiting_for_english)


# =========================
# ENGLISH
# =========================
@router.message(ApplicationForm.waiting_for_english)
async def handle_english(message: Message, state: FSMContext):
    await state.update_data(english_level=(message.text or "").strip())
    data = await state.get_data()
    save_partial_candidate(message.from_user.id, data)

    await safe_send(message.bot, message.chat.id, q("salary"))
    await state.set_state(ApplicationForm.waiting_for_salary)


# =========================
# SALARY
# =========================
@router.message(ApplicationForm.waiting_for_salary)
async def handle_salary(message: Message, state: FSMContext):
    text = message.text or ""
    match = re.search(r"\d+", text)
    if not match:
        return await safe_send(message.bot, message.chat.id,
                                "Введите число, например: 80000")

    salary = int(match.group())
    if salary > 1_000_000:
        return await safe_send(message.bot, message.chat.id,
                                "Похоже на опечатку — введите сумму в рублях.")

    await state.update_data(salary_expectation=salary)
    data = await state.get_data()
    save_partial_candidate(message.from_user.id, data)

    await safe_send(message.bot, message.chat.id, q("start_date"))
    await state.set_state(ApplicationForm.waiting_for_start_date)


# =========================
# START DATE
# =========================
@router.message(ApplicationForm.waiting_for_start_date)
async def handle_start_date(message: Message, state: FSMContext):
    await state.update_data(start_date=(message.text or "").strip())
    data = await state.get_data()
    save_partial_candidate(message.from_user.id, data)

    await safe_send(message.bot, message.chat.id, q("contract_type"))
    await state.set_state(ApplicationForm.waiting_for_contract_type)


# =========================
# CONTRACT TYPE — финальный шаг
# =========================
@router.message(ApplicationForm.waiting_for_contract_type)
async def handle_contract_type(message: Message, state: FSMContext):
    await state.update_data(contract_type=(message.text or "").strip())
    data = await state.get_data()

    candidate_fields = {
        "full_name", "consent", "contact", "location", "age",
        "english_level", "salary_expectation", "start_date", "contract_type",
    }

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
        await safe_send(message.bot, message.chat.id,
                        "😔 Спасибо за отклик, но по данной позиции мы не можем продолжить с вами процесс.")
        await state.clear()
        return

    await safe_send(message.bot, message.chat.id, "✅ Анкета отправлена! Ожидайте обратной связи.")

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
                vacancy = session.query(Vacancy).filter_by(id=app.vacancy_id).first()
                if vacancy:
                    vacancy_title = vacancy.title

        candidate_id = candidate.id
        session.expunge_all()

    ai_summary = await generate_candidate_summary(data, vacancy_title)

    if ai_summary:
        with SessionLocal() as session:
            candidate = session.query(Candidate).filter_by(tg_id=message.from_user.id).first()
            if candidate:
                candidate.ai_summary = ai_summary
                session.commit()

    base_info = (
        f"🆕 Новый кандидат\n"
        f"👤 {data.get('full_name', '—')}\n"
        + (f"💼 {vacancy_title}\n" if vacancy_title else "")
        + f"🎂 {data.get('age', '—')} лет\n"
        + f"💰 {data.get('salary_expectation', '—')} руб.\n"
        f"📍 {data.get('location', '—')}"
    )
    ai_block = f"\n\n🤖 AI-анализ:\n{ai_summary}" if ai_summary else ""

    resume_row = []
    if resume_file_id:
        resume_row = [InlineKeyboardButton(text="📄 Резюме", callback_data=f"resume:{candidate_id}")]
    elif resume_url:
        resume_row = [InlineKeyboardButton(text="📄 Резюме (ссылка)", url=resume_url)]

    rows = [
        [InlineKeyboardButton(text="✅ Интервью", callback_data=f"invite:{candidate_id}")],
        [InlineKeyboardButton(text="❌ Отказ",    callback_data=f"reject:{candidate_id}")],
        [InlineKeyboardButton(text="❓ Уточнить", callback_data=f"request_info:{candidate_id}")],
    ]
    if resume_row:
        rows.append(resume_row)

    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

    for admin_id in ADMIN_IDS:
        await safe_send(message.bot, admin_id, base_info + ai_block, reply_markup=keyboard)

    await state.clear()