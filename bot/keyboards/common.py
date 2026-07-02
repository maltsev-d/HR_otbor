from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_hr_actions_keyboard(candidate_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Пригласить", callback_data=f"invite:{candidate_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отказать", callback_data=f"reject:{candidate_id}"
        ),
        InlineKeyboardButton(
            text="❓ Уточнить", callback_data=f"request:{candidate_id}"
        )
    )
    return builder.as_markup()
