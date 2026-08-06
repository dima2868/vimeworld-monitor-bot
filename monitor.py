import asyncio
import logging
from datetime import datetime
from aiogram import Bot
from config import YOUTUBERS, CHECK_INTERVAL
import checker
import database as db

logger = logging.getLogger(__name__)

async def start_monitoring(bot: Bot):
    """
    Background worker loop that checks YouTuber online status periodically
    and notifies subscribers when someone comes online.
    """
    logger.info(f"Starting background monitoring loop (check interval: {CHECK_INTERVAL}s)...")
    
    # Initial status population without sending notifications on startup
    for nick in YOUTUBERS.keys():
        try:
            info = await checker.fetch_player_status(nick)
            await db.update_player_last_status(nick, info['is_online'])
            logger.info(f"Initialized status for {nick}: Online={info['is_online']}")
        except Exception as e:
            logger.error(f"Error during initial status check for {nick}: {e}")

    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL)
            
            for nick, data in YOUTUBERS.items():
                info = await checker.fetch_player_status(nick)
                is_currently_online = info['is_online']
                was_online = await db.get_player_last_status(nick)
                
                # Check for status transition: Offline -> Online
                if is_currently_online and not was_online:
                    logger.info(f"🚨 ALERT! {data['name']} ({nick}) came ONLINE on VimeWorld!")
                    
                    subscribers = await db.get_subscribers_for_player(nick)
                    if subscribers:
                        now_str = datetime.now().strftime("%H:%M:%S")
                        game_str = f"\n🎮 Режим игры: <b>{info['game']}</b>" if info.get('game') else ""
                        
                        alert_msg = (
                            f"🚨 <b>{data['icon']} {data['name'].upper()} В СЕТИ!</b> 🚨\n\n"
                            f"🎮 <b>{data['name']}</b> (<code>{nick}</code>) только что зашел на VimeWorld!{game_str}\n"
                            f"⏰ Время входа: <b>{now_str}</b>\n\n"
                            f"🔗 <a href='{data['url']}'>Перейти на профиль VimeWorld</a>"
                        )
                        
                        for user_id in subscribers:
                            try:
                                await bot.send_message(
                                    chat_id=user_id,
                                    text=alert_msg,
                                    parse_mode="HTML",
                                    disable_web_page_preview=False
                                )
                            except Exception as err:
                                logger.warning(f"Failed to send alert to user {user_id}: {err}")
                
                # Save updated status
                await db.update_player_last_status(nick, is_currently_online)
                
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
