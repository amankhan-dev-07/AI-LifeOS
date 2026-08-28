import json
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

    # =========================================================
    # HABIT COMPLETE
    # =========================================================

    if db is not None and user_id is not None:
        habit_id = _extract_habit_id(text)

        if (
            habit_id is not None
            and _is_habit_complete_request(text)
        ):
            result = complete_habit_tool(
                db=db,
                user_id=user_id,
                habit_id=habit_id,
            )

            if not result["success"]:
                return f"Habit complete nahi ho paya: {result['error']}"

            habit = result["habit"]

            return (
                "Done bhai, habit complete kar di:\n"
                f"• {habit['title']}\n"
                f"• Current streak: {habit['current_streak']} days\n"
                f"• Best streak: {habit['longest_streak']} days"
            )

    # =========================================================
    # HABIT DELETE
    # =========================================================

    if db is not None and user_id is not None:
        habit_id = _extract_habit_id(text)

        if (
            habit_id is not None
            and _is_habit_delete_request(text)
        ):
            result = delete_habit_tool(
                db=db,
                user_id=user_id,
                habit_id=habit_id,
            )

            if not result["success"]:
                return "Habit nahi mila bhai."

            habit = result["habit"]

            return (
                "Done bhai, habit delete kar di:\n"
                f"• {habit['title']}"
            )

    # =========================================================
    # HABIT UPDATE
    # =========================================================

    if db is not None and user_id is not None:
        habit_id = _extract_habit_id(text)

        if (
            habit_id is not None
            and _is_habit_update_request(text)
        ):
            frequency = _extract_habit_frequency(text)

            if frequency is not None:
                result = update_habit_tool(
                    db=db,
                    user_id=user_id,
                    habit_id=habit_id,
                    frequency=frequency,
                )

                if not result["success"]:
                    return "Habit nahi mila bhai."

                habit = result["habit"]

                return (
                    "Done bhai, habit update kar di:\n"
                    f"• {habit['title']}\n"
                    f"• Frequency: {habit['frequency']}"
                )

            if "inactive" in text or "deactivate" in text:
                result = update_habit_tool(
                    db=db,
                    user_id=user_id,
                    habit_id=habit_id,
                    is_active=False,
                )

                if not result["success"]:
                    return "Habit nahi mila bhai."

                habit = result["habit"]

                return (
                    "Done bhai, habit deactivate kar di:\n"
                    f"• {habit['title']}"
                )

            if "active" in text or "activate" in text:
                result = update_habit_tool(
                    db=db,
                    user_id=user_id,
                    habit_id=habit_id,
                    is_active=True,
                )

                if not result["success"]:
                    return "Habit nahi mila bhai."

                habit = result["habit"]

                return (
                    "Done bhai, habit activate kar di:\n"
                    f"• {habit['title']}"
                )

            return (
                "Habit me kya update karna hai, "
                "wo bata de bhai."
            )

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
                    return "Habit create nahi ho payi bhai."

                habit = result["habit"]

                return (
                    "Done bhai, habit create kar di:\n"
                    f"• {habit['title']}\n"
                    f"• Frequency: {habit['frequency']}\n"
                    f"• Current streak: {habit['current_streak']} days"
                )

            return (
                "Habit ka naam bata de bhai, "
                "phir main create kar deta hoon."
            )

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
                return "Habit nahi mila bhai."

            habit = result["habit"]
            completions = result["completions"]

            if not completions:
                return (
                    f"{habit['title']} ki abhi koi "
                    "completion history nahi hai."
                )

            lines = [
                f"{habit['title']} ki completion history:"
            ]

            for completion in completions:
                lines.append(
                    f"• {completion['completed_date']}"
                )

            lines.append(
                f"Current streak: {habit['current_streak']} days"
            )
            lines.append(
                f"Best streak: {habit['longest_streak']} days"
            )

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
                return "Abhi tumhari koi habits nahi hain."

            lines = [
                f"Tumhari total {len(habits)} habits hain:"
            ]

            for habit in habits:
                active_status = (
                    "active"
                    if habit["is_active"]
                    else "inactive"
                )

                lines.append(
                    f"• {habit['title']} "
                    f"({active_status}, "
                    f"{habit['frequency']}, "
                    f"streak {habit['current_streak']})"
                )

            return "\n".join(lines)

    # =========================================================
    # TASK COMPLETE
    # =========================================================

    if db is not None and user_id is not None:
        task_id = _extract_task_id(text)

        if (
            task_id is not None
            and _is_task_complete_request(text)
        ):
            result = complete_task_tool(
                db=db,
                user_id=user_id,
                task_id=task_id,
            )

            if not result["success"]:
                return "Task nahi mila bhai."

            task = result["task"]

            return (
                "Done bhai, task complete kar diya:\n"
                f"• {task['title']}\n"
                f"• Status: {task['status']}"
            )

    # =========================================================
    # TASK DELETE
    # =========================================================

    if db is not None and user_id is not None:
        task_id = _extract_task_id(text)

        if (
            task_id is not None
            and _is_task_delete_request(text)
        ):
            result = delete_task_tool(
                db=db,
                user_id=user_id,
                task_id=task_id,
            )

            if not result["success"]:
                return "Task nahi mila bhai."

            task = result["task"]

            return (
                "Done bhai, task delete kar diya:\n"
                f"• {task['title']}"
            )

    # =========================================================
    # TASK UPDATE
    # =========================================================

    if db is not None and user_id is not None:
        task_id = _extract_task_id(text)

        if (
            task_id is not None
            and _is_task_update_request(text)
        ):
            priority = _extract_priority_if_present(text)

            if priority is not None:
                result = update_task_tool(
                    db=db,
                    user_id=user_id,
                    task_id=task_id,
                    priority=priority,
                )

                if not result["success"]:
                    return "Task nahi mila bhai."

                task = result["task"]

                return (
                    "Done bhai, task update kar diya:\n"
                    f"• {task['title']}\n"
                    f"• Priority: {task['priority']}"
                )

            return (
                "Task me kya update karna hai, "
                "wo bata de bhai."
            )

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

                task = result["task"]

                return (
                    "Done bhai, task create kar diya:\n"
                    f"• {task['title']}\n"
                    f"• Priority: {task['priority']}\n"
                    f"• Status: {task['status']}"
                )

            return (
                "Task ka naam bata de bhai, "
                "phir main create kar deta hoon."
            )

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
                return "Abhi tumhare koi tasks nahi hain."

            lines = [
                f"Tumhare total {len(tasks)} tasks hain:"
            ]

            for task in tasks:
                lines.append(
                    f"• {task['title']} "
                    f"({task['status']}, "
                    f"{task['priority']} priority)"
                )

            return "\n".join(lines)

    # =========================================================
    # GOAL COMPLETE
    # =========================================================

    if db is not None and user_id is not None:
        goal_id = _extract_goal_id(text)

        if (
            goal_id is not None
            and _is_goal_complete_request(text)
        ):
            result = complete_goal_tool(
                db=db,
                user_id=user_id,
                goal_id=goal_id,
            )

            if not result["success"]:
                return "Goal nahi mila bhai."

            goal = result["goal"]

            return (
                "Done bhai, goal complete kar diya:\n"
                f"• {goal['title']}\n"
                f"• Completed: {goal['is_completed']}"
            )

    # =========================================================
    # GOAL DELETE
    # =========================================================

    if db is not None and user_id is not None:
        goal_id = _extract_goal_id(text)

        if (
            goal_id is not None
            and _is_goal_delete_request(text)
        ):
            result = delete_goal_tool(
                db=db,
                user_id=user_id,
                goal_id=goal_id,
            )

            if not result["success"]:
                return "Goal nahi mila bhai."

            goal = result["goal"]

            return (
                "Done bhai, goal delete kar diya:\n"
                f"• {goal['title']}"
            )

    # =========================================================
    # GOAL UPDATE
    # =========================================================

    if db is not None and user_id is not None:
        goal_id = _extract_goal_id(text)

        if (
            goal_id is not None
            and _is_goal_update_request(text)
        ):
            category = _extract_goal_category(text)

            if category is not None:
                result = update_goal_tool(
                    db=db,
                    user_id=user_id,
                    goal_id=goal_id,
                    category=category,
                )

                if not result["success"]:
                    return "Goal nahi mila bhai."

                goal = result["goal"]

                return (
                    "Done bhai, goal update kar diya:\n"
                    f"• {goal['title']}\n"
                    f"• Category: {goal['category']}"
                )

            return (
                "Goal me kya update karna hai, "
                "wo bata de bhai."
            )

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

                goal = result["goal"]

                return (
                    "Done bhai, goal create kar diya:\n"
                    f"• {goal['title']}\n"
                    f"• Category: {goal['category']}\n"
                    f"• Completed: {goal['is_completed']}"
                )

            return (
                "Goal ka naam bata de bhai, "
                "phir main create kar deta hoon."
            )

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
                return "Abhi tumhare koi goals nahi hain."

            lines = [
                f"Tumhare total {len(goals)} goals hain:"
            ]

            for goal in goals:
                status = (
                    "completed"
                    if goal["is_completed"]
                    else "active"
                )

                lines.append(
                    f"• {goal['title']} "
                    f"({status}, {goal['category']})"
                )

            return "\n".join(lines)

       # =========================================================
    # DAILY PLANNER
    # =========================================================

    if db is not None and user_id is not None:
        if _is_daily_plan_request(text):

            result = get_daily_plan_tool(
                db=db,
                user_id=user_id,
            )

            if not result["success"]:
                return (
                    "Bhai aaj ka plan banane me "
                    "problem aa gayi."
                )

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

            return (
                f"Abhi tumhari {count} active "
                f"{'habit' if count == 1 else 'habits'} hain."
            )

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

            return (
                f"Tumhari current streak "
                f"{streak} days ki hai."
            )

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

            return (
                f"Tumhari best streak "
                f"{streak} days ki hai."
            )

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

            return (
                f"Tumhare total {count} "
                f"{'task' if count == 1 else 'tasks'} hain."
            )

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

            return (
                f"Tumhare {count} pending "
                f"{'task' if count == 1 else 'tasks'} hain."
            )

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

            return (
                f"Tumne {count} "
                f"{'task' if count == 1 else 'tasks'} complete kiye hain."
            )

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

            return (
                f"Tumhare total {count} "
                f"{'goal' if count == 1 else 'goals'} hain."
            )

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

            return (
                f"Tumhare {count} active "
                f"{'goal' if count == 1 else 'goals'} hain."
            )

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

            return (
                f"Tumne {count} "
                f"{'goal' if count == 1 else 'goals'} complete kiye hain."
            )

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
            return _format_dashboard(dashboard)

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
    )


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
    phrases = [
        "habit update",
        "update habit",
        "habit ki frequency",
        "habit frequency",
        "frequency change",
        "frequency kar",
        "frequency set",
        "daily kar",
        "weekly kar",
        "monthly kar",
        "habit active",
        "habit inactive",
        "activate habit",
        "deactivate habit",
        "modify habit",
        "habit modify",
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


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
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


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

def _is_daily_plan_request(text: str) -> bool:
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

    return any(
        phrase in text
        for phrase in phrases
    )


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
        "daily",
        "weekly",
        "monthly",
    ]

    for phrase in cleanup_phrases:
        title = title.replace(
            phrase,
            "",
        )

    title = title.strip(" :,-.")
    lowered = title.lower()

    patterns = [
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
            title = (
                title[:index]
                + title[index + len(pattern):]
            ).strip()
            break

    title = title.strip(" :,-.")

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
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


def _is_task_update_request(text: str) -> bool:
    phrases = [
        "task update",
        "update task",
        "task ki priority",
        "task priority",
        "priority change",
        "priority kar",
        "priority set",
        "priority high kar",
        "priority low kar",
        "priority medium kar",
        "high priority kar",
        "low priority kar",
        "medium priority kar",
        "modify task",
        "task modify",
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


def _is_task_create_request(text: str) -> bool:
    phrases = [
        "task bana",
        "task banao",
        "task bana de",
        "task create",
        "task create kar",
        "task add",
        "task add kar",
        "task daal",
        "task likh",
        "ek task",
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


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
    )


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
    phrases = [
        "goal update",
        "update goal",
        "goal ki category",
        "goal category",
        "category change",
        "category kar",
        "category set",
        "category update",
        "career kar",
        "study kar",
        "health kar",
        "fitness kar",
        "personal kar",
        "finance kar",
        "business kar",
        "modify goal",
        "goal modify",
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


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
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


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

    if (
        "high priority" in text
        or "priority high" in text
        or "high priority kar" in text
        or "priority high kar" in text
    ):
        return "high"

    if (
        "medium priority" in text
        or "priority medium" in text
        or "medium priority kar" in text
        or "priority medium kar" in text
    ):
        return "medium"

    if (
        "low priority" in text
        or "priority low" in text
        or "low priority kar" in text
        or "priority low kar" in text
    ):
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
        title = title.replace(
            phrase,
            "",
        )

    title = title.strip(" :,-.")
    lowered = title.lower()

    patterns = [
        "ka task bana de",
        "ka task bana",
        "ka task banao",
        "ka task create kar",
        "ka task create",
        "ka task add kar",
        "ka task add",
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
            title = (
                title[:index]
                + title[index + len(pattern):]
            ).strip()
            break

    title = title.strip(" :,-.")

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
        title = title.replace(
            phrase,
            "",
        )

    title = title.strip(" :,-.")
    lowered = title.lower()

    patterns = [
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
            title = (
                title[:index]
                + title[index + len(pattern):]
            ).strip()
            break

    title = title.strip(" :,-.")

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
) -> str:

    tasks = dashboard["tasks"]
    goals = dashboard["goals"]
    habits = dashboard["habits"]

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


# =============================================================
# LOCAL QWEN
# =============================================================


def _ask_local_model(
    message: str,
    dashboard: dict | None = None,
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

    except urllib.error.URLError as exc:

        raise RuntimeError(
            "Ollama is not running. Please start Ollama first."
        ) from exc

    except json.JSONDecodeError as exc:

        raise RuntimeError(
            "Invalid response received from Ollama."
        ) from exc