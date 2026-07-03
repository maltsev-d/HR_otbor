import asyncio
import threading
import os
import time
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from flask import Flask
from bot.handlers import candidate
print("[STARTUP] candidate ok", flush=True)
from bot.handlers import hr_actions
print("[STARTUP] hr_actions ok", flush=True)
from bot.handlers import nudge
print("[STARTUP] nudge ok", flush=True)
from bot.handlers.nudge import run_scheduler
print("[STARTUP] bot.handlers.nudge ok", flush=True)
from admin.app import admin_bp
print("[STARTUP] admin.app ok", flush=True)
from bot.rag.index import rebuild_index
print("[STARTUP] bot.rag.index ok", flush=True)
from config.settings import BOT_TOKEN
print("[STARTUP] config.settings ok", flush=True)
print("[STARTUP] imports end", flush=True)


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
    try:
        print("[FLASK] STARTED")
        app.run(host="0.0.0.0", port=10000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[FLASK] CRASH: {e}")

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
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    time.sleep(2)  # даём Flask подняться до бота
    asyncio.run(main())