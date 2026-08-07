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

# Dungeon & Raid definitions
DUNGEONS = {
    "dungeon_hard": {
        "name": "Сложное подземелье",
        "icon": "🗡",
        "schedule_desc": "каждые :10 и :40 минут",
        "minutes": [10, 40],
        "alert_minutes": [8, 38],
    },
    "dungeon_medium": {
        "name": "Среднее подземелье",
        "icon": "⚔️",
        "schedule_desc": "каждые :15 и :45 минут",
        "minutes": [15, 45],
        "alert_minutes": [13, 43],
    },
    "dungeon_jeju": {
        "name": "Остров Чеджу (Рейд)",
        "icon": "🌋",
        "schedule_desc": "в 18:00 МСК",
        "alert_time": (17, 58), # 17:58 MSK
        "start_time": (18, 0),  # 18:00 MSK
    }
}

# Creator profile info
CREATOR = {
    "name": "dima_286812312",
    "nick": "dima_286812312",
    "url": "https://vimeworld.com/player/dima_286812312",
    "icon": "👑",
}

# Check interval in seconds for background monitoring
CHECK_INTERVAL = 2

# Persistent database path
raw_db_path = os.getenv("DB_PATH")
if not raw_db_path:
    volume_path = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    if volume_path:
        raw_db_path = os.path.join(volume_path, "bot_data.db")
    else:
        raw_db_path = os.path.join("data", "bot_data.db")

DB_PATH = raw_db_path
