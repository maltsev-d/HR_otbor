import asyncio
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db.session import SessionLocal
from db.models import Candidate, Interview, Application
from bot.states.application import ApplicationForm
from config.questions import q

router = Router()

# =========================
# ИНТЕРВАЛЫ
# =========================
DRAFT_NUDGE_AFTER_HOURS  = 24
INVITE_NUDGE_AFTER_HOURS = 2
CHECK_INTERVAL_SECONDS   = 60 * 30


# =========================
# ВСПОМОГАТЕЛЬНОЕ
# =========================
def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def strip_tz(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None)


# =========================
# ПЛАНИРОВЩИК
# =========================
async def run_scheduler(bot: Bot) -> None:
    logging.info("[NUDGE] Scheduler started")

    while True:
        try:
            await _nudge_drafts(bot)
            await _nudge_pending_invites(bot)
        except Exception:
            logging.exception("[NUDGE] Ошибка в планировщике")

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


# =========================
# 1) БРОШЕННЫЕ АНКЕТЫ
# =========================
async def _nudge_drafts(bot: Bot) -> None:
    threshold = strip_tz(utcnow() - timedelta(hours=DRAFT_NUDGE_AFTER_HOURS))

    with SessionLocal() as session:
        candidates = (
            session.query(Candidate)
            .filter(
                Candidate.status == "draft",
                Candidate.created_at <= threshold,
                Candidate.nudge_sent.is_(False),
            )
            .all()
        )
        rows = [(c.id, c.tg_id) for c in candidates]

    for candidate_id, tg_id in rows:
        try:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✍️ Продолжить заполнение", callback_data="resume_application")]
            ])
            await bot.send_message(
                tg_id,
                "👋 Вы начали заполнять анкету, но не завершили.\n"
                "Осталось буквально пара шагов — нажмите кнопку ниже:",
                reply_markup=keyboard,
            )
            with SessionLocal() as session:
                c = session.query(Candidate).filter_by(id=candidate_id).first()
                if c:
                    c.nudge_sent = True
                    session.commit()

            logging.info(f"[NUDGE] Draft reminder → tg_id={tg_id}")

        except Exception:
            logging.exception(f"[NUDGE] Не удалось отправить draft-напоминание tg_id={tg_id}")


# =========================
# 2) НЕТ ОТВЕТА НА ПРИГЛАШЕНИЕ
# =========================
async def _nudge_pending_invites(bot: Bot) -> None:
    threshold = strip_tz(utcnow() - timedelta(hours=INVITE_NUDGE_AFTER_HOURS))

    with SessionLocal() as session:
        rows_raw = (
            session.query(
                Candidate.id,
                Candidate.tg_id,
                Candidate.full_name,
                Interview.id.label("interview_id"),
                Interview.scheduled_at,
            )
            .join(Interview, Interview.candidate_id == Candidate.id)
            .filter(
                Candidate.status == "invited",
                Interview.confirmed.is_(False),
                Interview.declined.is_(False),
                Interview.invite_nudge_sent.is_(False),
                Interview.scheduled_at <= threshold,
            )
            .all()
        )

    for candidate_id, tg_id, full_name, interview_id, scheduled_at in rows_raw:
        try:
            dt_str = scheduled_at.strftime("%d.%m.%Y в %H:%M") if scheduled_at else ""

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_interview:{candidate_id}"),
                    InlineKeyboardButton(text="❌ Отказаться",  callback_data=f"decline_interview:{candidate_id}"),
                ]
            ])

            await bot.send_message(
                tg_id,
                f"⏰ Напоминаем: вас пригласили на собеседование"
                + (f" <b>{dt_str}</b>" if dt_str else "")
                + ".\n\nПожалуйста, подтвердите или откажитесь:",
                reply_markup=keyboard,
            )

            with SessionLocal() as session:
                interview = session.get(Interview, interview_id)
                if interview:
                    interview.invite_nudge_sent = True
                    session.commit()

            logging.info(f"[NUDGE] Invite reminder → tg_id={tg_id} ({full_name})")

        except Exception:
            logging.exception(f"[NUDGE] Не удалось отправить invite-напоминание tg_id={tg_id}")


# =========================
# РУЧНОЙ ЗАПУСК
# =========================
@router.message(F.text == "/nudge_drafts")
async def manually_trigger_nudge(message: Message):
    await message.answer("⏳ Запускаю напоминания вручную...")
    await _nudge_drafts(message.bot)
    await _nudge_pending_invites(message.bot)
    await message.answer("✅ Готово.")


# =========================
# КНОПКА «ПРОДОЛЖИТЬ» (из напоминания о брошенной анкете)
# =========================

# field в snap → (стейт, индекс в QUESTION_FLOW)
# resume объединён: file_id или url — достаточно любого
RESUME_STEPS = [
    ("vacancy_id",         ApplicationForm.waiting_for_vacancy,       "vacancy"),
    ("full_name",          ApplicationForm.waiting_for_full_name,     "full_name"),
    ("consent",            ApplicationForm.waiting_for_consent,       "consent"),
    ("resume",             ApplicationForm.waiting_for_resume,        "resume"),
    ("contact",            ApplicationForm.waiting_for_contact,       "contact"),
    ("location",           ApplicationForm.waiting_for_location,      "location"),
    ("age",                 ApplicationForm.waiting_for_age,           "age"),
    ("english_level",      ApplicationForm.waiting_for_english,       "english_level"),
    ("salary_expectation", ApplicationForm.waiting_for_salary,        "salary"),
    ("start_date",         ApplicationForm.waiting_for_start_date,    "start_date"),
    ("contract_type",      ApplicationForm.waiting_for_contract_type, "contract_type"),
]


@router.callback_query(F.data == "resume_application")
async def resume_application(callback: CallbackQuery, state: FSMContext):

    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(tg_id=callback.from_user.id).first()
        if not candidate:
            await callback.answer("Анкета не найдена", show_alert=True)
            return

        candidate.nudge_sent = False
        session.commit()

        app = session.query(Application).filter_by(candidate_id=candidate.id).first()

        snap = {
            "vacancy_id":         app.vacancy_id if app else None,
            "full_name":          candidate.full_name,
            "consent":            candidate.consent,
            "resume":             (app.resume_file_id or app.resume_url) if app else None,
            "contact":            candidate.contact,
            "location":           candidate.location,
            "age":                candidate.age,
            "english_level":      candidate.english_level,
            "salary_expectation": candidate.salary_expectation,
            "start_date":         candidate.start_date,
            "contract_type":      candidate.contract_type,
        }

    for field, next_state, q_key in RESUME_STEPS:
        if not snap.get(field):
            await state.set_state(next_state)
            await callback.message.answer(q(q_key))
            await callback.answer()
            return

    await callback.message.answer("👍 Вы уже всё заполнили!")
    await callback.answer()