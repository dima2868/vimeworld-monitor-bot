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

    lol_status_icon = "🟢 Включен" if lol_sub else "🔴 Выключен"
    fix_status_icon = "🟢 Включен" if fix_sub else "🔴 Выключен"

    keyboard = [
        [
            InlineKeyboardButton(
                text=f"🎬 Лололошка: {lol_status_icon}",
                callback_data="toggle_MrLalalashkaXXL"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🎮 Фиксплей: {fix_status_icon}",
                callback_data="toggle_F1xPlay_"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚡ Мониторить ВСЕХ",
                callback_data="enable_all"
            ),
            InlineKeyboardButton(
                text="❌ Выключить ВСЁ",
                callback_data="disable_all"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
