import aiosqlite
from config import DB_PATH
from datetime import date


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                banned_count INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            INSERT OR IGNORE INTO stats (id, banned_count) VALUES (1, 0)
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS image_usage (
                user_id INTEGER NOT NULL,
                usage_date TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, usage_date)
            )
        """)
        await db.commit()


async def save_message(user_id: int, role: str, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content)
        )
        await db.commit()


async def get_history(user_id: int, limit: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT role, content FROM messages
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
    return [{"role": row[0], "content": row[1]} for row in reversed(rows)]


async def clear_history(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
        await db.commit()


async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(DISTINCT user_id) FROM messages") as cursor:
            users = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM messages") as cursor:
            messages = (await cursor.fetchone())[0]
        async with db.execute("SELECT banned_count FROM stats WHERE id = 1") as cursor:
            banned = (await cursor.fetchone())[0]
    return {"users": users, "messages": messages, "banned": banned}


async def increment_banned():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE stats SET banned_count = banned_count + 1 WHERE id = 1")
        await db.commit()


async def get_image_usage(user_id: int) -> int:
    """Возвращает количество генераций фото за сегодня"""
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT count FROM image_usage WHERE user_id = ? AND usage_date = ?",
            (user_id, today)
        ) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else 0


async def increment_image_usage(user_id: int):
    """Увеличивает счётчик генераций фото за сегодня"""
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO image_usage (user_id, usage_date, count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, usage_date) DO UPDATE SET count = count + 1
            """,
            (user_id, today)
        )
        await db.commit()
