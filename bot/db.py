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
                    hobbies_json TEXT NOT NULL DEFAULT '[]',
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

                CREATE INDEX IF NOT EXISTS idx_tasks_user_day
                ON tasks(user_id, day);

                CREATE TABLE IF NOT EXISTS checkins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    day TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_checkins_user_day
                ON checkins(user_id, day);

                CREATE TABLE IF NOT EXISTS ai_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    day TEXT NOT NULL,
                    analysis TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_ai_user_day
                ON ai_analyses(user_id, day);

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

                CREATE INDEX IF NOT EXISTS idx_calories_user_day
                ON calories(user_id, day);
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
                    telegram_id,
                    full_name,
                    username,
                    timezone,
                    morning_time,
                    midday_time,
                    evening_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    full_name = COALESCE(excluded.full_name, users.full_name),
                    username = COALESCE(excluded.username, users.username),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    telegram_id,
                    full_name,
                    username,
                    timezone,
                    morning_time,
                    midday_time,
                    evening_time,
                ),
            )
            await db.commit()

            cursor = await db.execute(
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,),
            )
            row = await cursor.fetchone()
            return self._normalize_user(dict(row))

    async def get_user(self, telegram_id: int) -> dict[str, Any] | None:
        row = await self._fetchone(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        return self._normalize_user(row) if row else None

    async def get_user_by_telegram_id(self, telegram_id: int) -> dict[str, Any] | None:
        return await self.get_user(telegram_id)

    async def list_users(self) -> list[dict[str, Any]]:
        rows = await self._fetchall("SELECT * FROM users ORDER BY id ASC")
        return [self._normalize_user(row) for row in rows]

    async def user_profile_is_complete(self, telegram_id: int) -> bool:
        user = await self.get_user(telegram_id)
        if not user:
            return False

        return bool(
            user.get("onboarding_complete")
            and (user.get("full_name") or "").strip()
            and (user.get("bio") or "").strip()
            and user.get("hobbies")
        )

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
        clean_hobbies = [item.strip() for item in hobbies if item and item.strip()]

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
                (bio or "").strip(),
                json.dumps(clean_hobbies, ensure_ascii=False),
                timezone,
                morning_time,
                midday_time,
                evening_time,
                telegram_id,
            ),
        )

    async def update_schedule(
        self,
        telegram_id: int,
        timezone: str | None = None,
        morning_time: str | None = None,
        midday_time: str | None = None,
        evening_time: str | None = None,
    ) -> None:
        user = await self.get_user(telegram_id)
        if not user:
            return

        await self._execute(
            """
            UPDATE users
            SET timezone = ?,
                morning_time = ?,
                midday_time = ?,
                evening_time = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
            """,
            (
                timezone or user["timezone"],
                morning_time or user["morning_time"],
                midday_time or user["midday_time"],
                evening_time or user["evening_time"],
                telegram_id,
            ),
        )

    async def add_task(
        self,
        telegram_id: int,
        day: str,
        title: str,
        priority: int,
        duration_minutes: int | None,
        note: str | None,
    ) -> int:
        user = await self.get_user(telegram_id)
        if not user:
            raise ValueError("User not found")

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO tasks (
                    user_id,
                    day,
                    title,
                    priority,
                    duration_minutes,
                    note
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    day,
                    (title or "").strip(),
                    int(priority or 2),
                    duration_minutes,
                    (note or "").strip() or None,
                ),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def get_tasks_for_day(self, telegram_id: int, day: str) -> list[dict[str, Any]]:
        user = await self.get_user(telegram_id)
        if not user:
            return []

        return await self._fetchall(
            """
            SELECT *
            FROM tasks
            WHERE user_id = ? AND day = ?
            ORDER BY
                CASE status
                    WHEN 'pending' THEN 0
                    WHEN 'done' THEN 1
                    WHEN 'skipped' THEN 2
                    ELSE 3
                END,
                priority DESC,
                id ASC
            """,
            (user["id"], day),
        )

    async def get_task(self, task_id: int) -> dict[str, Any] | None:
        return await self._fetchone(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        )

    async def update_task_status(self, task_id: int, status: str) -> None:
        if status == "done":
            await self._execute(
                """
                UPDATE tasks
                SET status = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, task_id),
            )
        else:
            await self._execute(
                """
                UPDATE tasks
                SET status = ?, completed_at = NULL
                WHERE id = ?
                """,
                (status, task_id),
            )

    async def delete_task(self, task_id: int) -> None:
        await self._execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,),
        )

    async def save_checkin(self, telegram_id: int, day: str, kind: str, summary: str) -> None:
        user = await self.get_user(telegram_id)
        if not user:
            return

        await self._execute(
            """
            INSERT INTO checkins (user_id, day, kind, summary)
            VALUES (?, ?, ?, ?)
            """,
            (user["id"], day, kind, (summary or "").strip()),
        )

    async def get_checkins_for_day(self, telegram_id: int, day: str) -> list[dict[str, Any]]:
        user = await self.get_user(telegram_id)
        if not user:
            return []

        return await self._fetchall(
            """
            SELECT *
            FROM checkins
            WHERE user_id = ? AND day = ?
            ORDER BY id ASC
            """,
            (user["id"], day),
        )

    async def save_ai_analysis(self, telegram_id: int, day: str, analysis: str) -> None:
        user = await self.get_user(telegram_id)
        if not user:
            return

        await self._execute(
            """
            INSERT INTO ai_analyses (user_id, day, analysis)
            VALUES (?, ?, ?)
            """,
            (user["id"], day, (analysis or "").strip()),
        )

    async def get_latest_analysis(self, telegram_id: int, day: str) -> dict[str, Any] | None:
        user = await self.get_user(telegram_id)
        if not user:
            return None

        return await self._fetchone(
            """
            SELECT *
            FROM ai_analyses
            WHERE user_id = ? AND day = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user["id"], day),
        )

    async def get_recent_history(self, telegram_id: int, days: int = 7) -> dict[str, list[dict[str, Any]]]:
        user = await self.get_user(telegram_id)
        if not user:
            return {"tasks": [], "checkins": []}

        tasks = await self._fetchall(
            """
            SELECT *
            FROM tasks
            WHERE user_id = ?
              AND date(day) >= date('now', ?)
            ORDER BY day DESC, priority DESC, id ASC
            """,
            (user["id"], f"-{days} day"),
        )

        checkins = await self._fetchall(
            """
            SELECT *
            FROM checkins
            WHERE user_id = ?
              AND date(day) >= date('now', ?)
            ORDER BY day DESC, id ASC
            """,
            (user["id"], f"-{days} day"),
        )

        return {"tasks": tasks, "checkins": checkins}

    async def add_calorie_entry(
        self,
        telegram_id: int,
        day: str,
        meal_name: str,
        calories: int,
        protein_grams: float | None = None,
        fat_grams: float | None = None,
        carbs_grams: float | None = None,
        note: str | None = None,
        image_file_id: str | None = None,
    ) -> int:
        user = await self.get_user(telegram_id)
        if not user:
            raise ValueError("User not found")

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO calories (
                    user_id,
                    day,
                    meal_name,
                    calories,
                    protein_grams,
                    fat_grams,
                    carbs_grams,
                    note,
                    image_file_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    day,
                    (meal_name or "").strip() or "Блюдо",
                    int(calories),
                    protein_grams,
                    fat_grams,
                    carbs_grams,
                    (note or "").strip() or None,
                    image_file_id,
                ),
            )
            await db.commit()
            return int(cursor.lastrowid)

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
            SELECT SUM(calories) AS total
            FROM calories
            WHERE user_id = ? AND day = ?
            """,
            (user["id"], day),
        )

        return int(row["total"] or 0) if row else 0

    async def export_dataset(self, telegram_id: int, days: int = 30) -> dict[str, list[dict[str, Any]]]:
        user = await self.get_user(telegram_id)
        if not user:
            return {"tasks": [], "checkins": [], "analyses": [], "calories": []}

        tasks = await self._fetchall(
            """
            SELECT
                day,
                title,
                priority,
                duration_minutes,
                note,
                status,
                created_at,
                completed_at
            FROM tasks
            WHERE user_id = ?
              AND date(day) >= date('now', ?)
            ORDER BY day DESC, id DESC
            """,
            (user["id"], f"-{days} day"),
        )

        checkins = await self._fetchall(
            """
            SELECT
                day,
                kind,
                summary,
                created_at
            FROM checkins
            WHERE user_id = ?
              AND date(day) >= date('now', ?)
            ORDER BY day DESC, id DESC
            """,
            (user["id"], f"-{days} day"),
        )

        analyses = await self._fetchall(
            """
            SELECT
                day,
                analysis,
                created_at
            FROM ai_analyses
            WHERE user_id = ?
              AND date(day) >= date('now', ?)
            ORDER BY day DESC, id DESC
            """,
            (user["id"], f"-{days} day"),
        )

        calories = await self._fetchall(
            """
            SELECT
                day,
                meal_name,
                calories,
                protein_grams,
                fat_grams,
                carbs_grams,
                note,
                image_file_id,
                created_at
            FROM calories
            WHERE user_id = ?
              AND date(day) >= date('now', ?)
            ORDER BY day DESC, id DESC
            """,
            (user["id"], f"-{days} day"),
        )

        return {
            "tasks": tasks,
            "checkins": checkins,
            "analyses": analyses,
            "calories": calories,
        }

    @staticmethod
    def _normalize_user(row: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(row)

        hobbies_raw = normalized.pop("hobbies_json", "[]")
        try:
            normalized["hobbies"] = json.loads(hobbies_raw or "[]")
        except json.JSONDecodeError:
            normalized["hobbies"] = []

        normalized["onboarding_complete"] = bool(normalized.get("onboarding_complete", 0))
        return normalized
