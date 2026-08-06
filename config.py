import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8874409890:AAF10XCIfde3cGt2qHPT5vmZwmcPSJNjV8k")

# Target players to monitor
YOUTUBERS = {
    "MrLalalashkaXXL": {
        "name": "Лололошка",
        "nick": "MrLalalashkaXXL",
        "url": "https://vimeworld.com/player/MrLalalashkaXXL",
        "icon": "🎬",
    },
    "F1xPlay_": {
        "name": "Фиксплей",
        "nick": "F1xPlay_",
        "url": "https://vimeworld.com/player/F1xPlay_",
        "icon": "🎮",
    }
}

# Creator profile info
CREATOR = {
    "name": "dima_286812312",
    "nick": "dima_286812312",
    "url": "https://vimeworld.com/player/dima_286812312",
    "icon": "👑",
}

# Check interval in seconds for background monitoring (2 seconds)
CHECK_INTERVAL = 2

# Database path
DB_PATH = os.getenv("DB_PATH", "bot_data.db")
