import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8874409890:AAF10XCIfde3cGt2qHPT5vmZwmcPSJNjV8k")

# Admin User IDs
ADMIN_IDS = [5881764740]

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

# Persistent database path (supports Railway Volume or data/ directory)
raw_db_path = os.getenv("DB_PATH")
if not raw_db_path:
    volume_path = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    if volume_path:
        raw_db_path = os.path.join(volume_path, "bot_data.db")
    else:
        raw_db_path = os.path.join("data", "bot_data.db")

DB_PATH = raw_db_path
