from __future__ import annotations

from collections import Counter
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


def format_hobbies(hobbies: list[str] | None) -> str:
    if not hobbies:
        return "не указаны"
    return ", ".join(str(hobby).strip() for hobby in hobbies if str(hobby).strip()) or "не указаны"


def _shorten(text: str, limit: int = 60) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def format_task_card(task: dict[str, Any], index: int | None = None) -> str:
    title = escape(task.get("title") or "Без названия")
    title = _shorten(title, 70)

    priority = int(task.get("priority", 2) or 2)
    status = str(task.get("status", "pending") or "pending")
    duration = task.get("duration_minutes")

    priority_label = PRIORITY_LABELS.get(priority, "средняя")
    priority_emoji = PRIORITY_EMOJI.get(priority, "🟡")
    status_label = STATUS_LABELS.get(status, "в процессе")
    status_emoji = STATUS_EMOJI.get(status, "⏳")

    duration_text = f"{duration} мин" if duration else "не указано"
    number = f"{index}. " if index is not None else ""

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

    lines = ["🗓 <b>План на день</b>", ""]

    for i, task in enumerate(tasks, start=1):
        lines.append(format_task_card(task, i))
        lines.append("")

    return "\n".join(lines).strip()


def format_plan_table(tasks: list[dict[str, Any]]) -> str:
    return format_plan(tasks)


def format_tasks_table(tasks: list[dict[str, Any]]) -> str:
    return format_plan(tasks)


def progress_summary(tasks: list[dict[str, Any]]) -> str:
    if not tasks:
        return "📊 <b>Прогресс дня</b>\n\nПока задач нет."

    counter = Counter(task.get("status", "pending") for task in tasks)
    total = len(tasks)
    done = counter.get("done", 0)
    pending = counter.get("pending", 0)
    skipped = counter.get("skipped", 0)

    percent = round(done / total * 100) if total else 0
    filled = min(10, round(percent / 10))
    bar = "█" * filled + "░" * (10 - filled)

    return (
        "📊 <b>Прогресс дня</b>\n\n"
        f"<b>{bar}</b> {percent}%\n\n"
        f"✅ Выполнено: <b>{done}</b>\n"
        f"⏳ Осталось: <b>{pending}</b>\n"
        f"⏭️ Пропущено: <b>{skipped}</b>\n"
        f"📝 Всего задач: <b>{total}</b>"
    )
