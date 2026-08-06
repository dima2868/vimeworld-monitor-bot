import asyncio
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command, or_f
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from config import YOUTUBERS, CREATOR
import checker
import database as db
import keyboards

logger = logging.getLogger(__name__)

router = Router()

# Store active live update tasks: chat_id -> asyncio.Task
active_live_tasks = {}

def format_status_msg(info: dict, custom_title: str = None) -> str:
    """Formats player info into a clean Telegram HTML message."""
    title = custom_title or info['nickname']
    
    if info['is_online']:
        status_icon = "🟢 <b>В СЕТИ</b>"
        if info.get('game'):
            status_icon += f" (Режим: <code>{info['game']}</code>)"
    else:
        status_icon = "🔴 <b>НЕ В СЕТИ</b>"
    
    text = f"<b>{title}</b> (<code>{info['nickname']}</code>)\n\n"
    text += f"Статус: {status_icon}\n"
    if info.get('level') is not None:
        text += f"Уровень: <b>{info['level']}</b>\n"
    if info.get('rank'):
        text += f"Ранг: <b>{info['rank']}</b>\n"
        
    text += f"\n🔗 <a href='{info['url']}'>Открыть профиль на VimeWorld</a>"
    return text

async def generate_live_status_text() -> str:
    """Generates live status text for YouTubers (excluding creator)."""
    lol_info = await checker.fetch_player_status(YOUTUBERS["MrLalalashkaXXL"]["nick"])
    fix_info = await checker.fetch_player_status(YOUTUBERS["F1xPlay_"]["nick"])

    text = "📊 <b>Онлайн ютуберов на VimeWorld (Live ⚡):</b>\n\n"
    
    # Lololoshka
    if lol_info['is_online']:
        lol_icon = f"🟢 <b>В СЕТИ</b> (Режим: <code>{lol_info['game']}</code>)" if lol_info.get('game') else "🟢 <b>В СЕТИ</b>"
    else:
        lol_icon = "🔴 <b>Не в сети</b>"
    text += f"🎬 <b>Лололошка</b> (<code>{lol_info['nickname']}</code>): {lol_icon}\n"
    
    # FixPlay
    if fix_info['is_online']:
        fix_icon = f"🟢 <b>В СЕТИ</b> (Режим: <code>{fix_info['game']}</code>)" if fix_info.get('game') else "🟢 <b>В СЕТИ</b>"
    else:
        fix_icon = "🔴 <b>Не в сети</b>"
    text += f"🎮 <b>Фиксплей</b> (<code>{fix_info['nickname']}</code>): {fix_icon}\n\n"
    
    now_str = datetime.now().strftime("%H:%M:%S")
    text += f"⚡ <i>Live авто-обновление (каждую сек)...</i>\n"
    text += f"🕒 <i>Обновлено: {now_str}</i>"
    
    return text

def get_live_status_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for live status message."""
    keyboard = [
        [
            InlineKeyboardButton(text="🔄 Обновить сейчас", callback_data="refresh_live_status"),
            InlineKeyboardButton(text="⏹ Стоп", callback_data="stop_live_status")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def live_update_loop(chat_id: int, message_id: int, bot):
    """Background task to continuously edit and update status message live indefinitely every 1 second."""
    try:
        while True:
            await asyncio.sleep(1)
            try:
                new_text = await generate_live_status_text()
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=new_text,
                    reply_markup=get_live_status_keyboard(),
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
            except TelegramBadRequest as e:
                err_msg = str(e).lower()
                if "message is not modified" in err_msg:
                    pass
                elif "message to edit not found" in err_msg or "message can't be edited" in err_msg or "chat not found" in err_msg:
                    logger.info(f"Stopping live update loop for chat {chat_id}: message deleted or unavailable.")
                    break
                else:
                    logger.warning(f"TelegramBadRequest in live update loop for chat {chat_id}: {e}")
            except Exception as e:
                logger.warning(f"Temporary error in live update loop for chat {chat_id}: {e}. Retrying...")
    except asyncio.CancelledError:
        pass
    finally:
        active_live_tasks.pop(chat_id, None)

async def generate_monitoring_text(user_id: int) -> str:
    """Generates clear monitoring status text for user."""
    subs = await db.get_user_subscriptions(user_id)
    
    lol_active = "MrLalalashkaXXL" in subs
    fix_active = "F1xPlay_" in subs
    
    if lol_active and fix_active:
        overall_status = "🟢 <b>Мониторинг полностью ВКЛЮЧЕН</b> (Лололошка + Фиксплей)"
    elif lol_active or fix_active:
        active_name = "Лололошка" if lol_active else "Фиксплей"
        overall_status = f"🟡 <b>Мониторинг ВКЛЮЧЕН частично</b> (только {active_name})"
    else:
        overall_status = "🔴 <b>Мониторинг ВЫКЛЮЧЕН</b>"

    text = (
        f"🔔 <b>Управление мониторингом онлайна</b>\n\n"
        f"Текущее состояние: {overall_status}\n\n"
        "Нажимай на кнопки ниже, чтобы переключать уведомления для ютуберов:"
    )
    return text

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handler for /start command."""
    await db.add_user(message.from_user.id)
    
    welcome_text = (
        "👋 <b>Привет! Я бот-мониторинг онлайна на VimeWorld!</b>\n\n"
        "Я каждые 2 секунды отслеживаю сервер и оперативно сообщаю, когда ютуберы заходят в сеть:\n"
        "• 🎬 <b>Лололошка</b> (<code>MrLalalashkaXXL</code>)\n"
        "• 🎮 <b>Фиксплей</b> (<code>F1xPlay_</code>)\n\n"
        "Выбери нужный раздел на клавиатуре ниже или включи авто-мониторинг!"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=keyboards.get_main_keyboard(),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@router.message(F.text.contains("Лололошка"))
async def handle_lololoshka(message: Message):
    """Checks Lololoshka status."""
    info = await checker.fetch_player_status(YOUTUBERS["MrLalalashkaXXL"]["nick"])
    msg_text = format_status_msg(info, custom_title="🎬 Ютубер Лололошка")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🌐 Профиль VimeWorld", url=info['url'])
    ]])
    
    await message.answer(msg_text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)

@router.message(F.text.contains("Фиксплей"))
async def handle_fixplay(message: Message):
    """Checks FixPlay status."""
    info = await checker.fetch_player_status(YOUTUBERS["F1xPlay_"]["nick"])
    msg_text = format_status_msg(info, custom_title="🎮 Ютубер Фиксплей")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🌐 Профиль VimeWorld", url=info['url'])
    ]])
    
    await message.answer(msg_text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)

@router.message(F.text.contains("Общий статус"))
async def handle_all_status(message: Message):
    """Checks all YouTubers status with live auto-updating message."""
    chat_id = message.chat.id
    
    if chat_id in active_live_tasks:
        active_live_tasks[chat_id].cancel()
        
    initial_text = await generate_live_status_text()
    sent_msg = await message.answer(
        initial_text,
        reply_markup=get_live_status_keyboard(),
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    
    task = asyncio.create_task(live_update_loop(chat_id, sent_msg.message_id, message.bot))
    active_live_tasks[chat_id] = task

@router.callback_query(F.data == "refresh_live_status")
async def cb_refresh_live_status(callback: CallbackQuery):
    """Manual trigger to refresh live status message."""
    try:
        new_text = await generate_live_status_text()
        await callback.message.edit_text(
            new_text,
            reply_markup=get_live_status_keyboard(),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        await callback.answer("🔄 Статус обновлен!")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("Статус актуален")
        else:
            await callback.answer()

@router.callback_query(F.data == "stop_live_status")
async def cb_stop_live_status(callback: CallbackQuery):
    """Stops live auto-updating for status message."""
    chat_id = callback.message.chat.id
    if chat_id in active_live_tasks:
        active_live_tasks[chat_id].cancel()
        active_live_tasks.pop(chat_id, None)
        
    now_str = datetime.now().strftime("%H:%M:%S")
    lol_info = await checker.fetch_player_status(YOUTUBERS["MrLalalashkaXXL"]["nick"])
    fix_info = await checker.fetch_player_status(YOUTUBERS["F1xPlay_"]["nick"])
    
    text = "📊 <b>Онлайн ютуберов на VimeWorld:</b>\n\n"
    text += f"🎬 <b>Лололошка</b> (<code>MrLalalashkaXXL</code>): {'🟢 <b>В СЕТИ</b>' if lol_info['is_online'] else '🔴 <b>Не в сети</b>'}\n"
    text += f"🎮 <b>Фиксплей</b> (<code>F1xPlay_</code>): {'🟢 <b>В СЕТИ</b>' if fix_info['is_online'] else '🔴 <b>Не в сети</b>'}\n\n"
    text += f"⏹ <i>Авто-обновление остановлено ({now_str}).</i>"
    
    await callback.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer("⏹ Авто-обновление остановлено")

@router.message(or_f(Command("monitoring"), F.text.contains("Мониторинг"), F.text.contains("мониторинг")))
async def handle_monitoring(message: Message):
    """Shows monitoring menu with toggle controls."""
    user_id = message.from_user.id
    await db.add_user(user_id)
    text = await generate_monitoring_text(user_id)
    kb = await keyboards.get_monitoring_inline_keyboard(user_id)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.message(F.text.contains("Создатель"))
async def handle_creator(message: Message):
    """Shows creator info with live VimeWorld status."""
    info = await checker.fetch_player_status(CREATOR["nick"])
    
    if info['is_online']:
        status_icon = "🟢 <b>В СЕТИ</b>"
        if info.get('game'):
            status_icon += f" (Режим: <code>{info['game']}</code>)"
    else:
        status_icon = "🔴 <b>НЕ В СЕТИ</b>"
        
    text = (
        f"👑 <b>Создатель бота:</b> <a href='{CREATOR['url']}'>{CREATOR['name']}</a>\n\n"
        f"Текущий статус на VimeWorld: {status_icon}\n"
    )
    if info.get('level') is not None:
        text += f"Уровень: <b>{info['level']}</b>\n"
    if info.get('rank'):
        text += f"Ранг: <b>{info['rank']}</b>\n"
        
    text += f"\n🔗 <a href='{CREATOR['url']}'>Ссылка на профиль VimeWorld</a>"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👑 Профиль Создателя на VimeWorld", url=CREATOR['url'])
    ]])
    
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)

# Callback handlers for monitoring inline keyboard
@router.callback_query(F.data.startswith("toggle_"))
async def cb_toggle(callback: CallbackQuery):
    nick = callback.data.replace("toggle_", "")
    user_id = callback.from_user.id
    await db.add_user(user_id)
    
    is_sub = await db.is_subscribed(user_id, nick)
    if is_sub:
        await db.unsubscribe_user(user_id, nick)
        await callback.answer("🔴 Мониторинг отключен!")
    else:
        await db.subscribe_user(user_id, nick)
        await callback.answer("🟢 Мониторинг включен!")
        
    text = await generate_monitoring_text(user_id)
    kb = await keyboards.get_monitoring_inline_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@router.callback_query(F.data == "enable_all")
async def cb_enable_all(callback: CallbackQuery):
    user_id = callback.from_user.id
    await db.add_user(user_id)
    
    for nick in YOUTUBERS.keys():
        await db.subscribe_user(user_id, nick)
    await callback.answer("🟢 Мониторинг всех ютуберов ВКЛЮЧЕН!")
    
    text = await generate_monitoring_text(user_id)
    kb = await keyboards.get_monitoring_inline_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@router.callback_query(F.data == "disable_all")
async def cb_disable_all(callback: CallbackQuery):
    user_id = callback.from_user.id
    await db.add_user(user_id)
    
    for nick in YOUTUBERS.keys():
        await db.unsubscribe_user(user_id, nick)
    await callback.answer("🔴 Мониторинг всех ютуберов ВЫКЛЮЧЕН!")
    
    text = await generate_monitoring_text(user_id)
    kb = await keyboards.get_monitoring_inline_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        pass
