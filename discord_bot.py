import os
import asyncio
import logging
from config import DISCORD_BOT_TOKEN, DISCORD_VOICE_CHANNEL_ID

logger = logging.getLogger(__name__)

# Discord client instance placeholder
discord_client = None
voice_client = None

try:
    import discord
    from discord.ext import commands
    
    # Use standard non-privileged intents for voice channels
    intents = discord.Intents.default()
    intents.voice_states = True
    intents.guilds = True
    
    discord_client = commands.Bot(command_prefix="!", intents=intents)
    
    @discord_client.event
    async def on_ready():
        logger.info(f"Discord Bot connected as {discord_client.user} (ID: {discord_client.user.id})")

except ImportError:
    logger.warning("discord.py is not installed. Discord voice notifications will be disabled.")
    discord_client = None


def is_discord_ready() -> bool:
    """Checks if Discord bot is initialized and logged in."""
    return bool(discord_client and discord_client.is_ready())


async def find_active_human_voice_channel():
    """
    Finds a voice channel that has at least 1 non-bot human member inside.
    Checks DISCORD_VOICE_CHANNEL_ID first if configured, or searches all guilds.
    """
    if not is_discord_ready():
        return None
        
    # Check configured channel ID first if provided
    if DISCORD_VOICE_CHANNEL_ID:
        try:
            channel = discord_client.get_channel(DISCORD_VOICE_CHANNEL_ID)
            if not channel:
                channel = await discord_client.fetch_channel(DISCORD_VOICE_CHANNEL_ID)
            if isinstance(channel, discord.VoiceChannel):
                human_members = [m for m in channel.members if not m.bot]
                if len(human_members) > 0:
                    return channel
        except Exception as e:
            logger.warning(f"Error checking specified voice channel {DISCORD_VOICE_CHANNEL_ID}: {e}")

    # Search all voice channels across all connected Discord servers (guilds)
    for guild in discord_client.guilds:
        for vc in guild.voice_channels:
            human_members = [m for m in vc.members if not m.bot]
            if len(human_members) > 0:
                return vc

    return None


async def get_discord_debug_info() -> str:
    """Returns human-readable status of Discord bot connection."""
    if not DISCORD_BOT_TOKEN:
        return "❌ <b>Токен DISCORD_BOT_TOKEN не указан</b> в переменных окружения."
        
    if not is_discord_ready():
        return "⏳ <b>Discord-бот в процессе подключения...</b> Попробуйте через 5 секунд."
        
    guilds = discord_client.guilds
    if not guilds:
        return (
            "⚠️ <b>Бот подключен к Discord, но НЕ добавлен ни на один сервер!</b>\n\n"
            "Добавьте бота на ваш Discord-сервер по ссылке авторизации."
        )
        
    text = f"✅ <b>Discord-бот активен:</b> <code>{discord_client.user}</code>\n"
    text += f"🏠 <b>Серверы ({len(guilds)}):</b> " + ", ".join([g.name for g in guilds]) + "\n\n"
    
    active_vc = await find_active_human_voice_channel()
    if active_vc:
        humans = [m.display_name for m in active_vc.members if not m.bot]
        text += f"🔊 <b>Найден активный войс:</b> {active_vc.name} (Людей: {len(humans)} - {', '.join(humans)})\n"
    else:
        text += "🔇 <b>Никого нет в голосовых каналах.</b> Зайдите в любой голосовой канал на сервере для теста!\n"
        
    return text


async def play_voice_sound(sound_filename: str) -> tuple[bool, str]:
    """
    Plays an MP3/OGG sound file in the active Discord Voice Channel ONLY IF at least 1 human is inside.
    Amplifies audio volume by +250% (volume=2.5) via FFmpeg filter.
    Automatically disconnects from the voice channel immediately after playback completes.
    Returns (success: bool, detail_message: str).
    """
    global voice_client
    if not DISCORD_BOT_TOKEN:
        return False, "❌ Токен DISCORD_BOT_TOKEN не установлен в переменных окружения!"

    if not is_discord_ready():
        return False, "⏳ Discord бот еще не подключился к сетям Discord. Подождите пару секунд."

    # Check if any voice channel has active human members
    target_vc = await find_active_human_voice_channel()
    if not target_vc:
        msg = "🔇 Ни один человек не найден ни в одном голосовом канале! Зайдите в любой войс-канал на сервере и повторите тест."
        logger.info(f"Skipping Discord voice alert '{sound_filename}': {msg}")
        if voice_client and voice_client.is_connected():
            try:
                await voice_client.disconnect()
            except Exception:
                pass
            voice_client = None
        return False, msg
        
    sound_path = os.path.join("sounds", sound_filename)
    if not os.path.exists(sound_path):
        sound_path = sound_filename # Fallback to root dir
        
    if not os.path.exists(sound_path):
        msg = f"❌ Файл звука '{sound_filename}' не найден на сервере!"
        logger.warning(msg)
        return False, msg

    try:
        # Connect or move to the channel with human members
        if voice_client and voice_client.is_connected():
            if voice_client.channel.id != target_vc.id:
                await voice_client.move_to(target_vc)
        else:
            voice_client = await target_vc.connect()
            
        logger.info(f"Connected to Discord Voice Channel '{target_vc.name}' with human members.")

        if voice_client and voice_client.is_connected():
            if voice_client.is_playing():
                voice_client.stop()
                
            # FFmpeg option: -af "volume=2.5" amplifies audio volume to 250% (+8 dB)
            audio_source = discord.FFmpegPCMAudio(sound_path, options='-af "volume=2.5"')
            voice_client.play(audio_source)
            logger.info(f"Playing Discord voice alert (+250% volume): {sound_filename} in channel '{target_vc.name}'")
            
            # Background task to disconnect cleanly as soon as audio finishes playing
            async def disconnect_after_playback():
                global voice_client
                try:
                    while voice_client and voice_client.is_playing():
                        await asyncio.sleep(0.5)
                    await asyncio.sleep(1)
                    if voice_client and voice_client.is_connected():
                        await voice_client.disconnect()
                        voice_client = None
                        logger.info(f"Disconnected from Discord voice channel after playing {sound_filename}.")
                except Exception as ex:
                    logger.warning(f"Error disconnecting after playback: {ex}")
                    voice_client = None

            asyncio.create_task(disconnect_after_playback())
            
            return True, f"🔊 Проигрываю громкий звук (+250%) <b>{sound_filename}</b> в канале <b>{target_vc.name}</b>!"
    except Exception as e:
        err_msg = f"❌ Ошибка воспроизведения звука: {e}"
        logger.error(err_msg)
        return False, err_msg


async def start_discord_bot():
    """Launches Discord bot in background if DISCORD_BOT_TOKEN is set."""
    if not DISCORD_BOT_TOKEN:
        logger.info("DISCORD_BOT_TOKEN is not set. Discord voice bot skipped.")
        return
        
    if discord_client:
        logger.info("Starting Discord Voice Bot...")
        try:
            await discord_client.start(DISCORD_BOT_TOKEN)
        except Exception as e:
            logger.error(f"Error running Discord bot: {e}")
