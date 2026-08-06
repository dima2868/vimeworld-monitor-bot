import asyncio
import logging
from datetime import datetime
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError
from config import YOUTUBERS, CHECK_INTERVAL
import checker
import database as db

logger = logging.getLogger(__name__)

async def start_monitoring(bot: Bot):
    """
    Background worker loop that checks YouTuber online status periodically (every 2s).
    Triggers notifications on state transitions:
    - Entering Solo Leveling (SOLOLEVELING)
    - Moving to Lobby (LOBBY)
    - Disconnecting (OFFLINE)
    """
    logger.info(f"Starting background monitoring loop (check interval: {CHECK_INTERVAL}s)...")
    
    # Initial status population without sending notifications on startup
    for nick in YOUTUBERS.keys():
        try:
            info = await checker.fetch_player_status(nick)
            await db.update_player_last_state(nick, info['state'], info['is_online'])
            logger.info(f"Initialized status for {nick}: State={info['state']} ({info['status_display']})")
        except Exception as e:
            logger.error(f"Error during initial status check for {nick}: {e}")

    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL)
            
            for nick, data in YOUTUBERS.items():
                info = await checker.fetch_player_status(nick)
                current_state = info['state']
                prev_state = await db.get_player_last_state(nick)
                
                # Check for state transition
                if current_state != prev_state:
                    logger.info(f"⚡ State change for {data['name']} ({nick}): {prev_state} ➔ {current_state}")
                    
                    subscribers = await db.get_subscribers_for_player(nick)
                    if subscribers:
                        now_str = datetime.now().strftime("%H:%M:%S")
                        alert_msg = None
                        
                        # 1. Entered Solo Leveling
                        if current_state == "SOLOLEVELING":
                            alert_msg = (
                                f"🚨 <b>{data['icon']} {data['name'].upper()} ЗАШЁЛ НА SOLO LEVELING!</b> 🚨\n\n"
                                f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) зашёл в режим <b>Solo Leveling</b> на VimeWorld!\n"
                                f"⏰ Время: <b>{now_str}</b>\n\n"
                                f"🔗 <a href='{data['url']}'>Перейти на профиль VimeWorld</a>"
                            )
                        # 2. Left server (Offline)
                        elif current_state == "OFFLINE":
                            alert_msg = (
                                f"🔴 <b>{data['icon']} {data['name'].upper()} ВЫШЕЛ С СЕРВЕРА</b>\n\n"
                                f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) вышел с сервера VimeWorld.\n"
                                f"⏰ Время выхода: <b>{now_str}</b>"
                            )
                        # 3. Left Solo Leveling / Returned to Lobby
                        elif prev_state == "SOLOLEVELING" and current_state in ("LOBBY", "OTHER_GAME"):
                            alert_msg = (
                                f"🟡 <b>{data['icon']} {data['name'].upper()} ВЫШЕЛ С SOLO LEVELING В ЛОББИ</b>\n\n"
                                f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) вышел с Solo Leveling в лобби (или сменил режим).\n"
                                f"⏰ Время: <b>{now_str}</b>"
                            )
                        # 4. Connected to server (In Lobby)
                        elif prev_state == "OFFLINE" and current_state in ("LOBBY", "OTHER_GAME"):
                            alert_msg = (
                                f"🟡 <b>{data['icon']} {data['name'].upper()} ЗАШЁЛ НА СЕРВЕР (В ЛОББИ)</b>\n\n"
                                f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) зашёл на VimeWorld (сейчас в лобби).\n"
                                f"⏰ Время входа: <b>{now_str}</b>"
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
