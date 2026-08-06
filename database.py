import aiosqlite
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)

async def init_db():
    """Initializes SQLite database tables."""
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
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    logger.info("Database initialized successfully.")

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

async def get_player_last_status(target_nick: str) -> bool:
    """Gets the last recorded online status of a player (True/False). Defaults to False if unknown."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT is_online FROM player_status WHERE target_nick = ?",
            (target_nick,)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else False

async def update_player_last_status(target_nick: str, is_online: bool):
    """Updates the recorded online status for a player."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO player_status (target_nick, is_online, last_checked)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(target_nick) DO UPDATE SET
                is_online = excluded.is_online,
                last_checked = CURRENT_TIMESTAMP
            """,
            (target_nick, 1 if is_online else 0)
        )
        await db.commit()
