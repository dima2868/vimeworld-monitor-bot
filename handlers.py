import asyncio
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Router, F
from aiogram.filters import Command, or_f
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError
from config import YOUTUBERS, DUNGEONS, CREATOR, ADMIN_IDS
import checker
import dungeon_utils
import database as db
import keyboards
import discord_bot

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
    hard_active = "dungeon_hard" in subs
    med_active = "dungeon_medium" in subs
    jeju_active = "dungeon_jeju" in subs

    total_subs_count = sum([lol_active, fix_active, hard_active, med_active, jeju_active])
    
    if total_subs_count == 5:
        overall_status = "🟢 <b>Все уведомления ВКЛЮЧЕНЫ</b> (Ютуберы + Подземелья + Чеджу)"
    elif total_subs_count > 0:
        overall_status = f"🟡 <b>Уведомления ВКЛЮЧЕНЫ частично</b> ({total_subs_count} из 5 типов)"
    else:
        overall_status = "🔴 <b>Уведомления ВЫКЛЮЧЕНЫ</b>"

    text = (
        f"🔔 <b>Управление уведомлениями онлайна и подземелий</b>\n\n"
        f"Текущее состояние: {overall_status}\n\n"
        "<b>Доступные подписки:</b>\n"
        "• 🎬/🎮 <b>Ютуберы:</b> статус онлайна и входа на Solo Leveling\n"
        "• 🗡 <b>Сложное подземелье:</b> каждые :10 и :40 мин (увед за 1 мин)\n"
        "• ⚔️ <b>Среднее подземелье:</b> каждые :15 и :45 мин (увед за 1 мин)\n"
        "• 🌋 <b>Остров Чеджу (Рейд):</b> в 18:00 МСК (увед в 17:59)\n\n"
        "Нажимай на кнопки ниже, чтобы включать или выключать нужные уведомления:"
    )
    return text

async def generate_admin_stats_text() -> str:
    """Generates admin statistics text in MSK timezone including Discord voice bot status."""
    total_users = await db.get_total_users_count()
    active_subs = await db.get_active_subscribers_count()
    breakdown = await db.get_subscriptions_breakdown()
    
    lol_count = breakdown.get("MrLalalashkaXXL", 0)
    fix_count = breakdown.get("F1xPlay_", 0)
    hard_count = breakdown.get("dungeon_hard", 0)
    med_count = breakdown.get("dungeon_medium", 0)
    jeju_count = breakdown.get("dungeon_jeju", 0)
    
    now_str = get_now_msk_str()
    discord_info = await discord_bot.get_discord_debug_info()
    
    text = (
        "👑 <b>Панель Администратора</b>\n\n"
        f"📊 <b>Статистика бота:</b>\n"
        f"👥 Пользователей в базе: <code>{total_users}</code> | 🔔 Активных подписчиков: <code>{active_subs}</code>\n\n"
        f"<b>Подписки:</b>\n"
        f"• 🎬 Лололошка: <b>{lol_count}</b> | 🎮 Фиксплей: <b>{fix_count}</b>\n"
        f"• 🗡 Сложное: <b>{hard_count}</b> | ⚔️ Среднее: <b>{med_count}</b> | 🌋 Чеджу: <b>{jeju_count}</b>\n\n"
        f"<b>Статус Discord Voice:</b>\n{discord_info}\n\n"
        f"⏱ <i>Интервал проверки: 2 сек | Отчет (МСК): {now_str}</i>"
    )
    return text

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handler for /start command."""
    await db.add_user(message.from_user.id)
    
    welcome_text = (
        "👋 <b>Привет! Я бот-мониторинг VimeWorld (Solo Leveling)!</b>\n\n"
        "Я отслеживаю статус ютуберов и расписание подземелий с автоматическими уведомлениями:\n"
        "• 🎬 <b>Лололошка</b> (<code>MrLalalashkaXXL</code>)\n"
        "• 🎮 <b>Фиксплей</b> (<code>F1xPlay_</code>)\n"
        "• 🗡 <b>Сложное подземелье</b> (каждые :10 и :40 мин)\n"
        "• ⚔️ <b>Среднее подземелье</b> (каждые :15 и :45 мин)\n"
        "• 🌋 <b>Остров Чеджу (Рейд)</b> (в 18:00 МСК)\n\n"
        "Выбери нужный раздел на клавиатуре ниже!"
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

@router.message(or_f(Command("dungeons"), F.text.contains("Подземелья"), F.text.contains("подземелья"), F.text.contains("Рейды"), F.text.contains("рейды")))
async def handle_dungeons(message: Message):
    """Shows upcoming dungeons and raids schedule."""
    text = dungeon_utils.generate_dungeon_schedule_text()
    try:
        await message.answer(text, parse_mode="HTML")
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await message.answer(text, parse_mode="HTML")

@router.message(or_f(Command("monitoring"), F.text.contains("уведомлен"), F.text.contains("Уведомлен"), F.text.contains("Мониторинг"), F.text.contains("мониторинг")))
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

@router.callback_query(F.data.startswith("test_sound_"))
async def cb_test_sound(callback: CallbackQuery):
    """Triggers Discord voice sound playback test from admin panel."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
        
    sound_filename = callback.data.replace("test_sound_", "")
    await callback.answer("⏳ Запуск звукового теста Discord...")
    
    success, detail_msg = await discord_bot.play_voice_sound(sound_filename)
    
    admin_text = await generate_admin_stats_text()
    admin_text += f"\n\n<b>Результат теста звука ({sound_filename}):</b>\n{detail_msg}"
    
    kb = keyboards.get_admin_inline_keyboard()
    try:
        await callback.message.edit_text(admin_text, reply_markup=kb, parse_mode="HTML")
    except TelegramAPIError:
        pass

# Callback handlers for monitoring inline keyboard
ALL_KEYS = ["MrLalalashkaXXL", "F1xPlay_", "dungeon_hard", "dungeon_medium", "dungeon_jeju"]

@router.callback_query(F.data.startswith("toggle_"))
async def cb_toggle(callback: CallbackQuery):
    key = callback.data.replace("toggle_", "")
    user_id = callback.from_user.id
    await db.add_user(user_id)
    
    is_sub = await db.is_subscribed(user_id, key)
    if is_sub:
        await db.unsubscribe_user(user_id, key)
        await callback.answer("🔴 Уведомление отключено!")
    else:
        await db.subscribe_user(user_id, key)
        await callback.answer("🟢 Уведомление включено!")
        
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
    
    for key in ALL_KEYS:
        await db.subscribe_user(user_id, key)
    await callback.answer("🟢 Все уведомления ВКЛЮЧЕНЫ!")
    
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
    
    for key in ALL_KEYS:
        await db.unsubscribe_user(user_id, key)
    await callback.answer("🔴 Все уведомления ВЫКЛЮЧЕНЫ!")
    
    text = await generate_monitoring_text(user_id)
    kb = await keyboards.get_monitoring_inline_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramAPIError:
        pass
