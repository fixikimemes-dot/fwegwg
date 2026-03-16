from __future__ import annotations

import base64
import json
from collections import Counter
from typing import Any

try:
    from openai import AsyncOpenAI
except Exception:
    AsyncOpenAI = None

from .formatters import PRIORITY_LABELS, format_hobbies


class AIService:
    def __init__(self, api_key: str | None, model: str) -> None:
        self.model = model
        self.enabled = bool(api_key and AsyncOpenAI is not None)
        self.client = AsyncOpenAI(api_key=api_key) if self.enabled else None

    # =========================
    # АНАЛИЗ ДНЯ
    # =========================

    async def daily_analysis(
        self,
        user: dict[str, Any],
        today_tasks: list[dict[str, Any]],
        today_checkins: list[dict[str, Any]],
        recent_history: dict[str, list[dict[str, Any]]],
    ) -> str:

        if not self.enabled or not self.client:
            return self._fallback_analysis(user, today_tasks, today_checkins, recent_history)

        prompt = self._build_daily_analysis_prompt(
            user,
            today_tasks,
            today_checkins,
            recent_history,
        )

        response = await self.client.responses.create(
            model=self.model,
            instructions=(
                "Ты личный AI-коуч продуктивности. "
                "Отвечай по-русски. "
                "Формат ответа:\n"
                "1) главный фокус дня\n"
                "2) риски\n"
                "3) что изменить\n"
                "4) короткая мотивация"
            ),
            input=prompt,
            max_output_tokens=500,
        )

        return response.output_text.strip()

    # =========================
    # AI КОУЧ
    # =========================

    async def coach_reply(
        self,
        user: dict[str, Any],
        today_tasks: list[dict[str, Any]],
        recent_history: dict[str, list[dict[str, Any]]],
        question: str,
    ) -> str:

        if not self.enabled or not self.client:
            return self._fallback_coach_reply(user, today_tasks, recent_history, question)

        prompt = self._build_coach_prompt(user, today_tasks, recent_history, question)

        response = await self.client.responses.create(
            model=self.model,
            instructions="Ты AI-наставник по продуктивности. Дай краткий разбор и план действий.",
            input=prompt,
            max_output_tokens=500,
        )

        return response.output_text.strip()

    # =========================
    # АНАЛИЗ ЕДЫ ПО ФОТО
    # =========================

    async def estimate_meal_from_photo(
        self,
        image_bytes: bytes,
        caption: str | None = None,
    ) -> dict[str, Any] | None:

        if not self.enabled or not self.client:
            return None

        base64_image = base64.b64encode(image_bytes).decode()

        prompt = (
            "Определи блюдо на фото и оцени примерную калорийность.\n"
            "Верни JSON в формате:\n"
            "{\n"
            ' "meal_name": "...",\n'
            ' "calories": 500,\n'
            ' "protein_grams": 25,\n'
            ' "fat_grams": 20,\n'
            ' "carbs_grams": 60,\n'
            ' "note": "примерная оценка"\n'
            "}\n"
        )

        if caption:
            prompt += f"\nПодпись пользователя: {caption}"

        response = await self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    ],
                }
            ],
            max_output_tokens=300,
        )

        text = response.output_text.strip()

        try:
            return json.loads(text)
        except Exception:
            return None

    # =========================
    # PROMPTS
    # =========================

    def _build_daily_analysis_prompt(
        self,
        user,
        today_tasks,
        today_checkins,
        recent_history,
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

        return f"{profile}\nЗадачи:\n{tasks}"

    def _build_coach_prompt(self, user, today_tasks, history, question):

        tasks = "\n".join(
            f"- {t['title']} ({t.get('status')})"
            for t in today_tasks
        )

        return (
            f"Пользователь: {user.get('full_name')}\n"
            f"Увлечения: {format_hobbies(user.get('hobbies', []))}\n"
            f"Задачи:\n{tasks}\n\n"
            f"Вопрос: {question}"
        )

    # =========================
    # FALLBACK
    # =========================

    def _fallback_analysis(self, user, today_tasks, today_checkins, history):

        pending = [t for t in today_tasks if t.get("status") == "pending"]
        done = [t for t in today_tasks if t.get("status") == "done"]

        focus = pending[0]["title"] if pending else "завершить день"

        return (
            f"1) Фокус: <b>{focus}</b>\n"
            f"2) Риск: перегруз\n"
            f"3) Сделай 1 главную задачу\n"
            f"4) Уже выполнено {len(done)} задач"
        )

    def _fallback_coach_reply(self, user, today_tasks, history, question):

        pending = [t["title"] for t in today_tasks if t.get("status") == "pending"]

        return (
            f"Разбор: {question}\n\n"
            "План:\n"
            "1) выбери одну задачу\n"
            "2) 30 минут фокуса\n"
            "3) напиши результат"
        )
