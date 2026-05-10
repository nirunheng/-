from __future__ import annotations

import json
from pathlib import Path

DEFAULT_STATE = {
    "affection": 0,
    "total_companion_seconds": 0,
    "auto_sleep_enabled": True,
    "show_session_time": True,
    "show_total_time": False,
}


def load_pet_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return DEFAULT_STATE.copy()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_STATE.copy()

    if not isinstance(payload, dict):
        return DEFAULT_STATE.copy()

    state = DEFAULT_STATE.copy()
    state.update(
        {
            "affection": _sanitize_affection(payload.get("affection")),
            "total_companion_seconds": _sanitize_total_companion_seconds(payload.get("total_companion_seconds")),
            "auto_sleep_enabled": _sanitize_bool(payload.get("auto_sleep_enabled"), True),
            "show_session_time": _sanitize_bool(payload.get("show_session_time"), True),
            "show_total_time": _sanitize_bool(payload.get("show_total_time"), False),
        }
    )
    return state


def save_pet_state(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _sanitize_affection(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _sanitize_total_companion_seconds(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return max(0, value)
    return 0


def _sanitize_bool(value: object, default: bool) -> bool:
    return value if isinstance(value, bool) else default
