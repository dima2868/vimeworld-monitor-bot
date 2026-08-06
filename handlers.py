import asyncio
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError
from config import YOUTUBERS, CREATOR, ADMIN_IDS
import checker
import database as db
import keyboards

logger = logging.getLogger(__name__)

# Moscow Timezone (UTC+3)
MSK_TZ = timezone(timedelta(hours=3))

def get_now_msk_str() -> str:
    """Returns current Moscow time formatted as HH:MM:SS."""
    return datetime.now(MSK_TZ).strftime("%H:%M:%S")

router = Router()

def format_status_msg(info: dict, custom_title: str = None) -> str:
    """Formats player info into a clean Telegram HTML message."""
    title = custom_title or info['nickname']
    status_icon = info['status_display']
    
    text = f"<b>{title}</b> (<code>{info['nickname']}</code>)\n\n"
    text += f"Статус: <b>{status_icon}</b>\n"
    if info.get('level') is not None:
        text += f"Уровень: <b>{info['level']}</b>\n"
    if info.get('rank'):
        text += f"Ранг: <b>{info['rank']}</b>\n"
        
    text += f"\n🔗 <a href='{info['url']}'>Открыть профиль на VimeWorld</a>"
    return text

async def generate_monitoring_text(user_id: int) -> str:
    """Generates clear monitoring status text for user."""
    subs = await db.get_user_subscriptions(user_id)
    
    lol_active = "MrLalalashkaXXL" in subs
    fix_active = "F1xPlay_" in subs
    
    if lol_active and fix_active:
        overall_status = "🟢 <b>Уведомления полностью ВКЛЮЧЕНЫ</b> (Лололошка + Фиксплей)"
    elif lol_active or fix_active:
        active_name = "Лололошка" if lol_active else "Фиксплей"
        overall_status = f"🟡 <b>Уведомления ВКЛЮЧЕНЫ частично</b> (только {active_name})"
    else:
        overall_status = "🔴 <b>Уведомления ВЫКЛЮЧЕНЫ</b>"

    text = (
        f"🔔 <b>Управление уведомлениями онлайна</b>\n\n"
        f"Текущее состояние: {overall_status}\n\n"
        "Бот пришлёт вам уведомление, когда ютубер зайдёт на <b>Solo Leveling</b>, перейдёт в <b>лобби</b> или выйдет <b>офлайн</b>."
    )
    return text

async def generate_admin_stats_text() -> str:
    """Generates admin statistics text in MSK timezone."""
    total_users = await db.get_total_users_count()
    active_subs = await db.get_active_subscribers_count()
    breakdown = await db.get_subscriptions_breakdown()
    
    lol_count = breakdown.get("MrLalalashkaXXL", 0)
    fix_count = breakdown.get("F1xPlay_", 0)
    
    now_str = get_now_msk_str()
    
    text = (
        "👑 <b>Панель Администратора</b>\n\n"
        f"📊 <b>Статистика использования бота:</b>\n\n"
        f"👥 <b>Всего пользователей в базе:</b> <code>{total_users}</code>\n"
        f"🔔 <b>Пользователей с активными уведомлениями:</b> <code>{active_subs}</code>\n\n"
        f"<b>Подписки по ютуберам:</b>\n"
        f"• 🎬 <b>Лололошка</b> (<code>MrLalalashkaXXL</code>): <b>{lol_count}</b> чел.\n"
        f"• 🎮 <b>Фиксплей</b> (<code>F1xPlay_</code>): <b>{fix_count}</b> чел.\n\n"
        f"⏱ <b>Интервал проверки онлайна:</b> каждые <code>2 сек</code>\n"
        f"🕒 <i>Время отчета (МСК): {now_str}</i>"
    )
    return text

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handler for /start command."""
    await db.add_user(message.from_user.id)
    
    welcome_text = (
        "👋 <b>Привет! Я бот-мониторинг онлайна на VimeWorld!</b>\n\n"
        "Я отслеживаю сервер каждые 2 секунды и отправляю уведомления при входе на <b>Solo Leveling</b>, смене режима или выходе с сервера:\n"
        "• 🎬 <b>Лололошка</b> (<code>MrLalalashkaXXL</code>)\n"
        "• 🎮 <b>Фиксплей</b> (<code>F1xPlay_</code>)\n\n"
        "Выбери нужный раздел на клавиатуре ниже или настрой уведомления!"
    )
    
    try:
        await message.answer(
            welcome_text,
            reply_markup=keyboards.get_main_keyboard(message.from_user.id),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await message.answer(welcome_text, reply_markup=keyboards.get_main_keyboard(message.from_user.id), parse_mode="HTML")

@router.message(F.text.contains("Лололошка"))
async def handle_lololoshka(message: Message):
    """Checks Lololoshka status."""
    info = await checker.fetch_player_status(YOUTUBERS["MrLalalashkaXXL"]["nick"])
    msg_text = format_status_msg(info, custom_title="🎬 Ютубер Лололошка")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🌐 Профиль VimeWorld", url=info['url'])
    ]])
    
    try:
        await message.answer(msg_text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await message.answer(msg_text, reply_markup=kb, parse_mode="HTML")

@router.message(F.text.contains("Фиксплей"))
async def handle_fixplay(message: Message):
    """Checks FixPlay status."""
    info = await checker.fetch_player_status(YOUTUBERS["F1xPlay_"]["nick"])
    msg_text = format_status_msg(info, custom_title="🎮 Ютубер Фиксплей")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🌐 Профиль VimeWorld", url=info['url'])
    ]])
    
    try:
        await message.answer(msg_text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await message.answer(msg_text, reply_markup=kb, parse_mode="HTML")

@router.message(Command("monitoring"))
@router.message(F.text.contains("уведомлен"))
@router.message(F.text.contains("Уведомлен"))
@router.message(F.text.contains("Мониторинг"))
@router.message(F.text.contains("мониторинг"))
async def handle_monitoring(message: Message):
    """Shows monitoring menu with toggle controls."""
    user_id = message.from_user.id
    await db.add_user(user_id)
    text = await generate_monitoring_text(user_id)
    kb = await keyboards.get_monitoring_inline_keyboard(user_id)
    try:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.message(F.text.contains("Создатель"))
async def handle_creator(message: Message):
    """Shows creator info with live VimeWorld status."""
    info = await checker.fetch_player_status(CREATOR["nick"])
    status_icon = info['status_display']
        
    text = (
        f"👑 <b>Создатель бота:</b> <a href='{CREATOR['url']}'>{CREATOR['name']}</a>\n\n"
        f"Текущий статус на VimeWorld: <b>{status_icon}</b>\n"
    )
    if info.get('level') is not None:
        text += f"Уровень: <b>{info['level']}</b>\n"
    if info.get('rank'):
        text += f"Ранг: <b>{info['rank']}</b>\n"
        
    text += f"\n🔗 <a href='{CREATOR['url']}'>Ссылка на профиль VimeWorld</a>"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👑 Профиль Создателя на VimeWorld", url=CREATOR['url'])
    ]])
    
    try:
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await message.answer(text, parse_mode="HTML")

# ADMIN PANEL HANDLERS
@router.message(Command("admin"))
@router.message(Command("stats"))
@router.message(F.text.contains("Админ"))
@router.message(F.text.contains("админ"))
async def handle_admin_panel(message: Message):
    """Admin panel stats viewer."""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ <b>У вас нет доступа к админ-панели.</b>", parse_mode="HTML")
        return
        
    text = await generate_admin_stats_text()
    kb = keyboards.get_admin_inline_keyboard()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "admin_refresh_stats")
async def cb_admin_refresh_stats(callback: CallbackQuery):
    """Refreshes admin statistics."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
        
    text = await generate_admin_stats_text()
    kb = keyboards.get_admin_inline_keyboard()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer("🔄 Статистика обновлена!")
    except TelegramAPIError:
        await callback.answer("Статистика актуальна")

# Callback handlers for monitoring inline keyboard
@router.callback_query(F.data.startswith("toggle_"))
async def cb_toggle(callback: CallbackQuery):
    nick = callback.data.replace("toggle_", "")
    user_id = callback.from_user.id
    await db.add_user(user_id)
    
    is_sub = await db.is_subscribed(user_id, nick)
    if is_sub:
        await db.unsubscribe_user(user_id, nick)
        await callback.answer("🔴 Уведомления отключены!")
    else:
        await db.subscribe_user(user_id, nick)
        await callback.answer("🟢 Уведомления включены!")
        
    text = await generate_monitoring_text(user_id)
    kb = await keyboards.get_monitoring_inline_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramAPIError:
        pass

@router.callback_query(F.data == "enable_all")
async def cb_enable_all(callback: CallbackQuery):
    user_id = callback.from_user.id
    await db.add_user(user_id)
    
    for nick in YOUTUBERS.keys():
        await db.subscribe_user(user_id, nick)
    await callback.answer("🟢 Уведомления включены!")
    
    text = await generate_monitoring_text(user_id)
    kb = await keyboards.get_monitoring_inline_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramAPIError:
        pass

@router.callback_query(F.data == "disable_all")
async def cb_disable_all(callback: CallbackQuery):
    user_id = callback.from_user.id
    await db.add_user(user_id)
    
    for nick in YOUTUBERS.keys():
        await db.unsubscribe_user(user_id, nick)
    await callback.answer("🔴 Уведомления отключены!")
    
    text = await generate_monitoring_text(user_id)
    kb = await keyboards.get_monitoring_inline_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramAPIError:
        pass
