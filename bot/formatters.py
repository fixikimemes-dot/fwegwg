from __future__ import annotations

from html import escape
from typing import Any

PRIORITY_LABELS = {
    1: "низкая",
    2: "средняя",
    3: "высокая",
}

PRIORITY_EMOJI = {
    1: "🟢",
    2: "🟡",
    3: "🔴",
}

STATUS_LABELS = {
    "pending": "в процессе",
    "done": "выполнено",
    "skipped": "пропущено",
}

STATUS_EMOJI = {
    "pending": "⏳",
    "done": "✅",
    "skipped": "⏭️",
}


def format_hobbies(hobbies: list[str]) -> str:
    if not hobbies:
        return "не указаны"
    return ", ".join(hobbies)


def _shorten(text: str, limit: int = 48) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def format_task_card(task: dict[str, Any], index: int | None = None) -> str:
    title = escape(task.get("title") or "Без названия")
    title = _shorten(title, 60)

    priority = int(task.get("priority", 2) or 2)
    status = task.get("status", "pending")
    duration = task.get("duration_minutes")

    priority_label = PRIORITY_LABELS.get(priority, "средняя")
    priority_emoji = PRIORITY_EMOJI.get(priority, "🟡")
    status_label = STATUS_LABELS.get(status, "в процессе")
    status_emoji = STATUS_EMOJI.get(status, "⏳")

    number = f"{index}. " if index is not None else ""
    duration_text = f"{duration} мин" if duration else "время не указано"

    return (
        f"{status_emoji} <b>{number}{title}</b>\n"
        f"   {priority_emoji} Серьёзность: <b>{priority_label}</b>\n"
        f"   ⏱ Время: <b>{duration_text}</b>\n"
        f"   📌 Статус: <b>{status_label}</b>"
    )


def format_plan(tasks: list[dict[str, Any]]) -> str:
    if not tasks:
        return (
            "🗓 <b>План на день</b>\n\n"
            "У тебя пока нет задач.\n"
            "Добавь первую задачу через кнопку ниже."
        )

    lines = ["🗓 <b>План на день</b>\n"]
    for i, task in enumerate(tasks, start=1):
        lines.append(format_task_card(task, i))
        lines.append("")

    return "\n".join(lines).strip()
