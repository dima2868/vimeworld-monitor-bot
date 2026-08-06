from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import YOUTUBERS, CREATOR
import checker
import database as db
import keyboards

router = Router()

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
    """Checks all YouTubers + Creator status."""
    await message.answer("🔄 <i>Запрашиваю свежую информацию с VimeWorld...</i>", parse_mode="HTML")
    
    lol_info = await checker.fetch_player_status(YOUTUBERS["MrLalalashkaXXL"]["nick"])
    fix_info = await checker.fetch_player_status(YOUTUBERS["F1xPlay_"]["nick"])
    creator_info = await checker.fetch_player_status(CREATOR["nick"])

    text = "📊 <b>Текущий онлайн ютуберов на VimeWorld:</b>\n\n"
    
    # Lololoshka
    if lol_info['is_online']:
        lol_icon = f"🟢 В СЕТИ ({lol_info['game']})" if lol_info.get('game') else "🟢 В СЕТИ"
    else:
        lol_icon = "🔴 Не в сети"
    text += f"🎬 <b>Лололошка</b> (<code>{lol_info['nickname']}</code>): {lol_icon}\n"
    
    # FixPlay
    if fix_info['is_online']:
        fix_icon = f"🟢 В СЕТИ ({fix_info['game']})" if fix_info.get('game') else "🟢 В СЕТИ"
    else:
        fix_icon = "🔴 Не в сети"
    text += f"🎮 <b>Фиксплей</b> (<code>{fix_info['nickname']}</code>): {fix_icon}\n\n"
    
    # Creator
    if creator_info['is_online']:
        creator_icon = f"🟢 В СЕТИ ({creator_info['game']})" if creator_info.get('game') else "🟢 В СЕТИ"
    else:
        creator_icon = "🔴 Не в сети"
    text += f"👑 <b>Создатель бота</b> (<a href='{CREATOR['url']}'>{CREATOR['name']}</a>): {creator_icon}\n"

    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)

@router.message(F.text.contains("Мониторинг"))
async def handle_monitoring(message: Message):
    """Shows monitoring menu."""
    kb = await keyboards.get_monitoring_inline_keyboard(message.from_user.id)
    text = (
        "🔔 <b>Настройка авто-мониторинга</b>\n\n"
        "Включи тумблер для интересующих тебя ютуберов, и бот каждые 2 секунды проверяет их статус "
        "и мгновенно отправит тебе уведомление в Telegram, как только они зайдут в сеть!"
    )
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
    
    is_sub = await db.is_subscribed(user_id, nick)
    if is_sub:
        await db.unsubscribe_user(user_id, nick)
        await callback.answer("❌ Уведомления отключены!")
    else:
        await db.subscribe_user(user_id, nick)
        await callback.answer("🟢 Уведомления включены!")
        
    kb = await keyboards.get_monitoring_inline_keyboard(user_id)
    await callback.message.edit_reply_markup(reply_markup=kb)

@router.callback_query(F.data == "enable_all")
async def cb_enable_all(callback: CallbackQuery):
    user_id = callback.from_user.id
    for nick in YOUTUBERS.keys():
        await db.subscribe_user(user_id, nick)
    await callback.answer("⚡ Мониторинг всех ютуберов включен!")
    kb = await keyboards.get_monitoring_inline_keyboard(user_id)
    await callback.message.edit_reply_markup(reply_markup=kb)

@router.callback_query(F.data == "disable_all")
async def cb_disable_all(callback: CallbackQuery):
    user_id = callback.from_user.id
    for nick in YOUTUBERS.keys():
        await db.unsubscribe_user(user_id, nick)
    await callback.answer("❌ Мониторинг всех ютуберов отключен!")
    kb = await keyboards.get_monitoring_inline_keyboard(user_id)
    await callback.message.edit_reply_markup(reply_markup=kb)
