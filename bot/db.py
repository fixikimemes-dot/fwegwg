from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = str(db_path)

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    full_name TEXT,
                    username TEXT,
                    bio TEXT,
                    hobbies_json TEXT DEFAULT '[]',
                    timezone TEXT NOT NULL DEFAULT 'Europe/Amsterdam',
                    morning_time TEXT NOT NULL DEFAULT '08:00',
                    midday_time TEXT NOT NULL DEFAULT '14:00',
                    evening_time TEXT NOT NULL DEFAULT '20:30',
                    onboarding_complete INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    day TEXT NOT NULL,
                    title TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 2,
                    duration_minutes INTEGER,
                    note TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_user_day ON tasks(user_id, day);

                CREATE TABLE IF NOT EXISTS checkins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    day TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_checkins_user_day ON checkins(user_id, day);

                CREATE TABLE IF NOT EXISTS ai_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    day TEXT NOT NULL,
                    analysis TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_ai_user_day ON ai_analyses(user_id, day);

                CREATE TABLE IF NOT EXISTS calories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    day TEXT NOT NULL,
                    meal_name TEXT,
                    calories INTEGER NOT NULL,
                    protein_grams REAL,
                    fat_grams REAL,
                    carbs_grams REAL,
                    note TEXT,
                    image_file_id TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_calories_user_day ON calories(user_id, day);
                """
            )
            await db.commit()

    async def _execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, params)
            await db.commit()

    async def _fetchone(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def _fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def ensure_user(
        self,
        telegram_id: int,
        full_name: str | None,
        username: str | None,
        timezone: str,
        morning_time: str,
        midday_time: str,
        evening_time: str,
    ) -> dict[str, Any]:

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            await db.execute(
                """
                INSERT INTO users (
                    telegram_id, full_name, username, timezone, morning_time, midday_time, evening_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    full_name=excluded.full_name,
                    username=excluded.username,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (telegram_id, full_name, username, timezone, morning_time, midday_time, evening_time),
            )

            await db.commit()

            cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            row = await cursor.fetchone()

            return self._normalize_user(dict(row))

    async def get_user(self, telegram_id: int) -> dict[str, Any] | None:
        row = await self._fetchone("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        return self._normalize_user(row) if row else None

    async def list_users(self) -> list[dict[str, Any]]:
        rows = await self._fetchall("SELECT * FROM users")
        return [self._normalize_user(row) for row in rows]

    async def update_profile(
        self,
        telegram_id: int,
        bio: str,
        hobbies: list[str],
        timezone: str,
        morning_time: str,
        midday_time: str,
        evening_time: str,
    ) -> None:

        await self._execute(
            """
            UPDATE users
            SET bio = ?,
                hobbies_json = ?,
                timezone = ?,
                morning_time = ?,
                midday_time = ?,
                evening_time = ?,
                onboarding_complete = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
            """,
            (
                bio.strip(),
                json.dumps(hobbies, ensure_ascii=False),
                timezone,
                morning_time,
                midday_time,
                evening_time,
                telegram_id,
            ),
        )

    async def add_calorie_entry(
        self,
        telegram_id: int,
        day: str,
        meal_name: str,
        calories: int,
        protein_grams: float | None,
        fat_grams: float | None,
        carbs_grams: float | None,
        note: str | None,
        image_file_id: str | None,
    ) -> None:

        user = await self.get_user(telegram_id)
        if not user:
            return

        await self._execute(
            """
            INSERT INTO calories (
                user_id, day, meal_name, calories,
                protein_grams, fat_grams, carbs_grams,
                note, image_file_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                day,
                meal_name,
                calories,
                protein_grams,
                fat_grams,
                carbs_grams,
                note,
                image_file_id,
            ),
        )

    async def get_calorie_entries_for_day(self, telegram_id: int, day: str) -> list[dict[str, Any]]:

        user = await self.get_user(telegram_id)
        if not user:
            return []

        return await self._fetchall(
            """
            SELECT *
            FROM calories
            WHERE user_id = ? AND day = ?
            ORDER BY id ASC
            """,
            (user["id"], day),
        )

    async def get_calorie_total_for_day(self, telegram_id: int, day: str) -> int:

        user = await self.get_user(telegram_id)
        if not user:
            return 0

        row = await self._fetchone(
            """
            SELECT SUM(calories) as total
            FROM calories
            WHERE user_id = ? AND day = ?
            """,
            (user["id"], day),
        )

        return int(row["total"] or 0) if row else 0

    @staticmethod
    def _normalize_user(row: dict[str, Any]) -> dict[str, Any]:

        row = dict(row)

        row["hobbies"] = json.loads(row.pop("hobbies_json") or "[]")
        row["onboarding_complete"] = bool(row["onboarding_complete"])

        return row
