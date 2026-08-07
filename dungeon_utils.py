from datetime import datetime, timezone, timedelta
from config import DUNGEONS

MSK_TZ = timezone(timedelta(hours=3))

def get_now_msk() -> datetime:
    """Returns current datetime in Moscow timezone (UTC+3)."""
    return datetime.now(MSK_TZ)

def get_next_hard_dungeon(now: datetime = None) -> dict:
    """Calculates next Hard Dungeon (:10, :40)."""
    now = now or get_now_msk()
    minute = now.minute
    
    if minute < 10:
        target = now.replace(minute=10, second=0, microsecond=0)
    elif minute < 40:
        target = now.replace(minute=40, second=0, microsecond=0)
    else:
        # Next hour at :10
        next_hour = now + timedelta(hours=1)
        target = next_hour.replace(minute=10, second=0, microsecond=0)
        
    delta_sec = int((target - now).total_seconds())
    mins_left = delta_sec // 60
    secs_left = delta_sec % 60
    
    return {
        "key": "dungeon_hard",
        "name": DUNGEONS["dungeon_hard"]["name"],
        "icon": DUNGEONS["dungeon_hard"]["icon"],
        "formatted_time": target.strftime("%H:%M"),
        "total_seconds": delta_sec,
        "mins_left": mins_left,
        "secs_left": secs_left,
    }

def get_next_medium_dungeon(now: datetime = None) -> dict:
    """Calculates next Medium Dungeon (:15, :45)."""
    now = now or get_now_msk()
    minute = now.minute
    
    if minute < 15:
        target = now.replace(minute=15, second=0, microsecond=0)
    elif minute < 45:
        target = now.replace(minute=45, second=0, microsecond=0)
    else:
        # Next hour at :15
        next_hour = now + timedelta(hours=1)
        target = next_hour.replace(minute=15, second=0, microsecond=0)
        
    delta_sec = int((target - now).total_seconds())
    mins_left = delta_sec // 60
    secs_left = delta_sec % 60
    
    return {
        "key": "dungeon_medium",
        "name": DUNGEONS["dungeon_medium"]["name"],
        "icon": DUNGEONS["dungeon_medium"]["icon"],
        "formatted_time": target.strftime("%H:%M"),
        "total_seconds": delta_sec,
        "mins_left": mins_left,
        "secs_left": secs_left,
    }

def get_next_jeju_raid(now: datetime = None) -> dict:
    """Calculates next Jeju Island Raid (18:00 MSK)."""
    now = now or get_now_msk()
    target = now.replace(hour=18, minute=0, second=0, microsecond=0)
    
    if now >= target:
        # Tomorrow at 18:00 MSK
        target += timedelta(days=1)
        
    delta_sec = int((target - now).total_seconds())
    hours_left = delta_sec // 3600
    mins_left = (delta_sec % 3600) // 60
    
    time_str = target.strftime("%H:%M")
    date_str = "сегодня" if target.date() == now.date() else "завтра"
    
    return {
        "key": "dungeon_jeju",
        "name": DUNGEONS["dungeon_jeju"]["name"],
        "icon": DUNGEONS["dungeon_jeju"]["icon"],
        "formatted_time": f"{time_str} МСК ({date_str})",
        "total_seconds": delta_sec,
        "hours_left": hours_left,
        "mins_left": mins_left,
    }

def generate_dungeon_schedule_text() -> str:
    """Generates user-friendly text for upcoming dungeons and raids schedule."""
    hard = get_next_hard_dungeon()
    medium = get_next_medium_dungeon()
    jeju = get_next_jeju_raid()
    now_str = get_now_msk().strftime("%H:%M:%S")
    
    text = (
        "🗡 <b>Расписание Подземелий и Рейдов (Solo Leveling VimeWorld):</b>\n\n"
        f"1. {hard['icon']} <b>{hard['name']}</b> ({DUNGEONS['dungeon_hard']['schedule_desc']})\n"
        f"   🕒 Ближайшее: <b>{hard['formatted_time']}</b> (через <b>{hard['mins_left']} мин</b>)\n\n"
        f"2. {medium['icon']} <b>{medium['name']}</b> ({DUNGEONS['dungeon_medium']['schedule_desc']})\n"
        f"   🕒 Ближайшее: <b>{medium['formatted_time']}</b> (через <b>{medium['mins_left']} мин</b>)\n\n"
        f"3. {jeju['icon']} <b>{jeju['name']}</b> ({DUNGEONS['dungeon_jeju']['schedule_desc']})\n"
        f"   🕒 Ближайшее: <b>{jeju['formatted_time']}</b> (через <b>{jeju['hours_left']} ч {jeju['mins_left']} мин</b>)\n\n"
        f"🔔 <i>Уведомления и голосовые анонсы приходят ровно за 2 минуты до старта!</i>\n"
        f"🕒 <i>Текущее время (МСК): {now_str}</i>"
    )
    return text
