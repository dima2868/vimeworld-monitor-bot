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
    
    intents = discord.Intents.default()
    intents.voice_states = True
    intents.guilds = True
    intents.members = True
    
    discord_client = commands.Bot(command_prefix="!", intents=intents)
    
    @discord_client.event
    async def on_ready():
        logger.info(f"Discord Bot connected as {discord_client.user} (ID: {discord_client.user.id})")

except ImportError:
    logger.warning("discord.py is not installed. Discord voice notifications will be disabled.")
    discord_client = None


async def find_active_human_voice_channel():
    """
    Finds a voice channel that has at least 1 non-bot human member inside.
    Checks DISCORD_VOICE_CHANNEL_ID first if configured, or searches all guilds.
    """
    if not discord_client or not discord_client.is_ready():
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


async def play_voice_sound(sound_filename: str):
    """
    Plays an MP3/OGG sound file in the active Discord Voice Channel ONLY IF at least 1 human is inside.
    Sounds are stored in the 'sounds/' directory.
    """
    global voice_client
    if not discord_client or not DISCORD_BOT_TOKEN:
        return

    # Check if any voice channel has active human members
    target_vc = await find_active_human_voice_channel()
    if not target_vc:
        logger.info(f"Skipping Discord voice alert '{sound_filename}': No human users inside any voice channel.")
        # Disconnect if currently connected to an empty channel
        if voice_client and voice_client.is_connected():
            try:
                await voice_client.disconnect()
            except Exception:
                pass
            voice_client = None
        return
        
    sound_path = os.path.join("sounds", sound_filename)
    if not os.path.exists(sound_path):
        sound_path = sound_filename # Fallback to root dir
        
    if not os.path.exists(sound_path):
        logger.warning(f"Audio file '{sound_filename}' not found in sounds/ or root directory.")
        return

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
                
            audio_source = discord.FFmpegPCMAudio(sound_path)
            voice_client.play(audio_source)
            logger.info(f"Playing Discord voice alert: {sound_filename} in channel '{target_vc.name}'")
            
            # Wait for audio playback to finish
            while voice_client.is_playing():
                await asyncio.sleep(0.5)
                
            # Disconnect after playing if no humans remain
            await asyncio.sleep(1)
            human_members = [m for m in target_vc.members if not m.bot]
            if len(human_members) == 0:
                await voice_client.disconnect()
                voice_client = None
                logger.info("Disconnected from Discord voice channel as no humans remain.")
    except Exception as e:
        logger.error(f"Failed to play Discord voice sound '{sound_filename}': {e}")


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
