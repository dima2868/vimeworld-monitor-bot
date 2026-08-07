import asyncio
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError
from config import YOUTUBERS, DUNGEONS, CHECK_INTERVAL
import checker
import database as db
import discord_bot

logger = logging.getLogger(__name__)

# Moscow Timezone (UTC+3)
MSK_TZ = timezone(timedelta(hours=3))

def get_now_msk() -> datetime:
    """Returns current datetime in Moscow timezone (UTC+3)."""
    return datetime.now(MSK_TZ)

def get_now_msk_str() -> str:
    """Returns current Moscow time formatted as HH:MM:SS."""
    return get_now_msk().strftime("%H:%M:%S")

# Set to keep track of sent dungeon alerts to prevent duplicate sends
sent_dungeon_alerts = set()

async def check_and_send_dungeon_alerts(bot: Bot):
    """
    Checks if a dungeon or raid starts in 1 minute and sends notifications + plays Discord voice sound.
    - Hard Dungeon: starts at :10 and :40 -> alert at :09 and :39
    - Medium Dungeon: starts at :15 and :45 -> alert at :14 and :44
    - Jeju Raid: starts at 18:00 MSK -> alert at 17:59 MSK
    """
    now = get_now_msk()
    hour = now.hour
    minute = now.minute
    now_str = now.strftime("%H:%M:%S")
    
    # 1. Hard Dungeon Alert (Alert at :09 and :39 - 1 min before :10 and :40)
    if minute in (9, 39):
        start_min = 10 if minute == 9 else 40
        start_time_str = f"{hour:02d}:{start_min:02d}"
        alert_key = ("dungeon_hard", now.date(), hour, minute)
        
        if alert_key not in sent_dungeon_alerts:
            sent_dungeon_alerts.add(alert_key)
            
            # Play Discord Voice Audio
            asyncio.create_task(discord_bot.play_voice_sound("dungeon_hard.mp3"))
            
            subscribers = await db.get_subscribers_for_player("dungeon_hard")
            if subscribers:
                msg = (
                    f"⏰ <b>НАПОМИНАНИЕ О ПОДЗЕМЕЛЬЕ!</b> ⏰\n\n"
                    f"🗡 <b>Сложное подземелье</b> начнется через <b>1 минуту</b> (в <b>{start_time_str}</b>)!\n"
                    f"⏰ Время МСК: <b>{now_str}</b>"
                )
                for user_id in subscribers:
                    try:
                        await bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")
                    except TelegramRetryAfter as err:
                        await asyncio.sleep(err.retry_after + 1)
                    except Exception as err:
                        logger.warning(f"Error sending dungeon_hard alert to user {user_id}: {err}")

    # 2. Medium Dungeon Alert (Alert at :14 and :44 - 1 min before :15 and :45)
    if minute in (14, 44):
        start_min = 15 if minute == 14 else 45
        start_time_str = f"{hour:02d}:{start_min:02d}"
        alert_key = ("dungeon_medium", now.date(), hour, minute)
        
        if alert_key not in sent_dungeon_alerts:
            sent_dungeon_alerts.add(alert_key)
            
            # Play Discord Voice Audio
            asyncio.create_task(discord_bot.play_voice_sound("dungeon_medium.mp3"))
            
            subscribers = await db.get_subscribers_for_player("dungeon_medium")
            if subscribers:
                msg = (
                    f"⏰ <b>НАПОМИНАНИЕ О ПОДЗЕМЕЛЬЕ!</b> ⏰\n\n"
                    f"⚔️ <b>Среднее подземелье</b> начнется через <b>1 минуту</b> (в <b>{start_time_str}</b>)!\n"
                    f"⏰ Время МСК: <b>{now_str}</b>"
                )
                for user_id in subscribers:
                    try:
                        await bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")
                    except TelegramRetryAfter as err:
                        await asyncio.sleep(err.retry_after + 1)
                    except Exception as err:
                        logger.warning(f"Error sending dungeon_medium alert to user {user_id}: {err}")

    # 3. Jeju Island Raid Alert (Alert at 17:59 MSK - 1 min before 18:00 MSK)
    if hour == 17 and minute == 59:
        alert_key = ("dungeon_jeju", now.date(), hour, minute)
        
        if alert_key not in sent_dungeon_alerts:
            sent_dungeon_alerts.add(alert_key)
            
            # Play Discord Voice Audio
            asyncio.create_task(discord_bot.play_voice_sound("jeju_raid.mp3"))
            
            subscribers = await db.get_subscribers_for_player("dungeon_jeju")
            if subscribers:
                msg = (
                    f"🚨 <b>РЕЙД НА ОСТРОВ ЧЕДЖУ!</b> 🚨\n\n"
                    f"🌋 <b>Рейд на Остров Чеджу</b> начнется через <b>1 минуту</b> (в <b>18:00 МСК</b>)!\n"
                    f"⏰ Время МСК: <b>{now_str}</b>"
                )
                for user_id in subscribers:
                    try:
                        await bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")
                    except TelegramRetryAfter as err:
                        await asyncio.sleep(err.retry_after + 1)
                    except Exception as err:
                        logger.warning(f"Error sending dungeon_jeju alert to user {user_id}: {err}")

    # Clean old alert keys periodically
    if len(sent_dungeon_alerts) > 50:
        sent_dungeon_alerts.clear()

async def start_monitoring(bot: Bot):
    """
    Background worker loop that checks YouTuber online status and Dungeon/Raid timers every 2s.
    """
    logger.info(f"Starting background monitoring loop (check interval: {CHECK_INTERVAL}s)...")
    
    # Initialize status ONLY if player state does not exist in DB yet
    for nick in YOUTUBERS.keys():
        try:
            state_exists = await db.has_player_state(nick)
            if not state_exists:
                info = await checker.fetch_player_status(nick)
                await db.update_player_last_state(nick, info['state'], info['is_online'])
                logger.info(f"Initialized new player state for {nick}: State={info['state']}")
            else:
                saved_state = await db.get_player_last_state(nick)
                logger.info(f"Preserved existing player state across restart for {nick}: State={saved_state}")
        except Exception as e:
            logger.error(f"Error during status check on startup for {nick}: {e}")

    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL)
            
            # Check Dungeon & Raid 1-minute pre-alerts
            await check_and_send_dungeon_alerts(bot)
            
            # Check YouTuber online states
            for nick, data in YOUTUBERS.items():
                info = await checker.fetch_player_status(nick)
                current_state = info['state']
                prev_state = await db.get_player_last_state(nick)
                
                # Check for state transition
                if current_state != prev_state:
                    logger.info(f"⚡ State change for {data['name']} ({nick}): {prev_state} ➔ {current_state}")
                    
                    # Play Discord Voice Audio if YouTuber enters Solo Leveling
                    if current_state == "SOLOLEVELING" and "sound" in data:
                        asyncio.create_task(discord_bot.play_voice_sound(data["sound"]))

                    subscribers = await db.get_subscribers_for_player(nick)
                    if subscribers:
                        now_str = get_now_msk_str()
                        alert_msg = None
                        
                        # 1. Entered Solo Leveling
                        if current_state == "SOLOLEVELING":
                            alert_msg = (
                                f"🚨 <b>{data['icon']} {data['name'].upper()} ЗАШЁЛ НА SOLO LEVELING!</b> 🚨\n\n"
                                f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) зашёл в режим <b>Solo Leveling</b> на VimeWorld!\n"
                                f"⏰ Время (МСК): <b>{now_str}</b>\n\n"
                                f"🔗 <a href='{data['url']}'>Перейти на профиль VimeWorld</a>"
                            )
                        # 2. Left server (Offline)
                        elif current_state == "OFFLINE":
                            alert_msg = (
                                f"🔴 <b>{data['icon']} {data['name'].upper()} ВЫШЕЛ С СЕРВЕРА</b>\n\n"
                                f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) вышел с сервера VimeWorld.\n"
                                f"⏰ Время выхода (МСК): <b>{now_str}</b>"
                            )
                        # 3. Left Solo Leveling / Returned to Lobby
                        elif prev_state == "SOLOLEVELING" and current_state in ("LOBBY", "OTHER_GAME"):
                            alert_msg = (
                                f"🟡 <b>{data['icon']} {data['name'].upper()} ВЫШЕЛ С SOLO LEVELING В ЛОББИ</b>\n\n"
                                f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) вышел с Solo Leveling в лобби (или сменил режим).\n"
                                f"⏰ Время (МСК): <b>{now_str}</b>"
                            )
                        # 4. Connected to server (In Lobby)
                        elif prev_state == "OFFLINE" and current_state in ("LOBBY", "OTHER_GAME"):
                            alert_msg = (
                                f"🟡 <b>{data['icon']} {data['name'].upper()} ЗАШЁЛ НА СЕРВЕР (В ЛОББИ)</b>\n\n"
                                f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) зашёл на VimeWorld (сейчас в лобби).\n"
                                f"⏰ Время входа (МСК): <b>{now_str}</b>"
                            )

                        if alert_msg:
                            for user_id in subscribers:
                                try:
                                    await bot.send_message(
                                        chat_id=user_id,
                                        text=alert_msg,
                                        parse_mode="HTML",
                                        disable_web_page_preview=False
                                    )
                                except TelegramRetryAfter as err:
                                    logger.warning(f"Flood limit sending alert to user {user_id}. Waiting {err.retry_after}s...")
                                    await asyncio.sleep(err.retry_after + 1)
                                except Exception as err:
                                    logger.warning(f"Failed to send alert to user {user_id}: {err}")

                # Save updated state
                await db.update_player_last_state(nick, current_state, info['is_online'])
                
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
