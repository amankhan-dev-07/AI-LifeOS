"""
Natural-language date and time resolution for AI commands.

Resolves the words a person actually types — "tomorrow", "tonight", "Monday",
"next week", "at 6 PM", "in two hours" — into the project's storage
convention, which is naive UTC everywhere (see `reminder_service.utcnow`
and the column defaults).

The one thing this module is careful about is *ambiguity*. A phrase that
names a day but no time ("tomorrow") is a real answer only when the caller
says what a missing time means — 09:00 for a task due date, 09:00 for a
reminder the user forgot to time. A phrase that names neither ("remind me
sometime") resolves to `None`, and the orchestration layer turns that into a
clarification question rather than guessing. Silence here would surface as a
wrong record written confidently, which is exactly the failure mode Phase 14
exists to remove.

Timezone handling reuses the project's existing pieces: the IANA name comes
from `user_preferences_service` and is applied with `ZoneInfo`, and the
wall-clock → naive-UTC conversion reuses `reminder_service.to_naive_utc`, so
the value that reaches a domain service is indistinguishable from one the
Reminders form submitted.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.timezones import DEFAULT_TIMEZONE, normalize_timezone
from app.services.reminder_service import to_naive_utc


#: Wall-clock time applied to a date-only phrase when the caller supplies no
#: time of its own. Deliberately a single named constant: the two callers
#: (task due date, reminder) agree on it, and it is visible and changeable in
#: one place rather than being inlined at each parse site.
DEFAULT_HOUR = 9

DEFAULT_MINUTE = 0


class AmbiguousTime(Exception):
    """
    The phrase names a date but nothing usable can be attached to it.

    Carries the question the caller should put to the user, so the
    clarification text lives next to the logic that decided it was needed.
    """

    def __init__(self, question: str) -> None:
        super().__init__(question)
        self.question = question


# =========================================================
# WORD TABLES
# =========================================================

_WEEKDAYS = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "tues": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "thurs": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}

#: Relative-duration units for "in two hours" / "after 3 days".
_UNIT_SECONDS = {
    "second": 1,
    "seconds": 1,
    "sec": 1,
    "secs": 1,
    "minute": 60,
    "minutes": 60,
    "min": 60,
    "mins": 60,
    "hour": 3600,
    "hours": 3600,
    "hr": 3600,
    "hrs": 3600,
    "day": 86400,
    "days": 86400,
    "week": 604800,
    "weeks": 604800,
}

_NUMBER_WORDS = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

#: Phrases that fix a day relative to now.
_RELATIVE_DAYS = {
    "today": 0,
    "tonight": 0,
    "now": 0,
    "tomorrow": 1,
    "tmrw": 1,
    "tomorow": 1,
    "yesterday": -1,
}

#: Time-of-day keywords, mapped to the clock time they imply.
_CLOCK_KEYWORDS = {
    "morning": 9,
    "afternoon": 14,
    "evening": 18,
    "night": 21,
    "tonight": 21,
    "noon": 12,
    "midday": 12,
    "midnight": 0,
    "lunch": 13,
    "dinner": 20,
    "breakfast": 8,
}

#: Hinglish / romanised time words the existing brain already recognises, kept
#: so a user switching languages mid-conversation does not lose date parsing.
_HINGLISH_DAYS = {
    "kal": 1,
    "aaj": 0,
    "parso": 1,
    "agle": 1,
}

_HINGLISH_UNITS = {
    "ghante": 3600,
    "ghanta": 3600,
    "saat": 3600,
    "minute": 60,
    "din": 86400,
    "dinon": 86400,
    "hafta": 604800,
    "hafte": 604800,
}


def _words(text: str) -> list[str]:
    """Lowercase word tokens, punctuation stripped from the edges."""

    cleaned = "".join(
        char if char.isalnum() or char.isspace() or char in ".:/-" else " "
        for char in text.lower()
    )

    return cleaned.split()


# =========================================================
# TIME-OF-DAY PARSING
# =========================================================


def _parse_clock(words: list[str]) -> tuple[int, int] | None:
    """
    Pull a wall-clock time out of the token list.

    Handles "6pm", "6:30pm", "at 18:00", "half past six" is not supported and
    simply yields `None`, which the caller treats as absent rather than wrong.
    """

    joined = " ".join(words)

    # "6:30pm" / "18:00" / "6.30"
    for index, word in enumerate(words):
        if ":" not in word and "." not in word:
            continue

        separator = ":" if ":" in word else "."
        head, _, tail = word.partition(separator)

        if not head.isdigit():
            continue

        hour = int(head)

        minute = 0
        if tail[:2].isdigit():
            minute = int(tail[:2])

        meridiem = None
        if len(tail) > 2:
            meridiem = tail[:2]

        # Merge a separate "pm" token: "6:30 pm".
        if meridiem is None and index + 1 < len(words):
            candidate = words[index + 1]
            if candidate in {"am", "pm"}:
                meridiem = candidate

        hour = _apply_meridiem(hour, meridiem)

        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute

    # "6pm" / "at 6"
    for index, word in enumerate(words):
        stem = word
        meridiem = None

        for suffix in ("am", "pm"):
            if stem.endswith(suffix) and len(stem) > len(suffix):
                meridiem = suffix
                stem = stem[: -len(suffix)]
                break

        if not stem.isdigit():
            continue

        # A bare number is only a clock time when a meridiem marker or an
        # explicit "at" precedes it. Otherwise "in 2 hours" would read as
        # 02:00.
        has_marker = meridiem is not None
        if not has_marker and index > 0 and words[index - 1] == "at":
            has_marker = True

        if not has_marker:
            continue

        hour = _apply_meridiem(int(stem), meridiem)

        if 0 <= hour <= 23:
            return hour, 0

    # Bare keyword: "this evening", "at night".
    for word in words:
        if word in _CLOCK_KEYWORDS:
            return _CLOCK_KEYWORDS[word], 0

    return None


def _apply_meridiem(hour: int, meridiem: str | None) -> int:
    if meridiem == "pm" and 1 <= hour <= 11:
        return hour + 12

    if meridiem == "am" and hour == 12:
        return 0

    return hour


# =========================================================
# DATE PARSING
# =========================================================


def _resolve_weekday(
    reference: date,
    words: list[str],
) -> date | None:
    """
    "Monday" means the *next* Monday, including today.

    When today is Monday and the user says "Monday", the same-day reading is
    the more useful one — a command about today should not silently land a
    week out. That matches how the Planner and Tasks screens read a bare
    weekday.
    """

    wants_next = "next" in words

    for word in words:
        if word not in _WEEKDAYS:
            continue

        target = _WEEKDAYS[word]
        delta = (target - reference.weekday()) % 7

        if wants_next and delta == 0:
            delta = 7

        return reference + timedelta(days=delta)

    return None


def _resolve_offset(words: list[str]) -> timedelta | None:
    """Resolve "in two hours" / "in 3 days" to an offset from now."""

    for index, word in enumerate(words):
        if word not in {"in", "after"}:
            continue

        window = words[index + 1 : index + 4]

        quantity = _first_number(window)
        if quantity is None:
            continue

        for candidate in window:
            seconds = _UNIT_SECONDS.get(candidate) or _HINGLISH_UNITS.get(candidate)

            if seconds:
                return timedelta(seconds=quantity * seconds)

    return None


def _first_number(window: list[str]) -> int | None:
    for word in window:
        if word.isdigit():
            return int(word)

        if word in _NUMBER_WORDS:
            return _NUMBER_WORDS[word]

    return None


def _resolve_explicit_date(words: list[str]) -> date | None:
    """Resolve an ISO date the user typed verbatim: "2026-03-14"."""

    for word in words:
        candidate = word.strip("./")
        if len(candidate) == 10 and candidate[4] == "-" and candidate[7] == "-":
            try:
                return datetime.strptime(candidate, "%Y-%m-%d").date()
            except ValueError:
                continue

    return None


def _resolve_month_day(words: list[str]) -> date | None:
    """Resolve "march 14" / "14 march" in the reference year."""

    months = {
        "january": 1,
        "jan": 1,
        "february": 2,
        "feb": 2,
        "march": 3,
        "mar": 3,
        "april": 4,
        "apr": 4,
        "may": 5,
        "june": 6,
        "jun": 6,
        "july": 7,
        "jul": 7,
        "august": 8,
        "aug": 8,
        "september": 9,
        "sep": 9,
        "sept": 9,
        "october": 10,
        "oct": 10,
        "november": 11,
        "nov": 11,
        "december": 12,
        "dec": 12,
    }

    month = None
    day = None

    for word in words:
        if word in months:
            month = months[word]
        elif word.isdigit() and 1 <= int(word) <= 31:
            day = int(word)

    if month is None or day is None:
        return None

    reference_year = date.today().year

    try:
        return date(reference_year, month, day)
    except ValueError:
        return None


# =========================================================
# PUBLIC ENTRY POINT
# =========================================================


def resolve_datetime(
    text: str,
    timezone_name: str | None = None,
    default_hour: int = DEFAULT_HOUR,
    require_time: bool = False,
) -> datetime | None:
    """
    Resolve a natural-language time phrase to a naive-UTC datetime.

    Returns `None` when the text carries no time reference at all, which the
    caller distinguishes from an unresolvable one by passing
    `require_time=True`: in that mode a date without a clock time raises
    `AmbiguousTime` instead of silently picking `default_hour`.

    `default_hour` is only consulted for date-only phrases when
    `require_time` is False, so a task "due tomorrow" gets a concrete instant
    while a reminder "at 6" that lost its meridiem to a typo gets asked
    about.
    """

    zone = _zone(timezone_name)
    now_local = datetime.now(zone)

    words = _words(text)

    if not words:
        if require_time:
            raise AmbiguousTime(
                "I could not read a date or time from that. "
                "Please include one, for example \"tomorrow at 6 PM\"."
            )

        return None

    offset = _resolve_offset(words)

    if offset is not None:
        target_utc = to_naive_utc(
            datetime.now(ZoneInfo("UTC")) + offset
        )
        return target_utc

    clock = _parse_clock(words)

    target_date = _resolve_explicit_date(words)

    if target_date is None:
        target_date = _resolve_month_day(words)

    if target_date is None:
        target_date = _resolve_weekday(now_local.date(), words)

    if target_date is None:
        target_date = _resolve_named_day(now_local.date(), words)

    if target_date is None and _mentions_next_week(words):
        target_date = now_local.date() + timedelta(days=7)

    if target_date is None:
        if require_time and clock is not None:
            # A time of day with no date: today, and let the reminder service
            # reject it if it has already passed.
            target_date = now_local.date()

        if target_date is None:
            if require_time:
                raise AmbiguousTime(
                    "I could not tell which day you meant. "
                    "Please include a date, for example \"tomorrow at 6 PM\"."
                )

            return None

    if clock is None:
        if require_time:
            raise AmbiguousTime(
                "I could not tell what time you meant. "
                "Please include one, for example \"tomorrow at 6 PM\"."
            )

        clock = (default_hour, DEFAULT_MINUTE)

    return to_naive_utc(
        datetime.combine(
            target_date,
            time(hour=clock[0], minute=clock[1]),
        ).replace(tzinfo=zone)
    )


def _resolve_named_day(
    reference: date,
    words: list[str],
) -> date | None:
    """Relative day words, English and romanised Hindi."""

    for word in words:
        if word in _RELATIVE_DAYS:
            return reference + timedelta(days=_RELATIVE_DAYS[word])

        if word in _HINGLISH_DAYS:
            return reference + timedelta(days=_HINGLISH_DAYS[word])

    return None


def _mentions_next_week(words: list[str]) -> bool:
    if "week" not in words and "hafte" not in words and "hafta" not in words:
        return False

    return "next" in words or "agle" in words or "aage" in words


def _zone(timezone_name: str | None) -> ZoneInfo:
    """
    Resolve the user's stored IANA name into a usable zone.

    `normalize_timezone` already repairs an unusable stored value to the
    product default, so this cannot raise on persisted data.
    """

    return ZoneInfo(normalize_timezone(timezone_name) or DEFAULT_TIMEZONE)


def describe_datetime(value: datetime) -> str:
    """Render a resolved instant for the confirmation UI, in UTC terms.

    The confirmation panel shows the value the backend will actually store,
    which is naive UTC. Rendering it that way — rather than re-converting to
    the user's zone here — keeps what the user approves identical to what
    gets written, and the client formats it locally with the utilities it
    already uses.
    """

    if value.tzinfo is None:
        return value.strftime("%Y-%m-%d %H:%M UTC")

    return to_naive_utc(value).strftime("%Y-%m-%d %H:%M UTC")