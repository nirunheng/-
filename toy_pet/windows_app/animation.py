from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class MotionPhase:
    name: str
    duration_ms: int
    dx: int
    dy: int
    rotation_deg: float
    scale: float
    start_dx: int = 0
    start_dy: int = 0
    start_rotation_deg: float = 0.0
    start_scale: float = 1.0
    effect_name: str | None = None
    effect_dx: int = 0
    effect_dy: int = 0


@dataclass(frozen=True)
class MotionEffect:
    name: str
    offset: tuple[int, int]


def ease_in_out_sine(progress: float) -> float:
    progress = min(1.0, max(0.0, progress))
    return -(math.cos(math.pi * progress) - 1.0) / 2.0


def sample_phase(phase: MotionPhase, *, elapsed_ms: int) -> tuple[int, int, float, float, MotionEffect | None]:
    if phase.duration_ms <= 0:
        raise ValueError("duration_ms must be positive")

    amount = ease_in_out_sine(elapsed_ms / phase.duration_ms)
    dx = round(phase.start_dx + ((phase.dx - phase.start_dx) * amount))
    dy = round(phase.start_dy + ((phase.dy - phase.start_dy) * amount))
    rotation = phase.start_rotation_deg + ((phase.rotation_deg - phase.start_rotation_deg) * amount)
    scale = phase.start_scale + ((phase.scale - phase.start_scale) * amount)

    effect = None
    if phase.effect_name is not None:
        effect = MotionEffect(
            name=phase.effect_name,
            offset=(round(phase.effect_dx * amount), round(phase.effect_dy * amount)),
        )

    return (dx, dy, rotation, scale, effect)


def build_default_script() -> list[MotionPhase]:
    return [
        MotionPhase(name="idle", duration_ms=1500, dx=0, dy=-6, rotation_deg=0.0, scale=1.0),
        MotionPhase(name="jump-up", duration_ms=360, dx=0, dy=-34, rotation_deg=0.0, scale=1.0),
        MotionPhase(
            name="jump-down",
            duration_ms=360,
            dx=0,
            dy=0,
            rotation_deg=0.0,
            scale=1.0,
            start_dx=0,
            start_dy=-34,
            start_rotation_deg=0.0,
            start_scale=1.0,
        ),
        MotionPhase(name="sway-out", duration_ms=600, dx=-8, dy=0, rotation_deg=-2.0, scale=1.0),
        MotionPhase(
            name="sway-back",
            duration_ms=600,
            dx=0,
            dy=0,
            rotation_deg=0.0,
            scale=1.0,
            start_dx=-8,
            start_dy=0,
            start_rotation_deg=-2.0,
            start_scale=1.0,
        ),
        MotionPhase(
            name="kiss",
            duration_ms=900,
            dx=0,
            dy=-4,
            rotation_deg=0.0,
            scale=1.0,
            effect_name="heart",
            effect_dx=36,
            effect_dy=-18,
        ),
    ]
