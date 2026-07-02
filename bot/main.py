import asyncio
import threading
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from flask import Flask

from config.settings import BOT_TOKEN
from bot.handlers import candidate, hr_actions, nudge
from bot.handlers.nudge import run_scheduler
from admin.app import admin_bp
from bot.rag.index import rebuild_index



# =========================
# FLASK APP
# =========================
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
app.register_blueprint(admin_bp)

# =========================
# FLASK RUN (в отдельном треде)
# =========================
def run_web():
    print("[FLASK] STARTED")
    app.run(host="0.0.0.0", port=10000, debug=False, use_reloader=False)

# =========================
# BOT + SCHEDULER
# =========================
async def main():
    rebuild_index()  # ← сюда, первой строкой

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(candidate.router)
    dp.include_router(hr_actions.router)
    dp.include_router(nudge.router)

    print("[BOT] STARTED")

    await asyncio.gather(
        dp.start_polling(bot),
        run_scheduler(bot),
    )
# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    asyncio.run(main())