from __future__ import annotations

FULL_SLEEP_MINUTES = 20
FULL_WAKE_MINUTES = 210
SLEEP_THRESHOLD = 0.98
RESET_SLEEPINESS = 0.2


def _clamp_sleepiness(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def format_hours_minutes(total_minutes: int) -> str:
    total_minutes = max(0, int(total_minutes))
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}小时{minutes}分钟"


def build_companion_time_label(total_minutes: int) -> str:
    return f"陪你学习已经：{format_hours_minutes(total_minutes)}"


def build_total_companion_label(total_minutes: int) -> str:
    return f"累计陪伴：{format_hours_minutes(total_minutes)}"


def build_sleep_prompt_text() -> str:
    return "黄诗宇困啦，准备去睡一会儿。"


def evolve_sleep_cycle(
    *,
    sleepiness: float,
    is_sleeping: bool,
    auto_sleep_enabled: bool,
    sleep_elapsed_minutes: int,
    delta_minutes: int,
) -> dict[str, object]:
    delta_minutes = max(0, int(delta_minutes))
    sleepiness = _clamp_sleepiness(sleepiness)

    if is_sleeping:
        next_sleep_elapsed = sleep_elapsed_minutes + delta_minutes
        next_sleepiness = max(0.0, sleepiness - (delta_minutes / FULL_SLEEP_MINUTES))
        woke_up = next_sleep_elapsed >= FULL_SLEEP_MINUTES
        return {
            "sleepiness": RESET_SLEEPINESS if woke_up else next_sleepiness,
            "is_sleeping": not woke_up,
            "sleep_elapsed_minutes": 0 if woke_up else next_sleep_elapsed,
            "should_warn": False,
        }

    next_sleepiness = min(1.0, sleepiness + (delta_minutes / FULL_WAKE_MINUTES))
    should_warn = next_sleepiness >= SLEEP_THRESHOLD
    should_sleep = auto_sleep_enabled and should_warn
    return {
        "sleepiness": next_sleepiness,
        "is_sleeping": should_sleep,
        "sleep_elapsed_minutes": 0,
        "should_warn": should_warn,
    }
