import json
import re
import urllib.error
import urllib.request
from datetime import date

from sqlalchemy.orm import Session

from app.ai.tools import (
    complete_goal_tool,
    complete_habit_tool,
    complete_task_tool,
    create_goal_tool,
    create_habit_tool,
    create_task_tool,
    delete_goal_tool,
    delete_habit_tool,
    delete_task_tool,
    get_daily_plan_tool,
    get_dashboard_tool,
    get_goals_tool,
    get_habit_completions_tool,
    get_habits_tool,
    get_tasks_tool,
    update_goal_tool,
    update_habit_tool,
    update_task_tool,
)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:1.5b"


def _is_hinglish(msg: str) -> bool:
    if re.search(r"[\u0900-\u097F]", msg):
        return True
    lower = msg.lower()
    words = set(re.findall(r"\b[a-z]+\b", lower))
    markers = {
        "bana", "banao", "hai", "hain", "mera", "meri", "mere",
        "aaj", "kya", "kitne", "kitni", "kitna", "nahi", "bhai",
        "mujhe", "liye", "aur", "abhi", "chahiye", "kaha", "kaise",
        "bata", "dikha", "pura", "poora", "khatam", "hata", "mita",
        "roz", "hafte", "mahine", "wala", "wale", "diya", "gaya",
        "gayi", "raha", "rahi", "hoga", "hogi", "wala",
        "kar", "de", "ko", "ka", "ki", "ho", "gaya", "gayi",
    }
    if words & markers:
        return True
    phrases = [
        "bana de", "kar de", "ho gaya", "ho gayi", "kya hai",
        "mera status", "aaj ka", "kitne ", "complete kar",
        "kar diya", "kar de",
    ]
    return any(p in lower for p in phrases)


def _cap(s: str | None) -> str:
    if not s:
        return ""
    return s[:1].upper() + s[1:].lower()


def _task_created_msg(title: str, priority: str, hi: bool) -> str:
    if hi:
        return f"Task create ho gaya.\nName: {title}\nPriority: {_cap(priority)}"
    return f"Task created successfully.\nName: {title}\nPriority: {_cap(priority)}"


def _task_completed_msg(title: str, hi: bool) -> str:
    if hi:
        return f"Task complete ho gaya.\nName: {title}"
    return f"Task completed successfully.\nName: {title}"


def _task_deleted_msg(title: str, hi: bool) -> str:
    if hi:
        return f"Task delete ho gaya.\nName: {title}"
    return f"Task deleted successfully.\nName: {title}"


def _task_updated_msg(title: str, priority: str, hi: bool) -> str:
    if hi:
        return f"Task update ho gaya.\nName: {title}\nPriority: {_cap(priority)}"
    return f"Task updated successfully.\nName: {title}\nPriority: {_cap(priority)}"


def _goal_created_msg(title: str, category: str, hi: bool) -> str:
    if hi:
        return f"Goal create ho gaya.\nName: {title}\nCategory: {_cap(category)}"
    return f"Goal created successfully.\nName: {title}\nCategory: {_cap(category)}"


def _goal_completed_msg(title: str, hi: bool) -> str:
    if hi:
        return f"Goal complete ho gaya.\nName: {title}"
    return f"Goal completed successfully.\nName: {title}"


def _goal_deleted_msg(title: str, hi: bool) -> str:
    if hi:
        return f"Goal delete ho gaya.\nName: {title}"
    return f"Goal deleted successfully.\nName: {title}"


def _goal_updated_msg(title: str, category: str, hi: bool) -> str:
    if hi:
        return f"Goal update ho gaya.\nName: {title}\nCategory: {_cap(category)}"
    return f"Goal updated successfully.\nName: {title}\nCategory: {_cap(category)}"


def _habit_created_msg(title: str, freq: str, hi: bool) -> str:
    if hi:
        return f"Habit create ho gaya.\nName: {title}\nFrequency: {_cap(freq)}"
    return f"Habit created successfully.\nName: {title}\nFrequency: {_cap(freq)}"


def _habit_checked_msg(title: str, streak: int, best: int, hi: bool) -> str:
    day = "day" if streak == 1 else "days"
    if hi:
        return f"Habit check-in ho gaya.\nName: {title}\nCurrent streak: {streak} {day}"
    return f"Habit checked in successfully.\nName: {title}\nCurrent streak: {streak} {day}"


def _habit_deleted_msg(title: str, hi: bool) -> str:
    if hi:
        return f"Habit delete ho gayi.\nName: {title}"
    return f"Habit deleted successfully.\nName: {title}"


def _habit_updated_msg(title: str, freq: str | None, hi: bool) -> str:
    if freq:
        if hi:
            return f"Habit update ho gayi.\nName: {title}\nFrequency: {_cap(freq)}"
        return f"Habit updated successfully.\nName: {title}\nFrequency: {_cap(freq)}"
    return f"Habit updated successfully: {title}." if not hi else f"Habit update ho gayi: {title}."


def _not_found(entity: str, hi: bool) -> str:
    if hi:
        return f"{entity} nahi mila. Naam ya ID check kar le."
    return f"{entity} not found. Please check the name or ID."


def _need_name(entity: str, hi: bool) -> str:
    if hi:
        return f"{entity} ka naam bata de, phir main create kar deta hoon."
    low = entity.lower()
    return f"Please provide a {low} name."


def ask_brain(
    message: str,
    db: Session | None = None,
    user_id: int | None = None,
) -> str:
    """Main AI-LifeOS brain."""

    dashboard = None

    if db is not None and user_id is not None:
        dashboard = get_dashboard_tool(
            db=db,
            user_id=user_id,
        )

    text = message.lower().strip()
    hi = _is_hinglish(message)

    # =========================================================
    # HABIT COMPLETE
    # =========================================================

    if db is not None and user_id is not None:
        if _is_habit_complete_request(text):
            habit_id = _extract_habit_id(text)
            if habit_id is None:
                habit_id = _resolve_habit_id_by_name(
                    text, db, user_id
                )
            if habit_id is not None:
                result = complete_habit_tool(
                    db=db,
                    user_id=user_id,
                    habit_id=habit_id,
                )

                if not result["success"]:
                    err = result.get("error", "")
                    if hi:
                        return f"Habit complete nahi ho paya: {err}" if err else "Habit complete nahi ho paya."
                    return f"Could not complete habit: {err}" if err else "Could not complete habit."

                habit = result["habit"]

                return _habit_checked_msg(
                    habit["title"],
                    habit["current_streak"],
                    habit["longest_streak"],
                    hi,
                )
            if "habit" in text:
                return _not_found("Habit", hi)

    # =========================================================
    # HABIT DELETE
    # =========================================================

    if db is not None and user_id is not None:
        if _is_habit_delete_request(text):
            habit_id = _extract_habit_id(text)
            if habit_id is None:
                habit_id = _resolve_habit_id_by_name(
                    text, db, user_id
                )
            if habit_id is not None:
                result = delete_habit_tool(
                    db=db,
                    user_id=user_id,
                    habit_id=habit_id,
                )

                if not result["success"]:
                    return _not_found("Habit", hi)

                habit = result["habit"]

                return _habit_deleted_msg(habit["title"], hi)
            if "habit" in text:
                return _not_found("Habit", hi)

    # =========================================================
    # HABIT UPDATE
    # =========================================================

    if db is not None and user_id is not None:
        if _is_habit_update_request(text):
            habit_id = _extract_habit_id(text)
            if habit_id is None:
                habit_id = _resolve_habit_id_by_name(
                    text, db, user_id
                )
            if habit_id is not None:
                frequency = _extract_habit_frequency(text)

                if frequency is not None:
                    result = update_habit_tool(
                        db=db,
                        user_id=user_id,
                        habit_id=habit_id,
                        frequency=frequency,
                    )

                    if not result["success"]:
                        return _not_found("Habit", hi)

                    habit = result["habit"]

                    return _habit_updated_msg(
                        habit["title"],
                        habit["frequency"],
                        hi,
                    )

                if "inactive" in text or "deactivate" in text:
                    result = update_habit_tool(
                        db=db,
                        user_id=user_id,
                        habit_id=habit_id,
                        is_active=False,
                    )

                    if not result["success"]:
                        return _not_found("Habit", hi)

                    habit = result["habit"]

                    if hi:
                        return f"Habit deactivate ho gayi: {habit['title']}."
                    return f"Habit deactivated successfully: {habit['title']}."

                if "active" in text or "activate" in text:
                    result = update_habit_tool(
                        db=db,
                        user_id=user_id,
                        habit_id=habit_id,
                        is_active=True,
                    )

                    if not result["success"]:
                        return _not_found("Habit", hi)

                    habit = result["habit"]

                    if hi:
                        return f"Habit activate ho gayi: {habit['title']}."
                    return f"Habit activated successfully: {habit['title']}."

                if hi:
                    return "Habit me kya update karna hai, wo bata de."
                return "What would you like to update in this habit?"
            if "habit" in text:
                return _not_found("Habit", hi)

    # =========================================================
    # HABIT CREATE
    # =========================================================

    if db is not None and user_id is not None:
        if _is_habit_create_request(text):
            title = _extract_habit_title(message)
            frequency = _extract_habit_frequency(text)

            if frequency is None:
                frequency = "daily"

            if title:
                result = create_habit_tool(
                    db=db,
                    user_id=user_id,
                    title=title,
                    frequency=frequency,
                )

                if not result["success"]:
                    if hi:
                        return "Habit create nahi ho paya."
                    return "Could not create habit."

                habit = result["habit"]

                return _habit_created_msg(
                    habit["title"],
                    habit["frequency"],
                    hi,
                )

            return _need_name("Habit", hi)

    # =========================================================
    # HABIT COMPLETIONS / HISTORY
    # =========================================================

    if db is not None and user_id is not None:
        habit_id = _extract_habit_id(text)

        if (
            habit_id is not None
            and _is_habit_history_request(text)
        ):
            result = get_habit_completions_tool(
                db=db,
                user_id=user_id,
                habit_id=habit_id,
            )

            if not result["success"]:
                return _not_found("Habit", hi)

            habit = result["habit"]
            completions = result["completions"]

            if not completions:
                if hi:
                    return f"{habit['title']} ki abhi koi completion history nahi hai."
                return f"No completion history yet for {habit['title']}."

            lines = [
                f"{habit['title']}" + (" ki completion history:" if hi else " — completion history:"),
            ]

            for completion in completions:
                lines.append(
                    f"• {completion['completed_date']}"
                )

            if hi:
                lines.append(f"Current streak: {habit['current_streak']} days")
                lines.append(f"Best streak: {habit['longest_streak']} days")
            else:
                lines.append(f"Current streak: {habit['current_streak']} days")
                lines.append(f"Best streak: {habit['longest_streak']} days")

            return "\n".join(lines)

    # =========================================================
    # HABIT READ
    # =========================================================

    if db is not None and user_id is not None:
        if _is_habit_read_request(text):
            result = get_habits_tool(
                db=db,
                user_id=user_id,
            )

            habits = result["habits"]

            if not habits:
                if hi:
                    return "Abhi tumhari koi habits nahi hain."
                return "You don't have any habits yet."

            if hi:
                lines = [f"Tumhari total {len(habits)} habits hain:"]
            else:
                lines = [f"You have {len(habits)} habit{'s' if len(habits) != 1 else ''}:"]

            for habit in habits:
                if hi:
                    active_status = "active" if habit["is_active"] else "inactive"
                    lines.append(
                        f"• {habit['title']} "
                        f"({active_status}, "
                        f"{habit['frequency']}, "
                        f"streak {habit['current_streak']})"
                    )
                else:
                    active_status = "Active" if habit["is_active"] else "Inactive"
                    lines.append(
                        f"• {habit['title']} — {active_status}, {_cap(habit['frequency'])}"
                    )

            return "\n".join(lines)

    # =========================================================
    # TASK COMPLETE
    # =========================================================

    if db is not None and user_id is not None:
        if _is_task_complete_request(text):
            task_id = _extract_task_id(text)
            if task_id is None:
                task_id = _resolve_task_id_by_name(
                    text, db, user_id
                )
            if task_id is not None:
                result = complete_task_tool(
                    db=db,
                    user_id=user_id,
                    task_id=task_id,
                )

                if not result["success"]:
                    return _not_found("Task", hi)

                task = result["task"]

                return _task_completed_msg(task["title"], hi)
            if "task" in text:
                return _not_found("Task", hi)

    # =========================================================
    # TASK DELETE
    # =========================================================

    if db is not None and user_id is not None:
        if _is_task_delete_request(text):
            task_id = _extract_task_id(text)
            if task_id is None:
                task_id = _resolve_task_id_by_name(
                    text, db, user_id
                )
            if task_id is not None:
                result = delete_task_tool(
                    db=db,
                    user_id=user_id,
                    task_id=task_id,
                )

                if not result["success"]:
                    return _not_found("Task", hi)

                task = result["task"]

                return _task_deleted_msg(task["title"], hi)
            if "task" in text or "delete" in text or "remove" in text:
                return _not_found("Task", hi)

    # =========================================================
    # TASK UPDATE
    # =========================================================

    if db is not None and user_id is not None:
        if _is_task_update_request(text):
            task_id = _extract_task_id(text)
            if task_id is None:
                task_id = _resolve_task_id_by_name(
                    text, db, user_id
                )
            if task_id is not None:
                priority = _extract_priority_if_present(text)

                if priority is not None:
                    result = update_task_tool(
                        db=db,
                        user_id=user_id,
                        task_id=task_id,
                        priority=priority,
                    )

                    if not result["success"]:
                        return _not_found("Task", hi)

                    task = result["task"]

                    return _task_updated_msg(
                        task["title"],
                        task["priority"],
                        hi,
                    )

                if hi:
                    return "Task me kya update karna hai, wo bata de."
                return "What would you like to update in this task?"
            if "task" in text or "priority" in text:
                return _not_found("Task", hi)

    # =========================================================
    # TASK CREATE
    # =========================================================

    if db is not None and user_id is not None:
        if _is_task_create_request(text):
            title = _extract_task_title(message)

            if title:
                priority = _extract_priority(text)

                result = create_task_tool(
                    db=db,
                    user_id=user_id,
                    title=title,
                    priority=priority,
                )

                if not result.get("success"):
                    err = result.get("error", "")
                    if hi:
                        return f"Task create nahi ho paya: {err}" if err else "Task create nahi ho paya."
                    return f"Could not create task: {err}" if err else "Could not create task."

                task = result["task"]

                return _task_created_msg(
                    task["title"],
                    task["priority"],
                    hi,
                )

            return _need_name("Task", hi)

    # =========================================================
    # TASK READ
    # =========================================================

    if db is not None and user_id is not None:
        if _is_task_read_request(text):
            result = get_tasks_tool(
                db=db,
                user_id=user_id,
            )

            tasks = result["tasks"]

            if not tasks:
                if hi:
                    return "Abhi tumhare koi tasks nahi hain."
                return "You don't have any tasks yet."

            if hi:
                lines = [f"Tumhare total {len(tasks)} tasks hain:"]
            else:
                lines = [f"You have {len(tasks)} task{'s' if len(tasks) != 1 else ''}:"]

            for task in tasks:
                if hi:
                    status_hi = "pending" if task["status"] == "pending" else task["status"]
                    lines.append(
                        f"• {task['title']} — {status_hi}, {_cap(task['priority'])} priority"
                    )
                else:
                    lines.append(
                        f"• {task['title']} — {_cap(task['status'])}, {_cap(task['priority'])} priority"
                    )

            return "\n".join(lines)

    # =========================================================
    # GOAL COMPLETE
    # =========================================================

    if db is not None and user_id is not None:
        if _is_goal_complete_request(text):
            goal_id = _extract_goal_id(text)
            if goal_id is None:
                goal_id = _resolve_goal_id_by_name(
                    text, db, user_id
                )
            if goal_id is not None:
                result = complete_goal_tool(
                    db=db,
                    user_id=user_id,
                    goal_id=goal_id,
                )

                if not result["success"]:
                    return _not_found("Goal", hi)

                goal = result["goal"]

                return _goal_completed_msg(goal["title"], hi)
            if "goal" in text:
                return _not_found("Goal", hi)

    # =========================================================
    # GOAL DELETE
    # =========================================================

    if db is not None and user_id is not None:
        if _is_goal_delete_request(text):
            goal_id = _extract_goal_id(text)
            if goal_id is None:
                goal_id = _resolve_goal_id_by_name(
                    text, db, user_id
                )
            if goal_id is not None:
                result = delete_goal_tool(
                    db=db,
                    user_id=user_id,
                    goal_id=goal_id,
                )

                if not result["success"]:
                    return _not_found("Goal", hi)

                goal = result["goal"]

                return _goal_deleted_msg(goal["title"], hi)
            if "goal" in text:
                return _not_found("Goal", hi)

    # =========================================================
    # GOAL UPDATE
    # =========================================================

    if db is not None and user_id is not None:
        if _is_goal_update_request(text):
            goal_id = _extract_goal_id(text)
            if goal_id is None:
                goal_id = _resolve_goal_id_by_name(
                    text, db, user_id
                )
                if goal_id is None and "progress" in text:
                    try:
                        result_tmp = get_goals_tool(db=db, user_id=user_id)
                        goals_tmp = result_tmp.get("goals") or []
                        if len(goals_tmp) == 1:
                            goal_id = goals_tmp[0]["id"]
                    except Exception:
                        pass
            if goal_id is not None:
                progress = _extract_progress(text)
                if progress is not None:
                    result = update_goal_tool(
                        db=db,
                        user_id=user_id,
                        goal_id=goal_id,
                        progress=progress,
                    )
                    if not result["success"]:
                        return _not_found("Goal", hi)
                    goal = result["goal"]
                    if hi:
                        return f"Goal progress update ho gaya.\nName: {goal['title']}\nProgress: {goal['progress']}%"
                    return f"Goal progress updated successfully.\nName: {goal['title']}\nProgress: {goal['progress']}%"

                category = _extract_goal_category(text)

                if category is not None:
                    result = update_goal_tool(
                        db=db,
                        user_id=user_id,
                        goal_id=goal_id,
                        category=category,
                    )

                    if not result["success"]:
                        return _not_found("Goal", hi)

                    goal = result["goal"]

                    return _goal_updated_msg(
                        goal["title"],
                        goal["category"],
                        hi,
                    )

                if hi:
                    return "Goal me kya update karna hai, wo bata de."
                return "What would you like to update in this goal?"
            if "goal" in text or "category" in text or "progress" in text:
                return _not_found("Goal", hi)

    # =========================================================
    # GOAL CREATE
    # =========================================================

    if db is not None and user_id is not None:
        if _is_goal_create_request(text):
            title = _extract_goal_title(message)

            if title:
                category = _extract_goal_category(text)

                if category is None:
                    category = "general"

                result = create_goal_tool(
                    db=db,
                    user_id=user_id,
                    title=title,
                    category=category,
                )

                if not result.get("success"):
                    err = result.get("error", "")
                    if hi:
                        return f"Goal create nahi ho paya: {err}" if err else "Goal create nahi ho paya."
                    return f"Could not create goal: {err}" if err else "Could not create goal."

                goal = result["goal"]

                return _goal_created_msg(
                    goal["title"],
                    goal["category"],
                    hi,
                )

            return _need_name("Goal", hi)

    # =========================================================
    # GOAL READ
    # =========================================================

    if db is not None and user_id is not None:
        if _is_goal_read_request(text):
            result = get_goals_tool(
                db=db,
                user_id=user_id,
            )

            goals = result["goals"]

            if not goals:
                if hi:
                    return "Abhi tumhare koi goals nahi hain."
                return "You don't have any goals yet."

            if hi:
                lines = [f"Tumhare total {len(goals)} goals hain:"]
            else:
                lines = [f"You have {len(goals)} goal{'s' if len(goals) != 1 else ''}:"]

            for goal in goals:
                if hi:
                    status = "completed" if goal["is_completed"] else "active"
                    lines.append(
                        f"• {goal['title']} — {status.title()}, {_cap(goal['category'])}"
                    )
                else:
                    status = "Completed" if goal["is_completed"] else "Active"
                    lines.append(
                        f"• {goal['title']} — {status}, {_cap(goal['category'])}"
                    )

            return "\n".join(lines)

    # =========================================================
    # NOTES (frontend-local, no backend persistence yet)
    # =========================================================

    if db is not None and user_id is not None:
        if _is_note_request(text):
            has_other_intent = any(
                fn(text)
                for fn in [
                    _is_task_create_request,
                    _is_task_complete_request,
                    _is_task_delete_request,
                    _is_task_update_request,
                    _is_task_read_request,
                    _is_goal_create_request,
                    _is_goal_complete_request,
                    _is_goal_delete_request,
                    _is_goal_update_request,
                    _is_goal_read_request,
                    _is_habit_create_request,
                    _is_habit_complete_request,
                    _is_habit_delete_request,
                    _is_habit_update_request,
                    _is_habit_read_request,
                    _is_habit_history_request,
                    _is_daily_plan_request,
                ]
            )
            if not has_other_intent:
                if hi:
                    return (
                        "Notes abhi frontend me local store hoti hain, "
                        "backend database me sync nahi hai. "
                        "Tu Notes tab me jaake title/content likh ke Save kar sakta hai. "
                        "Backend support aate hi main tool se execute kar dunga — "
                        "tab tak fake success claim nahi karunga."
                    )
                return (
                    "Notes are currently stored locally in the frontend "
                    "and are not synced to the backend database. "
                    "You can create them in the Notes tab with a title and content, then Save. "
                    "I'll execute via a backend tool as soon as support is available — "
                    "I won't claim success until then."
                )

    # =========================================================
    # FINANCE (frontend-local, no backend persistence yet)
    # =========================================================

    if db is not None and user_id is not None:
        if _is_finance_request(text):
            has_other_intent = any(
                fn(text)
                for fn in [
                    _is_task_create_request,
                    _is_task_complete_request,
                    _is_task_delete_request,
                    _is_task_update_request,
                    _is_task_read_request,
                    _is_goal_create_request,
                    _is_goal_complete_request,
                    _is_goal_delete_request,
                    _is_goal_update_request,
                    _is_goal_read_request,
                    _is_habit_create_request,
                    _is_habit_complete_request,
                    _is_habit_delete_request,
                    _is_habit_update_request,
                    _is_habit_read_request,
                    _is_habit_history_request,
                    _is_daily_plan_request,
                    _is_note_request,
                ]
            )
            if not has_other_intent:
                dash = dashboard
                if dash is not None:
                    if hi:
                        return (
                            f"{_format_dashboard(dash, hi)}\n\n"
                            "Finance (income/expense) abhi frontend me local store hota hai, "
                            "backend persistence abhi nahi hai — isliye verified LifeOS snapshot upar diya hai. "
                            "Tu Finance tab me transaction add kar sakta hai; "
                            "backend support aate hi main tool se real entry karunga."
                        )
                    return (
                        f"{_format_dashboard(dash, hi)}\n\n"
                        "Finance data is currently stored locally in the frontend "
                        "and is not yet persisted to the backend. "
                        "You can add transactions in the Finance tab — "
                        "I'll create real entries via a backend tool as soon as support is available."
                    )
                if hi:
                    return (
                        "Finance tracking abhi frontend me local hai, "
                        "backend database me sync nahi hai. "
                        "Finance tab me jaake transaction add kar sakta hai."
                    )
                return (
                    "Finance tracking is currently local to the frontend "
                    "and not synced to the backend database. "
                    "You can add transactions in the Finance tab."
                )

       # =========================================================
    # PLANNER CRUD — honest limitation (no persistent event storage)
    # =========================================================

    if db is not None and user_id is not None:
        if _is_planner_create_request(text) or _is_planner_update_request(text) or _is_planner_delete_request(text):
            if hi:
                return (
                    "Planner events abhi backend me persistent storage me available nahi hain. "
                    "Isliye create/update/delete event abhi supported nahi hai. "
                    "Tumhara smart daily plan tasks aur habits se generate hota hai — "
                    "\"Show my planner\" ya \"Aaj ka plan\" bol ke verified plan dekh sakta hai."
                )
            return (
                "Planner events are not yet available as persistent database records, "
                "so creating, updating or deleting individual planner events is not currently supported. "
                "Your smart daily plan is generated from your tasks and habits — "
                "try \"Show my planner\" or \"Show my daily plan\" for the verified schedule."
            )

        # =========================================================
    # DAILY PLANNER
    # =========================================================

    if db is not None and user_id is not None:
        if _is_daily_plan_request(text) or _is_planner_read_request(text):

            result = get_daily_plan_tool(
                db=db,
                user_id=user_id,
            )

            if not result["success"]:
                if hi:
                    return "Plan banane me problem aa gayi."
                return "Could not generate your daily plan."

            summary = result["summary"]
            plan = result["plan"]
            goals = result["goals"]

            lines = [
                "📅 Aaj ka Smart Plan:",
                "",
            ]

            if not plan:
                lines.append(
                    "Aaj ke liye koi pending task "
                    "ya active habit nahi hai."
                )

            else:
                for index, item in enumerate(
                    plan,
                    start=1,
                ):
                    start_time = item.get(
                        "start_time",
                        "--:--",
                    )

                    end_time = item.get(
                        "end_time",
                        "--:--",
                    )

                    if item["type"] == "task":

                        priority = item.get(
                            "priority",
                            "medium",
                        )

                        lines.append(
                            f"{index}. "
                            f"{start_time} - {end_time} "
                            f"→ {item['title']} "
                            f"({priority} priority)"
                        )

                    elif item["type"] == "habit":

                        streak = item.get(
                            "current_streak",
                            0,
                        )

                        frequency = item.get(
                            "frequency",
                            "daily",
                        )

                        lines.append(
                            f"{index}. "
                            f"{start_time} - {end_time} "
                            f"→ {item['title']} "
                            f"(habit, {frequency}, "
                            f"streak {streak})"
                        )

            if goals:
                lines.extend(
                    [
                        "",
                        "🎯 Active Goals:",
                    ]
                )

                for goal in goals:
                    lines.append(
                        f"• {goal['title']} "
                        f"({goal['category']})"
                    )

            lines.extend(
                [
                    "",
                    "📊 Summary:",
                    f"• Pending tasks: "
                    f"{summary['pending_tasks']}",
                    f"• Active goals: "
                    f"{summary['active_goals']}",
                    f"• Active habits: "
                    f"{summary['active_habits']}",
                ]
            )

            return "\n".join(lines)
    # =========================================================
    # VERIFIED DASHBOARD FACTS
    # =========================================================

    if dashboard is not None:

        if _matches(
            text,
            [
                "active habit",
                "active habits",
                "kitne habit",
                "kitni habit",
                "kitne habits",
                "kitni habits",
            ],
        ):
            count = dashboard["habits"]["active"]
            if hi:
                return f"Abhi tumhari {count} active {'habit' if count == 1 else 'habits'} hain."
            return f"You have {count} active habit{'s' if count != 1 else ''}."

        if _matches(
            text,
            [
                "current streak",
                "current streak kya",
                "meri streak",
                "streak kitni",
                "streak kya",
            ],
        ):
            streak = dashboard["habits"]["current_streak"]
            if hi:
                return f"Tumhari current streak {streak} days ki hai."
            return f"Your current streak is {streak} day{'s' if streak != 1 else ''}."

        if _matches(
            text,
            [
                "best streak",
                "longest streak",
                "highest streak",
                "sabse badi streak",
            ],
        ):
            streak = dashboard["habits"]["best_streak"]
            if hi:
                return f"Tumhari best streak {streak} days ki hai."
            return f"Your best streak is {streak} day{'s' if streak != 1 else ''}."

        if _matches(
            text,
            [
                "total task",
                "total tasks",
                "kitne task",
                "kitne tasks",
            ],
        ):
            count = dashboard["tasks"]["total"]
            if hi:
                return f"Tumhare total {count} {'task' if count == 1 else 'tasks'} hain."
            return f"You have {count} task{'s' if count != 1 else ''} in total."

        if _matches(
            text,
            [
                "pending task",
                "pending tasks",
                "kitne pending",
                "pending kitne",
            ],
        ):
            count = dashboard["tasks"]["pending"]
            if hi:
                return f"Tumhare {count} pending {'task' if count == 1 else 'tasks'} hain."
            return f"You have {count} pending task{'s' if count != 1 else ''}."

        if _matches(
            text,
            [
                "completed task",
                "completed tasks",
                "kitne task complete",
                "kitne tasks complete",
            ],
        ):
            count = dashboard["tasks"]["completed"]
            if hi:
                return f"Tumne {count} {'task' if count == 1 else 'tasks'} complete kiye hain."
            return f"You have completed {count} task{'s' if count != 1 else ''}."

        if _matches(
            text,
            [
                "total goal",
                "total goals",
                "kitne goal",
                "kitne goals",
            ],
        ):
            count = dashboard["goals"]["total"]
            if hi:
                return f"Tumhare total {count} {'goal' if count == 1 else 'goals'} hain."
            return f"You have {count} goal{'s' if count != 1 else ''} in total."

        if _matches(
            text,
            [
                "active goal",
                "active goals",
                "kitne active goal",
                "kitne active goals",
            ],
        ):
            count = dashboard["goals"]["active"]
            if hi:
                return f"Tumhare {count} active {'goal' if count == 1 else 'goals'} hain."
            return f"You have {count} active goal{'s' if count != 1 else ''}."

        if _matches(
            text,
            [
                "completed goal",
                "completed goals",
                "kitne goal complete",
                "kitne goals complete",
            ],
        ):
            count = dashboard["goals"]["completed"]
            if hi:
                return f"Tumne {count} {'goal' if count == 1 else 'goals'} complete kiye hain."
            return f"You have completed {count} goal{'s' if count != 1 else ''}."

        if _matches(
            text,
            [
                "current status",
                "lifeos status",
                "current lifeos",
                "mera status",
                "overall status",
                "dashboard",
                "progress",
            ],
        ):
            return _format_dashboard(dashboard, hi)

    # =========================================================
    # GENERAL QUESTION → LOCAL QWEN
    # =========================================================

    return _ask_local_model(
        message=message,
        dashboard=dashboard,
    )


# =============================================================
# HABIT INTENTS
# =============================================================


def _is_habit_complete_request(text: str) -> bool:
    phrases = [
        "habit complete",
        "habit completed",
        "habit pura",
        "habit poora",
        "habit done",
        "habit finish",
        "complete habit",
        "complete the habit",
        "mark habit",
        "mark the habit",
        "complete kar",
        "complete kr",
        "pura kar",
        "poora kar",
        "done kar",
        "check in",
        "check-in",
        "checkin",
        "habit kar diya",
        "habit kar de",
    ]

    return any(
        phrase in text
        for phrase in phrases
    ) or ("habit" in text and any(w in text for w in ["complete", "done", "finish"]))


def _is_habit_delete_request(text: str) -> bool:
    delete_words = [
        "delete",
        "remove",
        "hata",
        "mita",
    ]

    return (
        "habit" in text
        and any(
            word in text
            for word in delete_words
        )
    )


def _is_habit_update_request(text: str) -> bool:
    if "frequency" in text and any(w in text for w in ["change", "update", "modify", "set", "kar"]):
        return True
    if "habit" in text and any(w in text for w in ["daily", "weekly", "monthly", "roz", "hafte", "mahine"]):
        if any(w in text for w in ["change", "update", "modify", "set", "kar"]):
            return True
    phrases = [
        "habit update",
        "update habit",
        "change habit",
        "modify habit",
        "habit modify",
        "habit ki frequency",
        "frequency change",
        "frequency kar",
        "frequency set",
        "habit active",
        "habit inactive",
        "activate habit",
        "deactivate habit",
    ]
    if any(phrase in text for phrase in phrases):
        return True
    if "habit" in text and any(w in text for w in ["change", "update", "modify", "set"]):
        return True
    return False


def _is_habit_create_request(text: str) -> bool:
    phrases = [
        "habit bana",
        "habit banao",
        "habit bana de",
        "habit create",
        "habit create kar",
        "habit add",
        "habit add kar",
        "habit daal",
        "ek habit",
        "create a habit",
        "create habit",
        "make a habit",
        "make habit",
        "add a habit",
        "add habit",
        "new habit",
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


def _is_habit_read_request(text: str) -> bool:
    phrases = [
        "mere habits",
        "meri habits",
        "mere habit",
        "meri habit",
        "habits bata",
        "habit bata",
        "habits dikha",
        "habit dikha",
        "habit list",
        "habits list",
        "show habits",
        "show my habits",
        "list habits",
        "my habits",
        "habits status",
        "show habit",
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


def _is_note_request(text: str) -> bool:
    return "note" in text or "notes" in text


def _is_finance_request(text: str) -> bool:
    keywords = [
        "finance",
        "transaction",
        "transactions",
        "expense",
        "expenses",
        "income",
        "balance",
        "cash flow",
        "cashflow",
        "kharcha",
        "kamai",
    ]
    return any(k in text for k in keywords)


def _is_habit_history_request(text: str) -> bool:
    """Return True when the user asks for a habit's history."""

    if "habit" not in text:
        return False

    history_words = [
        "history",
        "completions",
        "completion",
        "record",
        "records",
        "progress",
    ]

    return any(
        word in text
        for word in history_words
    )


def _extract_habit_id(text: str) -> int | None:
    words = (
        text
        .replace("#", " ")
        .replace(",", " ")
        .split()
    )

    for index, word in enumerate(words):

        if word != "habit":
            continue

        if (
            index + 2 < len(words)
            and words[index + 1] == "id"
        ):
            try:
                return int(words[index + 2])
            except ValueError:
                pass

        if index + 1 < len(words):
            try:
                return int(words[index + 1])
            except ValueError:
                pass

    return None


def _extract_habit_frequency(
    text: str,
) -> str | None:

    frequencies = [
        "daily",
        "weekly",
        "monthly",
    ]

    for frequency in frequencies:
        if frequency in text:
            return frequency

    if "roz" in text:
        return "daily"

    if "har din" in text:
        return "daily"

    if "hafte" in text or "hafta" in text:
        return "weekly"

    if "mahine" in text or "mahina" in text:
        return "monthly"

    return None

def _is_planner_create_request(text: str) -> bool:
    if "planner" not in text and "plan" not in text and "event" not in text and "schedule" not in text:
        return False
    if any(p in text for p in ["create planner", "add planner", "make planner", "new planner", "planner bana", "planner create", "planner add", "event bana", "event create", "create a planner", "create planner event", "add a planner event"]):
        return True
    if "planner" in text and any(w in text for w in ["create", "add", "make", "new", "bana"]):
        return True
    if "event" in text and any(w in text for w in ["create", "add", "make", "new", "bana"]):
        return True
    return False


def _is_planner_read_request(text: str) -> bool:
    phrases = [
        "show planner",
        "show my planner",
        "list planner",
        "planner events",
        "show planner events",
        "list planner events",
        "mere planner",
        "planner dikha",
        "planner bata",
        "show my events",
        "daily planner",
        "planner list",
    ]
    if any(p in text for p in phrases):
        return True
    if "planner" in text and any(w in text for w in ["show", "list", "get", "dikha", "bata", "events"]):
        return True
    return False


def _is_planner_update_request(text: str) -> bool:
    if "planner" not in text and "event" not in text and "schedule" not in text:
        return False
    if any(p in text for p in ["update planner", "change planner", "modify planner", "planner update", "update event", "change event", "modify event", "event update", "change time", "update time"]):
        return True
    if ("planner" in text or "event" in text) and any(w in text for w in ["change", "update", "modify", "set"]):
        return True
    return False


def _is_planner_delete_request(text: str) -> bool:
    if "planner" not in text and "event" not in text and "schedule" not in text:
        return False
    if any(p in text for p in ["delete planner", "remove planner", "planner delete", "delete event", "remove event", "event delete", "planner hata", "event hata"]):
        return True
    if ("planner" in text or "event" in text) and any(w in text for w in ["delete", "remove", "hata", "mita"]):
        return True
    return False


def _is_daily_plan_request(text: str) -> bool:
    if _is_planner_read_request(text):
        return False
    phrases = [
        "aaj ka plan",
        "aaj ka planner",
        "today ka plan",
        "today ka planner",
        "daily plan",
        "daily planner",
        "mera plan bana",
        "mera plan banao",
        "aaj kya karna hai",
        "aaj mujhe kya karna hai",
        "aaj ka schedule",
        "today schedule",
        "schedule bana",
        "schedule banao",
        "plan bana de",
        "plan bana do",
    ]
    return any(phrase in text for phrase in phrases)


def _extract_habit_title(
    message: str,
) -> str | None:

    title = message.strip()

    cleanup_phrases = [
        "daily frequency",
        "weekly frequency",
        "monthly frequency",
        "frequency daily",
        "frequency weekly",
        "frequency monthly",
    ]

    for phrase in cleanup_phrases:
        title = re.sub(
            re.escape(phrase),
            "",
            title,
            flags=re.IGNORECASE,
        )

    title = title.strip(" :,-.")
    lowered = title.lower()

    patterns = [
        "create a habit named",
        "create a habit called",
        "create a habit for",
        "create habit named",
        "create habit called",
        "create habit for",
        "make a habit named",
        "make a habit called",
        "make a habit for",
        "add a habit named",
        "add a habit called",
        "add a habit for",
        "create a habit",
        "create habit",
        "make a habit",
        "make habit",
        "add a habit",
        "add habit",
        "new habit",
        "ka habit bana do",
        "ki habit bana do",
        "ka habit bana de",
        "ki habit bana de",
        "ka habit bana",
        "ki habit bana",
        "ka habit banao",
        "ki habit banao",
        "ka habit create kar",
        "ki habit create kar",
        "ka habit create",
        "ki habit create",
        "ka habit add kar",
        "ki habit add kar",
        "ka habit add",
        "ki habit add",
        "habit bana do",
        "habit bana de",
        "habit bana",
        "habit banao",
        "habit create kar",
        "habit create",
        "habit add kar",
        "habit add",
        "habit daal",
        "ek habit",
    ]

    for pattern in patterns:
        index = lowered.find(pattern)

        if index != -1:
            after = title[index + len(pattern):].strip()
            before = title[:index].strip()
            if after:
                title = after
                if before and pattern.startswith(
                    ("create", "make", "add", "new")
                ):
                    pass
                elif before:
                    title = (before + " " + after).strip()
            else:
                title = before
            lowered = title.lower()
            break

    title = title.strip(" :,-.")
    title = title.strip("\"'")
    for prefix in ["named ", "called ", "for "]:
        if lowered.startswith(prefix):
            title = title[len(prefix):].strip()
            lowered = title.lower()
    title = title.strip(" :,-.\"'")
    for suffix in [" daily", " weekly", " monthly"]:
        if lowered.endswith(suffix) and len(title) > len(suffix):
            title = title[: -len(suffix)].strip()
            lowered = title.lower()
            break

    if not title:
        return None

    return title[:200]


# =============================================================
# TASK INTENTS
# =============================================================


def _is_task_complete_request(text: str) -> bool:
    phrases = [
        "task complete",
        "task completed",
        "task pura",
        "task poora",
        "task khatam",
        "task finish",
        "task done",
        "complete task",
        "complete the task",
        "mark task",
        "mark as complete",
        "finish task",
        "complete kar",
        "complete kr",
        "pura kar",
        "poora kar",
        "finish kar",
        "done kar",
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


def _is_task_delete_request(text: str) -> bool:
    phrases = [
        "task delete",
        "task hata",
        "task remove",
        "task mita",
        "task delete kar",
        "task hata de",
        "task remove kar",
        "task mita de",
        "delete task",
        "remove task",
        "delete the task",
        "remove the task",
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


def _is_task_update_request(text: str) -> bool:
    if "priority" in text and any(w in text for w in ["change", "update", "modify", "set", "kar", "to"]):
        return True
    phrases = [
        "task update",
        "update task",
        "change task",
        "modify task",
        "task modify",
        "set task",
        "priority change",
        "priority kar",
        "priority set",
        "priority high kar",
        "priority low kar",
        "priority medium kar",
        "high priority kar",
        "low priority kar",
        "medium priority kar",
    ]
    if any(phrase in text for phrase in phrases):
        return True
    if "task" in text and any(w in text for w in ["change", "update", "modify", "set"]):
        return True
    return False


def _is_task_create_request(text: str) -> bool:
    phrases = [
        "task bana",
        "task banao",
        "task bana de",
        "task bana do",
        "task create",
        "task create kar",
        "task add",
        "task add kar",
        "task daal",
        "task likh",
        "ek task",
        "create a task",
        "create task",
        "make a task",
        "make task",
        "add a task",
        "add task",
        "new task",
        "ka task bana do",
        "ki task bana do",
        "ka task bana de",
        "ki task bana de",
        "ka task bana",
        "ki task bana",
    ]
    return any(phrase in text for phrase in phrases)


def _is_task_read_request(text: str) -> bool:
    phrases = [
        "mere tasks",
        "mere task",
        "tasks bata",
        "task bata",
        "tasks dikha",
        "task dikha",
        "pending tasks",
        "pending task",
        "kaam bata",
        "kaam dikha",
        "show tasks",
        "show my tasks",
        "list tasks",
        "my tasks",
        "tasks status",
        "show task",
        "my pending tasks",
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


# =============================================================
# GOAL INTENTS
# =============================================================


def _is_goal_complete_request(text: str) -> bool:
    phrases = [
        "goal complete",
        "goal completed",
        "goal pura",
        "goal poora",
        "goal finish",
        "goal done",
        "goal khatam",
        "complete goal",
        "complete the goal",
        "mark goal",
        "mark the goal",
        "finish goal",
        "complete kar",
        "complete kr",
        "pura kar",
        "poora kar",
        "finish kar",
        "done kar",
        "complete kar de",
        "complete kr de",
        "pura kar de",
        "poora kar de",
        "finish kar de",
        "done kar de",
    ]

    return any(
        phrase in text
        for phrase in phrases
    ) or ("goal" in text and any(w in text for w in ["complete", "done", "finish", "khatam"]))


def _is_goal_delete_request(text: str) -> bool:
    delete_words = [
        "delete",
        "remove",
        "hata",
        "mita",
    ]

    return (
        "goal" in text
        and any(
            word in text
            for word in delete_words
        )
    )


def _is_goal_update_request(text: str) -> bool:
    has_verb = any(w in text for w in ["change", "update", "modify", "set", "kar", "to"])
    if any(k in text for k in ["progress", "percent", "%"]):
        if has_verb and ("goal" in text or "progress" in text):
            return True
    if "category" in text and has_verb:
        return True
    phrases = [
        "goal update",
        "update goal",
        "change goal",
        "modify goal",
        "goal modify",
        "goal ki category",
        "category change",
        "category kar",
        "category set",
        "category update",
    ]
    if any(phrase in text for phrase in phrases):
        return True
    if "goal" in text and has_verb:
        return True
    return False


def _is_goal_create_request(text: str) -> bool:
    phrases = [
        "goal bana",
        "goal banao",
        "goal bana de",
        "goal create",
        "goal create kar",
        "goal add",
        "goal add kar",
        "ek goal",
        "create a goal",
        "create goal",
        "make a goal",
        "make goal",
        "add a goal",
        "add goal",
        "new goal",
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


def _is_goal_read_request(text: str) -> bool:
    phrases = [
        "mere goals",
        "mere goal",
        "goals bata",
        "goal bata",
        "goals dikha",
        "goal dikha",
        "goal list",
        "goals list",
        "show goals",
        "show my goals",
        "list goals",
        "my goals",
        "goals status",
        "show goal",
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


def _resolve_task_id_by_name(text: str, db, user_id: int) -> int | None:
    try:
        result = get_tasks_tool(db=db, user_id=user_id)
        tasks = result.get("tasks") or []
        tl = text.lower()
        best = None
        best_len = 0
        for t in tasks:
            title = (t.get("title") or "").lower()
            if title and title in tl and len(title) > best_len:
                best = t["id"]
                best_len = len(title)
        return best
    except Exception:
        return None


def _resolve_goal_id_by_name(text: str, db, user_id: int) -> int | None:
    try:
        result = get_goals_tool(db=db, user_id=user_id)
        goals = result.get("goals") or []
        tl = text.lower()
        best = None
        best_len = 0
        for g in goals:
            title = (g.get("title") or "").lower()
            if title and title in tl and len(title) > best_len:
                best = g["id"]
                best_len = len(title)
        return best
    except Exception:
        return None


def _resolve_habit_id_by_name(text: str, db, user_id: int) -> int | None:
    try:
        result = get_habits_tool(db=db, user_id=user_id)
        habits = result.get("habits") or []
        tl = text.lower()
        import re as _re
        best = None
        best_len = 0
        for h in habits:
            title = (h.get("title") or "").lower()
            if not title:
                continue
            title_words = set(_re.findall(r"\b\w+\b", title))
            text_words = set(_re.findall(r"\b\w+\b", tl))
            if title in tl and len(title) > best_len:
                best = h["id"]
                best_len = len(title)
            elif title_words and title_words & text_words:
                overlap = len(title_words & text_words)
                score = overlap * 10 + len(title)
                if overlap >= 1 and score > best_len:
                    best = h["id"]
                    best_len = score
        return best
    except Exception:
        return None


# =============================================================
# TASK PARSING
# =============================================================


def _extract_task_id(text: str) -> int | None:
    words = (
        text
        .replace("#", " ")
        .replace(",", " ")
        .split()
    )

    for index, word in enumerate(words):

        if word != "task":
            continue

        if (
            index + 2 < len(words)
            and words[index + 1] == "id"
        ):
            try:
                return int(words[index + 2])
            except ValueError:
                pass

        if index + 1 < len(words):
            try:
                return int(words[index + 1])
            except ValueError:
                pass

    return None


def _extract_priority(text: str) -> str:
    if (
        "high priority" in text
        or "priority high" in text
    ):
        return "high"

    if (
        "low priority" in text
        or "priority low" in text
    ):
        return "low"

    if (
        "medium priority" in text
        or "priority medium" in text
    ):
        return "medium"

    return "medium"


def _extract_priority_if_present(
    text: str,
) -> str | None:
    if "priority" in text:
        if "high" in text:
            return "high"
        if "medium" in text:
            return "medium"
        if "low" in text:
            return "low"
    if "high priority" in text or "priority high" in text:
        return "high"
    if "medium priority" in text or "priority medium" in text:
        return "medium"
    if "low priority" in text or "priority low" in text:
        return "low"
    return None


def _extract_task_title(
    message: str,
) -> str | None:
    title = message.strip()

    priority_phrases = [
        "high priority",
        "priority high",
        "medium priority",
        "priority medium",
        "low priority",
        "priority low",
    ]

    for phrase in priority_phrases:
        title = re.sub(
            re.escape(phrase),
            "",
            title,
            flags=re.IGNORECASE,
        )

    title = title.strip(" :,-.")
    lowered = title.lower()

    patterns = [
        "create a task named",
        "create a task called",
        "create a task for",
        "create task named",
        "create task called",
        "create task for",
        "make a task named",
        "make a task called",
        "make a task for",
        "make task named",
        "make task called",
        "make task for",
        "add a task named",
        "add a task called",
        "add a task for",
        "add task named",
        "add task called",
        "add task for",
        "create a task",
        "create task",
        "make a task",
        "make task",
        "add a task",
        "add task",
        "new task",
        "ka task bana do",
        "ki task bana do",
        "ka task bana de",
        "ki task bana de",
        "ka task bana",
        "ki task bana",
        "ka task banao",
        "ki task banao",
        "ka task create kar",
        "ki task create kar",
        "ka task create",
        "ki task create",
        "ka task add kar",
        "ki task add kar",
        "ka task add",
        "ki task add",
        "task bana do",
        "task bana de",
        "task bana",
        "task banao",
        "task create kar",
        "task create",
        "task add kar",
        "task add",
        "task daal",
        "task likh",
        "ek task",
    ]

    for pattern in patterns:
        index = lowered.find(pattern)

        if index != -1:
            after = title[index + len(pattern):].strip()
            before = title[:index].strip()
            if after:
                title = after
                if before and pattern.startswith(
                    ("create", "make", "add", "new")
                ):
                    pass
                elif before:
                    title = (before + " " + after).strip() if after else before
            else:
                title = before
            lowered = title.lower()
            break

    title = title.strip(" :,-.")
    title = title.strip("\"'")

    for prefix in ["named ", "called ", "for "]:
        if lowered.startswith(prefix):
            title = title[len(prefix):].strip()
            lowered = title.lower()

    title = title.strip(" :,-.\"'")
    lowered = title.lower()
    for suf in [" ka", " ki", " ko", " ke", " par", " pe"]:
        if lowered.endswith(suf) and len(title) > len(suf) + 2:
            title = title[: -len(suf)].strip()
            lowered = title.lower()
    title = title.strip(" :,-.\"'")

    if not title:
        return None

    return title[:200]


# =============================================================
# GOAL PARSING
# =============================================================


def _extract_goal_id(text: str) -> int | None:
    words = (
        text
        .replace("#", " ")
        .replace(",", " ")
        .split()
    )

    for index, word in enumerate(words):

        if word != "goal":
            continue

        if (
            index + 2 < len(words)
            and words[index + 1] == "id"
        ):
            try:
                return int(words[index + 2])
            except ValueError:
                pass

        if index + 1 < len(words):
            try:
                return int(words[index + 1])
            except ValueError:
                pass

    return None


def _extract_goal_category(
    text: str,
) -> str | None:
    if "progress" in text or "percent" in text or "%" in text:
        return None

    categories = [
        "career",
        "study",
        "health",
        "fitness",
        "personal",
        "finance",
        "financial",
        "business",
        "general",
    ]

    for category in categories:

        if category in text:

            if category == "financial":
                return "finance"

            return category

    return None


def _extract_progress(text: str) -> int | None:
    m = re.search(r"(\d{1,3})\s*%", text)
    if m:
        try:
            v = int(m.group(1))
            return max(0, min(100, v))
        except ValueError:
            pass
    m = re.search(r"progress.*?(\d{1,3})", text)
    if m:
        try:
            v = int(m.group(1))
            return max(0, min(100, v))
        except ValueError:
            pass
    m = re.search(r"(\d{1,3})\s*(?:percent|percentage)", text)
    if m:
        try:
            v = int(m.group(1))
            return max(0, min(100, v))
        except ValueError:
            pass
    if "progress" in text:
        nums = re.findall(r"\b(\d{1,3})\b", text)
        for token in reversed(nums):
            try:
                v = int(token)
                if 0 <= v <= 100:
                    return v
            except ValueError:
                continue
    return None


def _extract_goal_title(
    message: str,
) -> str | None:

    title = message.strip()

    cleanup_phrases = [
        "career category me",
        "study category me",
        "health category me",
        "fitness category me",
        "personal category me",
        "finance category me",
        "financial category me",
        "business category me",
        "general category me",
        "career category",
        "study category",
        "health category",
        "fitness category",
        "personal category",
        "finance category",
        "financial category",
        "business category",
        "general category",
    ]

    for phrase in cleanup_phrases:
        title = re.sub(
            re.escape(phrase),
            "",
            title,
            flags=re.IGNORECASE,
        )

    title = title.strip(" :,-.")
    lowered = title.lower()

    patterns = [
        "create a goal named",
        "create a goal called",
        "create a goal for",
        "create goal named",
        "create goal called",
        "create goal for",
        "make a goal named",
        "make a goal called",
        "make a goal for",
        "add a goal named",
        "add a goal called",
        "add a goal for",
        "create a goal",
        "create goal",
        "make a goal",
        "make goal",
        "add a goal",
        "add goal",
        "new goal",
        "ka goal bana de",
        "ka goal bana",
        "ka goal banao",
        "ka goal create kar",
        "ka goal create",
        "ka goal add kar",
        "ka goal add",
        "goal bana de",
        "goal bana",
        "goal banao",
        "goal create kar",
        "goal create",
        "goal add kar",
        "goal add",
        "ek goal",
    ]

    for pattern in patterns:

        index = lowered.find(pattern)

        if index != -1:
            after = title[index + len(pattern):].strip()
            before = title[:index].strip()
            if after:
                title = after
                if before and pattern.startswith(
                    ("create", "make", "add", "new")
                ):
                    pass
                elif before:
                    title = (before + " " + after).strip()
            else:
                title = before
            lowered = title.lower()
            break

    title = title.strip(" :,-.")
    title = title.strip("\"'")
    for prefix in ["named ", "called ", "for "]:
        if lowered.startswith(prefix):
            title = title[len(prefix):].strip()
            lowered = title.lower()
    title = title.strip(" :,-.\"'")

    for category in [
        "career",
        "study",
        "health",
        "fitness",
        "personal",
        "finance",
        "financial",
        "business",
        "general",
    ]:

        suffix = f" {category}"

        if title.lower().endswith(suffix):
            title = title[
                :-len(suffix)
            ].strip()

    if not title:
        return None

    return title[:200]


# =============================================================
# GENERAL HELPERS
# =============================================================


def _matches(
    message: str,
    phrases: list[str],
) -> bool:
    return any(
        phrase in message
        for phrase in phrases
    )


def _format_dashboard(
    dashboard: dict,
    hi: bool = True,
) -> str:

    tasks = dashboard["tasks"]
    goals = dashboard["goals"]
    habits = dashboard["habits"]

    if hi:
        return (
            "Tumhara current LifeOS status:\n"
            f"• Tasks: {tasks['total']} total, "
            f"{tasks['pending']} pending, "
            f"{tasks['completed']} completed.\n"
            f"• Goals: {goals['total']} total, "
            f"{goals['active']} active, "
            f"{goals['completed']} completed.\n"
            f"• Habits: {habits['active']} active, "
            f"current streak {habits['current_streak']} days, "
            f"best streak {habits['best_streak']} days."
        )
    return (
        "Your current LifeOS status:\n"
        f"• Tasks: {tasks['total']} total, "
        f"{tasks['pending']} pending, "
        f"{tasks['completed']} completed.\n"
        f"• Goals: {goals['total']} total, "
        f"{goals['active']} active, "
        f"{goals['completed']} completed.\n"
        f"• Habits: {habits['active']} active, "
        f"current streak {habits['current_streak']} days, "
        f"best streak {habits['best_streak']} days."
    )


# =============================================================
# LOCAL QWEN
# =============================================================


def _ask_local_model(
    message: str,
    dashboard: dict | None = None,
    hi: bool | None = None,
) -> str:

    context = ""

    if dashboard is not None:
        context = f"""
Verified LifeOS data:

Tasks:
- Total: {dashboard["tasks"]["total"]}
- Pending: {dashboard["tasks"]["pending"]}
- Completed: {dashboard["tasks"]["completed"]}

Goals:
- Total: {dashboard["goals"]["total"]}
- Active: {dashboard["goals"]["active"]}
- Completed: {dashboard["goals"]["completed"]}

Habits:
- Active: {dashboard["habits"]["active"]}
- Current streak: {dashboard["habits"]["current_streak"]}
- Best streak: {dashboard["habits"]["best_streak"]}
""".strip()

    prompt = f"""
You are the AI assistant of AI-LifeOS.

You help the user with productivity,
planning, organization and general questions.

Important rules:

1. Use verified LifeOS data when it is provided.
2. Never invent LifeOS numbers.
3. Do not claim that you performed an action
   unless a Python tool has performed it.
4. Give concise and practical answers.
5. Answer in the same language/style as the user.

{context}

User:
{message}

Answer:
""".strip()

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 250,
        },
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=120,
        ) as response:

            response_data = json.loads(
                response.read().decode("utf-8")
            )

        return response_data.get(
            "response",
            "I couldn't generate a response.",
        ).strip()

    except urllib.error.URLError:
        is_hi = _is_hinglish(message)
        fallback = dashboard and _format_dashboard(dashboard, is_hi)
        if fallback:
            if is_hi:
                return f"{fallback}\n\n(Ollama offline — verified LifeOS snapshot dikhaya gaya hai.)"
            return f"{fallback}\n\n(Ollama offline — showing verified LifeOS snapshot.)"
        if is_hi:
            return "AI brain offline hai (Ollama running nahi hai). Tumhare tasks, goals aur habits abhi bhi available hain."
        return "AI brain is offline (Ollama not running). Your tasks, goals and habits are still available."

    except json.JSONDecodeError:
        if _is_hinglish(message):
            return "AI response invalid aaya — please dobara try karo."
        return "AI response was invalid — please try again."
    except RuntimeError as exc:
        msg = str(exc)
        if "Ollama" in msg:
            is_hi = _is_hinglish(message)
            fallback = None
            try:
                if dashboard is not None:
                    fallback = _format_dashboard(dashboard, is_hi)
            except Exception:
                fallback = None
            if fallback:
                if is_hi:
                    return f"{fallback}\n\n(Ollama offline — verified LifeOS snapshot dikhaya gaya hai.)"
                return f"{fallback}\n\n(Ollama offline — showing verified LifeOS snapshot.)"
            if is_hi:
                return "AI brain offline hai — local LLM chat ke liye Ollama start karo."
            return "AI brain is offline — please start Ollama to enable local LLM chat."
        raise