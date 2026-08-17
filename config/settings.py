import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN    = os.getenv("BOT_TOKEN")
ADMIN_IDS    = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
DATABASE_URL = os.getenv("DATABASE_URL")

# Язык бота: ru | en | lo | th
BOT_LANG = os.getenv("BOT_LANG", "en")

# Валюта определяется языком — не спрашиваем у кандидата
LANG_CURRENCY = {
    "ru": "RUB",
    "en": "USD",
    "lo": "LAK",
    "th": "THB",
}
DEFAULT_CURRENCY = LANG_CURRENCY.get(BOT_LANG, "USD")

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))