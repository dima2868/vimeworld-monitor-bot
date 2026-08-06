import os
import aiosqlite
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)

async def init_db():
    """Initializes SQLite database tables and ensures target directory exists."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER,
                target_nick TEXT,
                PRIMARY KEY (user_id, target_nick)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS player_status (
                target_nick TEXT PRIMARY KEY,
                is_online INTEGER,
                last_state TEXT DEFAULT 'OFFLINE',
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Ensure column last_state exists for database migrations
        try:
            await db.execute("ALTER TABLE player_status ADD COLUMN last_state TEXT DEFAULT 'OFFLINE'")
        except Exception:
            pass
            
        await db.commit()
    logger.info(f"Database initialized successfully at: {DB_PATH}")

async def add_user(user_id: int):
    """Registers a new user if not exists."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user_id,)
        )
        await db.commit()

async def subscribe_user(user_id: int, target_nick: str):
    """Subscribes a user to monitor a specific player."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO subscriptions (user_id, target_nick) VALUES (?, ?)",
            (user_id, target_nick)
        )
        await db.commit()

async def unsubscribe_user(user_id: int, target_nick: str):
    """Unsubscribes a user from monitoring a specific player."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM subscriptions WHERE user_id = ? AND target_nick = ?",
            (user_id, target_nick)
        )
        await db.commit()

async def is_subscribed(user_id: int, target_nick: str) -> bool:
    """Checks if a user is subscribed to a player."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM subscriptions WHERE user_id = ? AND target_nick = ?",
            (user_id, target_nick)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None

async def get_user_subscriptions(user_id: int) -> list:
    """Gets list of target nicks a user is subscribed to."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT target_nick FROM subscriptions WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_subscribers_for_player(target_nick: str) -> list:
    """Gets all user_ids subscribed to a specific player."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM subscriptions WHERE target_nick = ?",
            (target_nick,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def has_player_state(target_nick: str) -> bool:
    """Checks if player state exists in database."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM player_status WHERE target_nick = ?",
            (target_nick,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None

async def get_player_last_state(target_nick: str) -> str:
    """Gets the last recorded state of a player ('OFFLINE', 'LOBBY', 'SOLOLEVELING', 'OTHER_GAME')."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT last_state FROM player_status WHERE target_nick = ?",
            (target_nick,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if (row and row[0]) else "OFFLINE"

async def update_player_last_state(target_nick: str, state: str, is_online: bool):
    """Updates the recorded state for a player."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO player_status (target_nick, is_online, last_state, last_checked)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(target_nick) DO UPDATE SET
                is_online = excluded.is_online,
                last_state = excluded.last_state,
                last_checked = CURRENT_TIMESTAMP
            """,
            (target_nick, 1 if is_online else 0, state)
        )
        await db.commit()

# --- ADMIN STATS FUNCTIONS ---

async def get_total_users_count() -> int:
    """Returns total count of registered bot users."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_active_subscribers_count() -> int:
    """Returns count of unique users who have at least 1 active subscription."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(DISTINCT user_id) FROM subscriptions") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_subscriptions_breakdown() -> dict:
    """Returns dictionary mapping target_nick to subscriber count."""
    result = {}
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT target_nick, COUNT(*) FROM subscriptions GROUP BY target_nick") as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                result[row[0]] = row[1]
    return result
