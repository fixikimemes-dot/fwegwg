from __future__ import annotations

from collections import Counter
from html import escape
from typing import Any, Iterable


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
    "skipped": "отложено",
}

STATUS_EMOJI = {
    "pending": "⏳",
    "done": "✅",
    "skipped": "⏭️",
}


def shorten(text: str, width: int) -> str:
    clean = " ".join((text or "").replace("\n", " ").split())
    if len(clean) <= width:
        return clean
    if width <= 1:
        return clean[:width]
    return clean[: width - 1].rstrip() + "…"


def format_hobbies(hobbies: Iterable[str]) -> str:
    values = [item.strip() for item in hobbies if item and item.strip()]
    return ", ".join(values) if values else "не указаны"


def format_task_card(task: dict[str, Any], index: int | None = None) -> str:
    title = escape(task.get("title") or "Без названия")
    title = shorten(title, 70)

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
            "Нажми «➕ Добавить задачу», и я соберу тебе план."
        )

    lines = ["🗓 <b>План на день</b>", ""]

    for idx, task in enumerate(tasks, start=1):
        lines.append(format_task_card(task, idx))
        lines.append("")

    return "\n".join(lines).strip()


def format_plan_table(tasks: list[dict[str, Any]]) -> str:
    return format_plan(tasks)


def format_tasks_table(tasks: list[dict[str, Any]]) -> str:
    return format_plan(tasks)


def progress_summary(tasks: list[dict[str, Any]]) -> str:
    if not tasks:
        return "📊 <b>Прогресс дня</b>\n\nПлан на день пока пустой."

    counter = Counter(task.get("status", "pending") for task in tasks)
    total = len(tasks)
    done = counter.get("done", 0)
    pending = counter.get("pending", 0)
    skipped = counter.get("skipped", 0)
    percent = round((done / total) * 100) if total else 0

    filled = min(10, round(percent / 10))
    bar = "█" * filled + "░" * (10 - filled)

    return (
        "📊 <b>Прогресс дня</b>\n\n"
        f"<b>{bar}</b> {percent}%\n\n"
        f"✅ Выполнено: <b>{done}</b>\n"
        f"⏳ В процессе: <b>{pending}</b>\n"
        f"⏭️ Отложено: <b>{skipped}</b>\n"
        f"📝 Всего задач: <b>{total}</b>"
    )


def format_task_details(task: dict[str, Any]) -> str:
    duration = task.get("duration_minutes")
    duration_text = f"{duration} мин" if duration else "не указано"
    note = escape(task.get("note") or "—")
    title = escape(task.get("title") or "Без названия")
    status = STATUS_LABELS.get(task.get("status", "pending"), "в процессе")
    priority = PRIORITY_LABELS.get(task.get("priority", 2), "средняя")

    return (
        f"<b>{title}</b>\n"
        f"Серьёзность: <b>{priority}</b>\n"
        f"Длительность: <b>{duration_text}</b>\n"
        f"Статус: <b>{status}</b>\n"
        f"Комментарий: {note}"
    )


def format_calorie_estimate(estimate: dict[str, Any]) -> str:
    meal_name = escape(str(estimate.get("meal_name") or "Блюдо"))
    calories = int(round(float(estimate.get("calories") or 0)))
    protein = round(float(estimate.get("protein_grams") or 0), 1)
    fat = round(float(estimate.get("fat_grams") or 0), 1)
    carbs = round(float(estimate.get("carbs_grams") or 0), 1)
    note = escape(str(estimate.get("note") or "Это примерная оценка по фото."))

    return (
        "🍽 <b>Оценка блюда</b>\n\n"
        f"🍴 <b>{meal_name}</b>\n"
        f"🔥 Калории: <b>{calories} ккал</b>\n"
        f"🥩 Белки: <b>{protein} г</b>\n"
        f"🧈 Жиры: <b>{fat} г</b>\n"
        f"🍞 Углеводы: <b>{carbs} г</b>\n\n"
        f"ℹ️ {note}\n\n"
        "Если всё ок — добавь в дневник."
    )


def format_calorie_day(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return (
            "🔥 <b>Калории за сегодня</b>\n\n"
            "Пока записей нет.\n"
            "Нажми «📷 Блюдо по фото» и пришли первое блюдо."
        )

    total = sum(int(item.get("calories") or 0) for item in entries)

    lines = ["🔥 <b>Калории за сегодня</b>", ""]
    for idx, item in enumerate(entries, start=1):
        meal_name = escape(str(item.get("meal_name") or "Блюдо"))
        calories = int(item.get("calories") or 0)
        created_at = str(item.get("created_at") or "")
        hhmm = created_at[11:16] if len(created_at) >= 16 else "--:--"
        lines.append(f"{idx}. <b>{meal_name}</b> — {calories} ккал <i>({hhmm})</i>")

    lines.append("")
    lines.append(f"🔥 <b>Итого за день: {total} ккал</b>")

    return "\n".join(lines)
