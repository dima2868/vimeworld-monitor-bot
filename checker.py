import aiohttp
import re
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

_session = None

async def get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(headers=HEADERS)
    return _session

async def fetch_player_status(nickname: str) -> dict:
    """
    Fetches real-time online status and details for a VimeWorld player.
    Classifies state:
    - OFFLINE: Not connected
    - LOBBY: Online but not in a specific game
    - SOLOLEVELING: Online playing Solo Leveling
    - OTHER_GAME: Online playing another mode
    """
    api_url = f"https://api.vimeworld.com/user/name/{nickname}/session"
    web_url = f"https://vimeworld.com/player/{nickname}"
    
    result = {
        "nickname": nickname,
        "is_online": False,
        "state": "OFFLINE",
        "status_display": "🔴 Не в сети",
        "game": None,
        "level": None,
        "rank": None,
        "avatar_url": f"https://skin.vimeworld.com/body/{nickname}/360.png",
        "url": web_url
    }

    session = await get_session()
    
    # Try VimeWorld Session API
    try:
        async with session.get(api_url, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                if isinstance(data, dict):
                    user_data = data.get("user", {})
                    online_info = data.get("online", {})
                    
                    is_online = bool(online_info.get("value", False))
                    game_mode = online_info.get("game")
                    
                    result["is_online"] = is_online
                    result["game"] = game_mode
                    result["level"] = user_data.get("level")
                    result["rank"] = user_data.get("rank")
                    
                    if not is_online:
                        result["state"] = "OFFLINE"
                        result["status_display"] = "🔴 Не в сети"
                    elif game_mode and "SOLOLEVELING" in str(game_mode).upper():
                        result["state"] = "SOLOLEVELING"
                        result["status_display"] = "🟢 На Solo Leveling"
                    elif game_mode:
                        result["state"] = "OTHER_GAME"
                        result["status_display"] = f"🔵 В игре ({game_mode})"
                    else:
                        result["state"] = "LOBBY"
                        result["status_display"] = "🟡 В лобби"
                        
                    return result
    except Exception as e:
        logger.warning(f"VimeWorld Session API request failed for {nickname}: {e}. Falling back to web scraping.")

    # Fallback to Web Scraping
    try:
        async with session.get(web_url, timeout=5) as resp:
            if resp.status == 200:
                html = await resp.text()
                
                if "vw-7ya4b" in html or "Онлайн" in html:
                    result["is_online"] = True
                    result["state"] = "LOBBY"
                    result["status_display"] = "🟢 Онлайн"
                else:
                    result["is_online"] = False
                    result["state"] = "OFFLINE"
                    result["status_display"] = "🔴 Не в сети"
                            
                lvl_match = re.search(r'(\d+)\s*уровень', html, re.IGNORECASE)
                if lvl_match:
                    result["level"] = lvl_match.group(1)
    except Exception as e:
        logger.error(f"Error scraping VimeWorld webpage for {nickname}: {e}")

    return result
