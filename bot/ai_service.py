from __future__ import annotations

from collections import Counter
from typing import Any
import os

try:
    from openai import AsyncOpenAI
except Exception:
    AsyncOpenAI = None

from .formatters import PRIORITY_LABELS, format_hobbies


class AIService:
    def __init__(self, api_key: str | None, model: str) -> None:
        base_url = os.getenv("OPENAI_BASE_URL")

        self.model = model
        self.enabled = bool(api_key and AsyncOpenAI)

        if self.enabled:
            if base_url:
                self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            else:
                self.client = AsyncOpenAI(api_key=api_key)
        else:
            self.client = None

    async def daily_analysis(
        self,
        user: dict[str, Any],
        today_tasks: list[dict[str, Any]],
        today_checkins: list[dict[str, Any]],
        recent_history: dict[str, list[dict[str, Any]]],
    ) -> str:

        if not self.enabled or not self.client:
            return "AI недоступен. Проверь OPENAI_API_KEY."

        prompt = self._build_daily_analysis_prompt(
            user, today_tasks, today_checkins, recent_history
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ты личный AI-коуч по продуктивности. Отвечай на русском."
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"Ошибка AI: {e}"

    async def coach_reply(
        self,
        user: dict[str, Any],
        today_tasks: list[dict[str, Any]],
        recent_history: dict[str, list[dict[str, Any]]],
        question: str,
    ) -> str:

        if not self.enabled or not self.client:
            return "AI недоступен. Проверь OPENAI_API_KEY."

        prompt = self._build_coach_prompt(
            user, today_tasks, recent_history, question
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ты AI-наставник по учебе и продуктивности. Отвечай коротко и практично."
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"Ошибка AI: {e}"

    @staticmethod
    def _build_daily_analysis_prompt(
        user: dict[str, Any],
        today_tasks: list[dict[str, Any]],
        today_checkins: list[dict[str, Any]],
        recent_history: dict[str, list[dict[str, Any]]],
    ) -> str:

        profile = (
            f"Имя: {user.get('full_name')}\n"
            f"Биография: {user.get('bio')}\n"
            f"Увлечения: {format_hobbies(user.get('hobbies', []))}\n"
        )

        tasks = "\n".join(
            f"- {t['title']} ({PRIORITY_LABELS.get(t.get('priority',2))})"
            for t in today_tasks
        )

        return f"""
Профиль пользователя:
{profile}

Задачи на сегодня:
{tasks}

Сделай анализ дня и дай рекомендации.
"""

    @staticmethod
    def _build_coach_prompt(
        user: dict[str, Any],
        today_tasks: list[dict[str, Any]],
        recent_history: dict[str, list[dict[str, Any]]],
        question: str,
    ) -> str:

        tasks = "\n".join(f"- {t['title']}" for t in today_tasks)

        return f"""
Пользователь: {user.get('full_name')}
Увлечения: {format_hobbies(user.get('hobbies', []))}

Задачи сегодня:
{tasks}

Вопрос пользователя:
{question}
"""
