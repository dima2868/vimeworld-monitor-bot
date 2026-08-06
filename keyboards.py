from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import YOUTUBERS, CREATOR
import database as db

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Returns main menu reply keyboard."""
    keyboard = [
        [
            KeyboardButton(text="🎬 Лололошка"),
            KeyboardButton(text="🎮 Фиксплей")
        ],
        [
            KeyboardButton(text="📊 Общий статус"),
            KeyboardButton(text="🔔 Настройка мониторинга")
        ],
        [
            KeyboardButton(text=f"👑 Создатель ({CREATOR['name']})")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True
    )

async def get_monitoring_inline_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generates inline keyboard for monitoring subscriptions."""
    subs = await db.get_user_subscriptions(user_id)
    
    lol_sub = "MrLalalashkaXXL" in subs
    fix_sub = "F1xPlay_" in subs

    lol_btn_text = "🎬 Лололошка: 🟢 Включан" if lol_sub else "🎬 Лололошка: 🔴 Выключен"
    fix_btn_text = "🎮 Фиксплей: 🟢 Включен" if fix_sub else "🎮 Фиксплей: 🔴 Выключен"

    keyboard = [
        [
            InlineKeyboardButton(
                text=lol_btn_text,
                callback_data="toggle_MrLalalashkaXXL"
            )
        ],
        [
            InlineKeyboardButton(
                text=fix_btn_text,
                callback_data="toggle_F1xPlay_"
            )
        ],
        [
            InlineKeyboardButton(
                text="🟢 Включить всё",
                callback_data="enable_all"
            ),
            InlineKeyboardButton(
                text="🔴 Выключить всё",
                callback_data="disable_all"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
