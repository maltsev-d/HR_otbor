from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db.session import SessionLocal
from db.models import Candidate, Interview, Application, HRMessage
from datetime import datetime
import logging

router = Router()

DATETIME_FORMATS = [
    "%d.%m.%y %H:%M",
    "%d.%m.%Y %H:%M",
    "%d.%m %H:%M",
]


def parse_datetime(text: str) -> datetime | None:
    text = text.strip()
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


class InterviewForm(StatesGroup):
    waiting_for_datetime = State()


class ClarificationHRForm(StatesGroup):
    waiting_for_hr_message = State()


class ClarificationForm(StatesGroup):
    waiting_for_candidate_reply = State()


# =========================
# РЕЗЮМЕ — отправить файл HR
# =========================
@router.callback_query(F.data.startswith("resume:"))
async def handle_resume(callback: CallbackQuery):
    candidate_id = int(callback.data.split(":")[1])

    with SessionLocal() as session:
        app = session.query(Application).filter_by(candidate_id=candidate_id).first()
        if not app:
            await callback.answer("Резюме не найдено", show_alert=True)
            return
        file_id  = app.resume_file_id
        file_url = app.resume_url

    if file_id:
        try:
            await callback.message.bot.send_document(callback.from_user.id, file_id)
            await callback.answer()
        except Exception:
            logging.exception(f"Не удалось отправить резюме candidate_id={candidate_id}")
            await callback.answer("Не удалось отправить файл", show_alert=True)
    elif file_url:
        await callback.message.answer(f"📄 Резюме (ссылка): {file_url}")
        await callback.answer()
    else:
        await callback.answer("Файл резюме недоступен", show_alert=True)


# =========================
# ПРИГЛАСИТЬ НА СОБЕС
# =========================
@router.callback_query(F.data.startswith("invite:"))
async def handle_invite(callback: CallbackQuery, state: FSMContext):
    candidate_id = int(callback.data.split(":")[1])
    await state.set_state(InterviewForm.waiting_for_datetime)
    await state.update_data(candidate_id=candidate_id, hr_id=callback.from_user.id)
    await callback.message.answer(
        "Введите дату и время собеседования:\n"
        "Форматы: <code>12.07.25 15:00</code> или <code>12.07.2025 15:00</code>"
    )
    await callback.answer()


@router.message(InterviewForm.waiting_for_datetime)
async def receive_datetime(message: Message, state: FSMContext):
    interview_dt = parse_datetime(message.text or "")
    if not interview_dt:
        return await message.answer(
            "Не могу распознать дату. Попробуй в формате: <code>12.07.25 15:00</code>"
        )

    data = await state.get_data()
    candidate_id = data["candidate_id"]

    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(id=candidate_id).first()
        if not candidate:
            await state.clear()
            return await message.answer("Кандидат не найден")

        tg_id     = candidate.tg_id
        full_name = candidate.full_name or "Кандидат"

        # Если интервью уже есть — обновляем, иначе создаём
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

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_interview:{candidate_id}"),
        InlineKeyboardButton(text="❌ Отказаться",  callback_data=f"decline_interview:{candidate_id}"),
    ]])

    dt_str = interview_dt.strftime("%d.%m.%Y в %H:%M")

    try:
        await message.bot.send_message(
            tg_id,
            f"👋 Привет, {full_name}!\n\n"
            f"📅 Вас приглашают на собеседование:\n"
            f"<b>{dt_str}</b>\n\nПодтвердите участие:",
            reply_markup=keyboard,
        )
    except Exception:
        logging.exception(f"Не удалось отправить приглашение tg_id={tg_id}")

    await message.answer(f"📨 Приглашение отправлено. Собеседование: {dt_str}")
    await state.clear()


# =========================
# КАНДИДАТ ПОДТВЕРДИЛ
# =========================
@router.callback_query(F.data.startswith("confirm_interview:"))
async def confirm_interview(callback: CallbackQuery):
    candidate_id = int(callback.data.split(":")[1])
    dt_str = ""

    with SessionLocal() as session:
        interview = session.query(Interview).filter_by(candidate_id=candidate_id).first()
        candidate = session.query(Candidate).filter_by(id=candidate_id).first()

        if interview:
            interview.confirmed = True
            if interview.scheduled_at:
                dt_str = interview.scheduled_at.strftime("%d.%m.%Y в %H:%M")

        if candidate:
            candidate.status = "confirmed"
            full_name = candidate.full_name or f"ID {candidate_id}"

        session.commit()

    await callback.message.answer(
        "✅ Спасибо! Вы подтвердили участие в собеседовании."
        + (f"\n📅 Ждём вас {dt_str}" if dt_str else "")
    )

    from config.settings import ADMIN_IDS
    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                admin_id,
                f"✅ Кандидат <b>{full_name}</b> подтвердил собеседование"
                + (f" ({dt_str})" if dt_str else "") + "."
            )
        except Exception:
            logging.exception(f"Не удалось уведомить HR admin_id={admin_id}")

    await callback.answer()


# =========================
# КАНДИДАТ ОТКАЗАЛСЯ
# =========================
@router.callback_query(F.data.startswith("decline_interview:"))
async def decline_interview(callback: CallbackQuery):
    candidate_id = int(callback.data.split(":")[1])
    full_name = ""
    dt_str = ""

    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(id=candidate_id).first()
        interview = session.query(Interview).filter_by(candidate_id=candidate_id).first()

        if candidate:
            candidate.status = "declined"
            full_name = candidate.full_name or f"ID {candidate_id}"

        if interview:
            interview.declined = True
            if interview.scheduled_at:
                dt_str = interview.scheduled_at.strftime("%d.%m.%Y в %H:%M")

        session.commit()

    await callback.message.answer("❌ Вы отказались от собеседования. Спасибо за отклик!")

    from config.settings import ADMIN_IDS
    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                admin_id,
                f"❌ Кандидат <b>{full_name}</b> отказался от собеседования"
                + (f" ({dt_str})" if dt_str else "") + "."
            )
        except Exception:
            logging.exception(f"Не удалось уведомить HR admin_id={admin_id}")

    await callback.answer()


# =========================
# ОТКАЗАТЬ КАНДИДАТУ
# =========================
@router.callback_query(F.data.startswith("reject:"))
async def handle_reject(callback: CallbackQuery):
    candidate_id = int(callback.data.split(":")[1])

    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(id=candidate_id).first()
        if not candidate:
            await callback.answer("Кандидат не найден")
            return
        tg_id = candidate.tg_id
        candidate.status = "rejected"
        session.commit()

    try:
        await callback.message.bot.send_message(
            tg_id,
            "😔 Спасибо за отклик, но по данной позиции мы не можем продолжить с вами процесс."
        )
    except Exception:
        logging.exception(f"Не удалось отправить отказ tg_id={tg_id}")

    await callback.message.answer("Кандидату отправлен отказ.")
    await callback.answer()


# =========================
# ЗАПРОСИТЬ ДОП.ИНФО — шаг 1
# =========================
@router.callback_query(F.data.startswith("request_info:"))
async def handle_request_info(callback: CallbackQuery, state: FSMContext):
    candidate_id = int(callback.data.split(":")[1])

    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(id=candidate_id).first()
        if not candidate:
            await callback.answer("Кандидат не найден")
            return
        tg_id     = candidate.tg_id
        full_name = candidate.full_name or f"ID {candidate_id}"

    await state.set_state(ClarificationHRForm.waiting_for_hr_message)
    await state.update_data(candidate_id=candidate_id, candidate_tg_id=tg_id, hr_id=callback.from_user.id)

    await callback.message.answer(
        f"✏️ Введите сообщение для кандидата <b>{full_name}</b>:\n"
        f"(оно будет отправлено ему в Telegram)"
    )
    await callback.answer()


# =========================
# ЗАПРОСИТЬ ДОП.ИНФО — шаг 2
# =========================
@router.message(ClarificationHRForm.waiting_for_hr_message)
async def send_hr_message_to_candidate(message: Message, state: FSMContext):
    data             = await state.get_data()
    candidate_tg_id  = data.get("candidate_tg_id")
    candidate_id     = data.get("candidate_id")
    hr_id            = data.get("hr_id")

    try:
        await message.bot.send_message(
            candidate_tg_id,
            f"📩 Сообщение от HR-менеджера:\n\n{message.text}\n\nВы можете ответить прямо в этот чат."
        )

        # Сохраняем вопрос в HRMessage, answer пока null
        with SessionLocal() as session:
            session.add(HRMessage(
                candidate_id=candidate_id,
                hr_tg_id=hr_id,
                question=message.text,
            ))
            session.commit()

        await message.answer("✅ Сообщение отправлено кандидату. Ответ придёт сюда.")

    except Exception:
        logging.exception(f"Не удалось отправить сообщение кандидату tg_id={candidate_tg_id}")
        await message.answer("❌ Не удалось отправить сообщение кандидату.")

    await state.clear()


# =========================
# ОТВЕТ КАНДИДАТА → пересылаем HR
# =========================
@router.message(lambda m: True)
async def candidate_free_reply(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        return

    tg_id = message.from_user.id

    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(tg_id=tg_id).first()
        if not candidate:
            return

        # Ищем последний вопрос без ответа
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

        # Сохраняем ответ
        pending.answer = message.text
        session.commit()

    try:
        await message.bot.send_message(
            hr_id,
            f"📩 Ответ от кандидата <b>{full_name}</b>:\n\n{message.text}"
        )
        await message.answer("✅ Ваш ответ отправлен HR-менеджеру.")
    except Exception:
        logging.exception(f"Не удалось переслать ответ HR hr_id={hr_id}")
        await message.answer("❌ Не удалось доставить ответ. Попробуйте позже.")


# =========================
# FLASK — подтверждение / отказ
# =========================
@router.callback_query(F.data.startswith("flask_confirm:"))
async def flask_confirm_interview(callback: CallbackQuery):
    tg_id = int(callback.data.split(":")[1])
    full_name = ""
    dt_str = ""

    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(tg_id=tg_id).first()
        if not candidate:
            await callback.answer("Кандидат не найден")
            return

        full_name = candidate.full_name or f"tg_id={tg_id}"
        candidate.status = "confirmed"

        interview = session.query(Interview).filter_by(candidate_id=candidate.id).first()
        if interview:
            interview.confirmed = True
            if interview.scheduled_at:
                dt_str = interview.scheduled_at.strftime("%d.%m.%Y в %H:%M")

        session.commit()

    await callback.message.answer(
        "✅ Спасибо! Вы подтвердили участие в собеседовании."
        + (f"\n📅 Ждём вас {dt_str}" if dt_str else "")
    )

    from config.settings import ADMIN_IDS
    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                admin_id,
                f"✅ Кандидат <b>{full_name}</b> подтвердил собеседование"
                + (f" ({dt_str})" if dt_str else "") + "."
            )
        except Exception:
            logging.exception(f"Не удалось уведомить HR admin_id={admin_id}")

    await callback.answer()


@router.callback_query(F.data.startswith("flask_decline:"))
async def flask_decline_interview(callback: CallbackQuery):
    tg_id = int(callback.data.split(":")[1])
    full_name = ""
    dt_str = ""

    with SessionLocal() as session:
        candidate = session.query(Candidate).filter_by(tg_id=tg_id).first()
        if not candidate:
            await callback.answer("Кандидат не найден")
            return

        full_name        = candidate.full_name or f"tg_id={tg_id}"
        candidate.status = "declined"

        interview = session.query(Interview).filter_by(candidate_id=candidate.id).first()
        if interview:
            interview.declined = True
            if interview.scheduled_at:
                dt_str = interview.scheduled_at.strftime("%d.%m.%Y в %H:%M")

        session.commit()

    await callback.message.answer("❌ Вы отказались от собеседования. Спасибо за отклик!")

    from config.settings import ADMIN_IDS
    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                admin_id,
                f"❌ Кандидат <b>{full_name}</b> отказался от собеседования"
                + (f" ({dt_str})" if dt_str else "") + "."
            )
        except Exception:
            logging.exception(f"Не удалось уведомить HR admin_id={admin_id}")

    await callback.answer()