import requests
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


def send_telegram_message(chat_id: int, text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print("Ошибка отправки сообщения:", e)


def send_interview_invite(chat_id: int, interview_time: object) -> None:
    """
    Отправляет кандидату приглашение на собеседование с кнопками.
    flask_confirm / flask_decline резолвятся в боте по tg_id.
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    dt_str = interview_time.strftime("%d.%m.%Y в %H:%M")

    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Подтвердить", "callback_data": f"flask_confirm:{chat_id}"},
            {"text": "❌ Отказаться",  "callback_data": f"flask_decline:{chat_id}"},
        ]]
    }
    text = (
        f"📅 Вас приглашают на собеседование:\n"
        f"<b>{dt_str}</b>\n\n"
        f"Подтвердите участие:"
    )
    try:
        requests.post(url, json={
            "chat_id": chat_id, "text": text,
            "parse_mode": "HTML", "reply_markup": keyboard
        }, timeout=10)
    except Exception as e:
        print("Ошибка отправки приглашения:", e)


def send_resume_to_hr(hr_chat_id: int, file_id: str, candidate_name: str) -> None:
    """
    Пересылает резюме (Telegram file_id) HR-у в личку.
    Вызывается из /candidates/<id>/request-resume.
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    try:
        requests.post(url, json={
            "chat_id": hr_chat_id,
            "document": file_id,
            "caption": f"📎 Резюме кандидата: <b>{candidate_name}</b>",
            "parse_mode": "HTML",
        }, timeout=10)
    except Exception as e:
        print("Ошибка пересылки резюме:", e)