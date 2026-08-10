import math
import aiohttp
import logging
from config import YOUTUBERS, CREATOR

logger = logging.getLogger(__name__)

PROFILE_API_URL = "https://api.vimeworld.com/user/name/{nickname}"
SESSION_API_URL = "https://api.vimeworld.com/user/name/{nickname}/session"
STATS_API_URL = "https://api.vimeworld.com/user/name/{nickname}/stats"

SUFFIXES = [
    "", "K", "M", "B", "T", "QA", "QI", "SX", "SP", "OC", "NO", "DC",
    "UDC", "DDC", "TDC", "QAD", "QID", "SXD", "SPD", "OCD", "NOD", "VGN",
    "UVG", "DVG", "TVG", "QAV", "QIV", "SXV", "SPV", "OCV", "NOV", "CENT"
]

REBIRTH_RANK_MAP = {
    72: "Герой SSS+", 71: "Герой SSS", 70: "Герой SS+", 69: "Герой SS",
    68: "Герой S+", 67: "Герой S", 66: "Герой AAA+", 65: "Герой AAA",
    64: "Герой AA+", 63: "Герой AA", 62: "Герой A+", 61: "Герой A",
    60: "Герой BBB+", 59: "Герой BBB", 58: "Герой BB+", 57: "Герой BB",
    56: "Герой B+", 55: "Герой B", 54: "Герой CCC+", 53: "Герой CCC",
    52: "Герой CC+", 51: "Герой CC", 50: "Герой C+", 49: "Герой C",
    48: "Герой DDD+", 47: "Герой DDD", 46: "Герой DD+", 45: "Герой DD",
    44: "Герой D+", 43: "Герой D", 42: "Герой EEE",
    41: "SSS+", 40: "SSS", 39: "SS+", 38: "SS", 37: "S+", 36: "S",
    35: "AAA+", 34: "AAA", 33: "AA+", 32: "AA", 31: "A+", 30: "A",
    29: "BBB+", 28: "BBB", 27: "BB+", 26: "BB", 25: "B+", 24: "B",
    23: "CCC+", 22: "CCC", 21: "CC+", 20: "CC", 19: "C+", 18: "C",
    17: "DDD+", 16: "DDD", 15: "DD+", 14: "DD", 13: "D+", 12: "D",
    11: "EEE+", 10: "EEE", 9: "EE+", 8: "EE", 7: "E+", 6: "E",
    5: "FFF+", 4: "FFF", 3: "FF+", 2: "FF", 1: "F+", 0: "F"
}

def get_rebirth_rank_title(rebirth_count: int) -> str:
    """Returns official Solo Leveling rank title (e.g. Герой SSS+, Герой EEE, SSS... F) based on rebirth count."""
    if rebirth_count >= 72:
        return "Герой SSS+"
    return REBIRTH_RANK_MAP.get(rebirth_count, "F")

def format_big_number(val) -> str:
    """Formats large Solo Leveling numbers into clean VimeWorld style (e.g. 82.5DVG, 13.9OCD)."""
    if not val or val == 0:
        return "0"
    try:
        val = float(val)
        if val < 1000:
            return f"{val:.0f}"
        
        exp = int(math.log10(val) // 3)
        if exp < len(SUFFIXES):
            scaled = val / (10 ** (exp * 3))
            return f"{scaled:.1f}{SUFFIXES[exp]}"
        return f"{val:.2e}"
    except Exception:
        return str(val)

async def fetch_player_status(nickname: str) -> dict:
    """
    Fetches real-time online status and session details for a nickname.
    States: OFFLINE, LOBBY, SOLOLEVELING, OTHER_GAME
    """
    default_result = {
        "nickname": nickname,
        "is_online": False,
        "state": "OFFLINE",
        "game_mode": "Offline",
        "status_display": "🔴 Не в сети",
        "level": None,
        "rank": None,
        "url": f"https://vimeworld.com/player/{nickname}"
    }

    async with aiohttp.ClientSession() as session:
        try:
            # 1. Fetch real-time session status
            async with session.get(SESSION_API_URL.format(nickname=nickname), timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    online_data = data.get("online", {})
                    is_online = online_data.get("value", False)
                    game = online_data.get("game", "")
                    message = online_data.get("message", "")

                    default_result["is_online"] = is_online
                    if is_online:
                        if game == "SOLOLEVELING" or "Solo Leveling" in message or "Лоботомия" in message:
                            default_result["state"] = "SOLOLEVELING"
                            default_result["game_mode"] = "Solo Leveling 🗡"
                            default_result["status_display"] = "🟢 В ИГРЕ (Solo Leveling)"
                        elif message == "В лобби" or not game:
                            default_result["state"] = "LOBBY"
                            default_result["game_mode"] = "Лобби"
                            default_result["status_display"] = "🟡 В Лобби"
                        else:
                            default_result["state"] = "OTHER_GAME"
                            default_result["game_mode"] = message or game
                            default_result["status_display"] = f"🔵 Играет в {message or game}"
        except Exception as e:
            logger.warning(f"Error fetching session for {nickname}: {e}")

        try:
            # 2. Fetch basic profile data (level, donator rank)
            async with session.get(PROFILE_API_URL.format(nickname=nickname), timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        u = data[0]
                        default_result["level"] = u.get("level", 1)
                        default_result["rank"] = u.get("rank", "USER")
                        default_result["nickname"] = u.get("username", nickname)
        except Exception as e:
            logger.warning(f"Error fetching user profile for {nickname}: {e}")

    return default_result


async def fetch_full_player_profile(nickname: str) -> dict:
    """
    Fetches comprehensive player profile including level, donator rank, and Solo Leveling stats.
    Supports rebirth calculation across all seasons (SOLOLEVELING8 down to SOLOLEVELING).
    """
    status_data = await fetch_player_status(nickname)
    
    result = {
        "nickname": status_data["nickname"],
        "is_online": status_data["is_online"],
        "status_display": status_data["status_display"],
        "level": status_data.get("level", 0),
        "level_pct": 0,
        "rank": status_data.get("rank", "USER"),
        "played_hours": 0,
        "guild_name": None,
        "guild_level": 0,
        "sl_rebirth": 0,
        "sl_rebirth_rank": "F",
        "sl_damage_raw": 0,
        "sl_damage_formatted": "0",
        "sl_gold_raw": 0,
        "sl_gold_formatted": "0",
        "sl_upgrade_points": 0,
        "head_url": f"https://render.vimeworld.com/head/{status_data['nickname']}.png",
        "url": f"https://vimeworld.com/player/{status_data['nickname']}",
        "exists": False,
        "sl_stats_loaded": False
    }

    async with aiohttp.ClientSession() as session:
        try:
            # Fetch user info API
            async with session.get(PROFILE_API_URL.format(nickname=nickname), timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        u = data[0]
                        result["exists"] = True
                        result["nickname"] = u.get("username", nickname)
                        result["level"] = u.get("level", 0)
                        result["level_pct"] = int(u.get("levelPercentage", 0) * 100)
                        result["rank"] = u.get("rank", "USER")
                        result["played_hours"] = round(u.get("playedSeconds", 0) / 3600, 1)
                        result["head_url"] = f"https://render.vimeworld.com/head/{u.get('username', nickname)}.png"
                        
                        guild_info = u.get("guild")
                        if guild_info:
                            result["guild_name"] = guild_info.get("name")
                            result["guild_level"] = guild_info.get("level", 0)
                else:
                    return result
        except Exception as e:
            logger.warning(f"Error fetching full profile for {nickname}: {e}")
            return result

        try:
            # Fetch stats API (Solo Leveling stats)
            async with session.get(STATS_API_URL.format(nickname=nickname), timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stats = data.get("stats", {})
                    
                    best_rebirth = 0
                    current_season_stats = None

                    # Check all season keys from SOLOLEVELING8 down to SOLOLEVELING
                    sl_keys = ["SOLOLEVELING8", "SOLOLEVELING7", "SOLOLEVELING6", "SOLOLEVELING5", "SOLOLEVELING4", "SOLOLEVELING3", "SOLOLEVELING2", "SOLOLEVELING"]
                    for k in sl_keys:
                        if k in stats:
                            if current_season_stats is None:
                                current_season_stats = stats[k].get("global", {})
                            r_val = stats[k].get("global", {}).get("rebirth", 0)
                            if r_val > best_rebirth:
                                best_rebirth = r_val

                    result["sl_stats_loaded"] = True

                    if current_season_stats:
                        dmg = current_season_stats.get("damage_power", 0)
                        gold = current_season_stats.get("gold", 0)
                        upg = current_season_stats.get("upgrade_points", 0)

                        result["sl_damage_raw"] = dmg
                        result["sl_damage_formatted"] = format_big_number(dmg)
                        result["sl_gold_raw"] = gold
                        result["sl_gold_formatted"] = format_big_number(gold)
                        result["sl_upgrade_points"] = upg

                    result["sl_rebirth"] = best_rebirth
                    result["sl_rebirth_rank"] = get_rebirth_rank_title(best_rebirth)
        except Exception as e:
            logger.warning(f"Error fetching stats for {nickname}: {e}")

    return result
