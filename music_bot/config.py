import os
from dotenv import load_dotenv

load_dotenv()

# Discord Music Bot Token
# You can set a dedicated bot token for the music bot, or reuse the same token
DISCORD_MUSIC_BOT_TOKEN = os.getenv("DISCORD_MUSIC_BOT_TOKEN") or os.getenv("DISCORD_BOT_TOKEN", "")

# Excluded Voice Channel IDs (AFK channels, private rooms, etc.)
EXCLUDED_VOICE_CHANNEL_IDS = [
    553187808630538240,  # AFK channel
    541663825892737034   # Гостиная 2
]

# Admin Discord User IDs who can force-stop or manage the bot
DISCORD_ADMIN_IDS = [
    541663310009860116
]
