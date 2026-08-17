import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db.session import SessionLocal
from db.models import Candidate, Interview, Application, HRMessage
from config.questions import q
from config.settings import ADMIN_IDS

router = Router()

DATETIME_FORMATS = ["%d.%m.%y %H:%M", "%d.%m.%Y %H:%M", "%d.%m %H:%M"]


def parse_datetime(text: str) -> datetime | None:
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return None


class InterviewForm(StatesGroup):
    waiting_for_datetime = State()


class ClarificationHRForm(StatesGroup):
    waiting_for_hr_message = State()


# ─── РЕЗЮМЕ → HR ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("resume:"))
async def handle_resume(callback: CallbackQuery):
    candidate_id = int(callback.data.split(":")[1])

    with SessionLocal() as session:
        app = session.query(Application).filter_by(candidate_id=candidate_id).first()
        if not app:
            await callback.answer(q("hr_resume_not_found"), show_alert=True)
            return
        file_id  = app.resume_file_id
        file_url = app.resume_url

    if file_id:
        try:
            await callback.message.bot.send_document(callback.from_user.id, file_id)
            await callback.answer()
        except Exception:
            logging.exception(f"Failed to send resume candidate_id={candidate_id}")
            await callback.answer(q("hr_resume_send_failed"), show_alert=True)
    elif file_url:
        await callback.message.answer(q("hr_resume_link").format(url=file_url))
        await callback.answer()
    else:
        await callback.answer(q("hr_resume_unavailable"), show_alert=True)


# ─── ПРИГЛАСИТЬ НА ИНТЕРВЬЮ ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("invite:"))
async def handle_invite(callback: CallbackQuery, state: FSMContext):
    candidate_id = int(callback.data.split(":")[1])
    await state.set_state(InterviewForm.waiting_for_datetime)
    await state.update_data(candidate_id=candidate_id, hr_id=callback.from_user.id)
    await callback.message.answer(q("hr_invite_input"))
    await callback.answer()


@router.message(InterviewForm.waiting_for_datetime)
async def receive_datetime(message: Message, state: FSMContext):
    interview_dt = parse_datetime(message.text or "")
    if not interview_dt:
        return await message.answer(q("hr_invite_parse_error"))

    data         = await state.get_data()
    candidate_id = data["candidate_id"]

    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(id=candidate_id).first()
        if not candidate:
            await state.clear()
            return await message.answer(q("hr_candidate_not_found"))

        tg_id     = candidate.tg_id
        full_name = candidate.full_name or "Candidate"

        interview = session.query(Interview).filter_by(candidate_id=candidate_id).first()
        if interview:
            interview.scheduled_at      = interview_dt
            interview.confirmed         = False
            interview.declined          = False
            interview.invite_nudge_sent = False
        else:
            interview = Interview(candidate_id=candidate_id, scheduled_at=interview_dt)
            session.add(interview)

        candidate.status = "invited"
        session.commit()

    dt_str   = interview_dt.strftime("%d.%m.%Y %H:%M")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=q("hr_invite_confirm_btn"),
            callback_data=f"confirm_interview:{candidate_id}"
        ),
        InlineKeyboardButton(
            text=q("hr_invite_decline_btn"),
            callback_data=f"decline_interview:{candidate_id}"
        ),
    ]])

    try:
        await message.bot.send_message(
            tg_id,
            q("hr_invite_text").format(name=full_name, dt=dt_str),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except Exception:
        logging.exception(f"Failed to send invite tg_id={tg_id}")

    await message.answer(q("hr_invite_sent").format(dt=dt_str))
    await state.clear()


# ─── КАНДИДАТ ПОДТВЕРДИЛ ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("confirm_interview:"))
async def confirm_interview(callback: CallbackQuery):
    candidate_id = int(callback.data.split(":")[1])
    full_name = ""
    dt_str    = ""

    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(id=candidate_id).first()
        interview = session.query(Interview).filter_by(candidate_id=candidate_id).first()

        if candidate:
            candidate.status = "confirmed"
            full_name = candidate.full_name or f"ID {candidate_id}"
        if interview:
            interview.confirmed = True
            if interview.scheduled_at:
                dt_str = interview.scheduled_at.strftime("%d.%m.%Y %H:%M")
        session.commit()

    see_you = ("\n" + q("hr_confirmed_see_you").format(dt=dt_str)) if dt_str else ""
    await callback.message.answer(q("hr_confirmed_candidate") + see_you)

    dt_part = f" ({dt_str})" if dt_str else ""
    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                admin_id,
                q("hr_candidate_confirmed").format(name=full_name, dt=dt_part),
                parse_mode="HTML",
            )
        except Exception:
            logging.exception(f"Failed to notify HR admin_id={admin_id}")

    await callback.answer()


# ─── КАНДИДАТ ОТКАЗАЛСЯ ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("decline_interview:"))
async def decline_interview(callback: CallbackQuery):
    candidate_id = int(callback.data.split(":")[1])
    full_name = ""
    dt_str    = ""

    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(id=candidate_id).first()
        interview = session.query(Interview).filter_by(candidate_id=candidate_id).first()

        if candidate:
            candidate.status = "declined"
            full_name = candidate.full_name or f"ID {candidate_id}"
        if interview:
            interview.declined = True
            if interview.scheduled_at:
                dt_str = interview.scheduled_at.strftime("%d.%m.%Y %H:%M")
        session.commit()

    await callback.message.answer(q("hr_declined_candidate"))

    dt_part = f" ({dt_str})" if dt_str else ""
    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                admin_id,
                q("hr_candidate_declined").format(name=full_name, dt=dt_part),
                parse_mode="HTML",
            )
        except Exception:
            logging.exception(f"Failed to notify HR admin_id={admin_id}")

    await callback.answer()


# ─── ОТКАЗАТЬ КАНДИДАТУ ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("reject:"))
async def handle_reject(callback: CallbackQuery):
    candidate_id = int(callback.data.split(":")[1])

    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(id=candidate_id).first()
        if not candidate:
            await callback.answer(q("hr_candidate_not_found"))
            return
        tg_id = candidate.tg_id
        candidate.status = "rejected"
        session.commit()

    try:
        await callback.message.bot.send_message(tg_id, q("form_rejected"))
    except Exception:
        logging.exception(f"Failed to send rejection tg_id={tg_id}")

    await callback.message.answer(q("hr_rejection_sent"))
    await callback.answer()


# ─── ЗАПРОС УТОЧНЕНИЯ — шаг 1 ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("request_info:"))
async def handle_request_info(callback: CallbackQuery, state: FSMContext):
    candidate_id = int(callback.data.split(":")[1])

    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(id=candidate_id).first()
        if not candidate:
            await callback.answer(q("hr_candidate_not_found"))
            return
        tg_id     = candidate.tg_id
        full_name = candidate.full_name or f"ID {candidate_id}"

    await state.set_state(ClarificationHRForm.waiting_for_hr_message)
    await state.update_data(candidate_id=candidate_id, candidate_tg_id=tg_id, hr_id=callback.from_user.id)
    await callback.message.answer(
        q("hr_clarify_input").format(name=full_name),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── ЗАПРОС УТОЧНЕНИЯ — шаг 2 ────────────────────────────────────────────────

@router.message(ClarificationHRForm.waiting_for_hr_message)
async def send_hr_message_to_candidate(message: Message, state: FSMContext):
    data            = await state.get_data()
    candidate_tg_id = data.get("candidate_tg_id")
    candidate_id    = data.get("candidate_id")
    hr_id           = data.get("hr_id")

    try:
        await message.bot.send_message(
            candidate_tg_id,
            q("hr_clarify_msg").format(text=message.text),
        )
        with SessionLocal() as session:
            session.add(HRMessage(
                candidate_id=candidate_id,
                hr_tg_id=hr_id,
                question=message.text,
            ))
            session.commit()
        await message.answer(q("hr_msg_sent"))
    except Exception:
        logging.exception(f"Failed to message candidate tg_id={candidate_tg_id}")
        await message.answer(q("hr_msg_failed"))

    await state.clear()


# ─── ОТВЕТ КАНДИДАТА → HR ────────────────────────────────────────────────────

@router.message(lambda m: True)
async def candidate_free_reply(message: Message, state: FSMContext):
    if await state.get_state() is not None:
        return

    tg_id = message.from_user.id

    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(tg_id=tg_id).first()
        if not candidate:
            return

        pending = (
            session.query(HRMessage)
            .filter_by(candidate_id=candidate.id, answer=None)
            .order_by(HRMessage.created_at.desc())
            .first()
        )
        if not pending:
            return

        hr_id     = pending.hr_tg_id
        full_name = candidate.full_name or f"tg_id={tg_id}"
        pending.answer = message.text
        session.commit()

    try:
        await message.bot.send_message(
            hr_id,
            q("hr_candidate_reply").format(name=full_name, text=message.text),
            parse_mode="HTML",
        )
        await message.answer(q("hr_reply_sent"))
    except Exception:
        logging.exception(f"Failed to forward reply hr_id={hr_id}")
        await message.answer(q("hr_reply_failed"))


# ─── FLASK CONFIRM / DECLINE ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("flask_confirm:"))
async def flask_confirm_interview(callback: CallbackQuery):
    tg_id     = int(callback.data.split(":")[1])
    full_name = ""
    dt_str    = ""

    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(tg_id=tg_id).first()
        if not candidate:
            await callback.answer(q("hr_candidate_not_found"))
            return
        full_name        = candidate.full_name or f"tg_id={tg_id}"
        candidate.status = "confirmed"
        interview = session.query(Interview).filter_by(candidate_id=candidate.id).first()
        if interview:
            interview.confirmed = True
            if interview.scheduled_at:
                dt_str = interview.scheduled_at.strftime("%d.%m.%Y %H:%M")
        session.commit()

    see_you = ("\n" + q("hr_confirmed_see_you").format(dt=dt_str)) if dt_str else ""
    await callback.message.answer(q("hr_confirmed_candidate") + see_you)

    dt_part = f" ({dt_str})" if dt_str else ""
    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                admin_id,
                q("hr_candidate_confirmed").format(name=full_name, dt=dt_part),
                parse_mode="HTML",
            )
        except Exception:
            logging.exception(f"Failed to notify HR admin_id={admin_id}")
    await callback.answer()


@router.callback_query(F.data.startswith("flask_decline:"))
async def flask_decline_interview(callback: CallbackQuery):
    tg_id     = int(callback.data.split(":")[1])
    full_name = ""
    dt_str    = ""

    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(tg_id=tg_id).first()
        if not candidate:
            await callback.answer(q("hr_candidate_not_found"))
            return
        full_name        = candidate.full_name or f"tg_id={tg_id}"
        candidate.status = "declined"
        interview = session.query(Interview).filter_by(candidate_id=candidate.id).first()
        if interview:
            interview.declined = True
            if interview.scheduled_at:
                dt_str = interview.scheduled_at.strftime("%d.%m.%Y %H:%M")
        session.commit()

    await callback.message.answer(q("hr_declined_candidate"))

    dt_part = f" ({dt_str})" if dt_str else ""
    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                admin_id,
                q("hr_candidate_declined").format(name=full_name, dt=dt_part),
                parse_mode="HTML",
            )
        except Exception:
            logging.exception(f"Failed to notify HR admin_id={admin_id}")
    await callback.answer()