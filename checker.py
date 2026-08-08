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
    40: "SSS", 39: "SS+", 38: "SS", 37: "S+", 36: "S",
    35: "AAA+", 34: "AAA", 33: "AA+", 32: "AA", 31: "A+", 30: "A",
    29: "BBB+", 28: "BBB", 27: "BB+", 26: "BB", 25: "B+", 24: "B",
    23: "CCC+", 22: "CCC", 21: "CC+", 20: "CC", 19: "C+", 18: "C",
    17: "DDD+", 16: "DDD", 15: "DD+", 14: "DD", 13: "D+", 12: "D",
    11: "EEE+", 10: "EEE", 9: "EE+", 8: "EE", 7: "E+", 6: "E",
    5: "FFF+", 4: "FFF", 3: "FF+", 2: "FF", 1: "F+", 0: "F"
}

def get_rebirth_rank_title(rebirth_count: int) -> str:
    """Returns official Solo Leveling rank title (e.g. SSS, SS+, SS, S, AAA... F) based on rebirth count."""
    if rebirth_count >= 40:
        return "SSS"
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

                    default_result["is_online"] = is_online
                    if is_online:
                        if game == "SOLOLEVELING":
                            default_result["state"] = "SOLOLEVELING"
                            default_result["status_display"] = "🟢 На Solo Leveling"
                        elif game == "LOBBY" or not game:
                            default_result["state"] = "LOBBY"
                            default_result["status_display"] = "🟡 В лобби VimeWorld"
                        else:
                            default_result["state"] = "OTHER_GAME"
                            default_result["status_display"] = f"🟢 Играет в {game}"
                    else:
                        default_result["state"] = "OFFLINE"
                        default_result["status_display"] = "🔴 Не в сети"
        except Exception as e:
            logger.warning(f"Error fetching session status for {nickname}: {e}")

        try:
            # 2. Fetch base profile
            async with session.get(PROFILE_API_URL.format(nickname=nickname), timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        user_info = data[0]
                        default_result["level"] = user_info.get("level")
                        default_result["rank"] = user_info.get("rank")
        except Exception as e:
            logger.warning(f"Error fetching profile for {nickname}: {e}")

    return default_result

async def fetch_full_player_profile(nickname: str) -> dict:
    """
    Fetches comprehensive player profile including VimeWorld stats and Solo Leveling data.
    """
    status_info = await fetch_player_status(nickname)
    
    result = {
        **status_info,
        "exists": False,
        "played_hours": 0,
        "level_pct": 0,
        "prime": False,
        "guild_name": None,
        "guild_level": None,
        "skin_url": f"https://skin.vimeworld.com/body/{nickname}/360.png",
        "head_url": f"https://skin.vimeworld.com/head/{nickname}/64.png",
        # Solo Leveling stats
        "sl_rebirth": 0,
        "sl_rebirth_rank": "F",
        "sl_damage_raw": 0,
        "sl_damage_formatted": "0",
        "sl_gold_raw": 0,
        "sl_gold_formatted": "0",
        "sl_upgrade_points": 0,
    }

    async with aiohttp.ClientSession() as session:
        try:
            # 1. Base profile
            async with session.get(PROFILE_API_URL.format(nickname=nickname), timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        u = data[0]
                        result["exists"] = True
                        result["nickname"] = u.get("username", nickname)
                        result["level"] = u.get("level", 0)
                        result["level_pct"] = int((u.get("levelPercentage", 0) or 0) * 100)
                        result["rank"] = u.get("rank", "USER")
                        result["prime"] = u.get("prime", False)
                        
                        played_secs = u.get("playedSeconds", 0) or 0
                        result["played_hours"] = played_secs // 3600
                        
                        guild = u.get("guild")
                        if guild:
                            result["guild_name"] = guild.get("name")
                            result["guild_level"] = guild.get("level")
        except Exception as e:
            logger.warning(f"Error fetching full profile for {nickname}: {e}")

        # 2. Stats API for Solo Leveling
        try:
            async with session.get(STATS_API_URL.format(nickname=nickname), timeout=5) as resp:
                if resp.status == 200:
                    stats_json = await resp.json()
                    stats = stats_json.get("stats", {})
                    
                    best_damage = 0
                    best_rebirth = 0
                    best_gold = 0
                    best_upgrades = 0
                    
                    for k, v in stats.items():
                        if "SOLOLEVELING" in k and isinstance(v, dict):
                            g = v.get("global", {})
                            dmg = g.get("damage_power", 0) or 0
                            reb = g.get("rebirth", 0) or 0
                            gold = g.get("gold", 0) or 0
                            upg = g.get("upgrade_points", 0) or 0
                            
                            if reb > best_rebirth:
                                best_rebirth = reb
                            if dmg > best_damage:
                                best_damage = dmg
                            if gold > best_gold:
                                best_gold = gold
                            if upg > best_upgrades:
                                best_upgrades = upg

                    result["sl_rebirth"] = best_rebirth
                    result["sl_rebirth_rank"] = get_rebirth_rank_title(best_rebirth)
                    result["sl_damage_raw"] = best_damage
                    result["sl_damage_formatted"] = format_big_number(best_damage)
                    result["sl_gold_raw"] = best_gold
                    result["sl_gold_formatted"] = format_big_number(best_gold)
                    result["sl_upgrade_points"] = best_upgrades
        except Exception as e:
            logger.warning(f"Error fetching stats for {nickname}: {e}")

    return result
