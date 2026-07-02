import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN    = os.getenv("BOT_TOKEN")
ADMIN_IDS    = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
DATABASE_URL = os.getenv("DATABASE_URL")

# Корень проекта (на уровень выше config/)
_BASE_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

os.makedirs(RESUME_DIR, exist_ok=True)