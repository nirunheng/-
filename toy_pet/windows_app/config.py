from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PetConfig:
    root_dir: Path
    png_name: str
    svg_name: str
    image_size: tuple[int, int]
    display_ratio: float
    margin_px: int
    anchor: str
    motions: list[str]

    @property
    def png_path(self) -> Path:
        return self.root_dir / self.png_name


def load_manifest(path: Path) -> PetConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return PetConfig(
        root_dir=path.parent,
        png_name=payload["png_name"],
        svg_name=payload["svg_name"],
        image_size=(payload["image_size"]["width"], payload["image_size"]["height"]),
        display_ratio=float(payload["display_ratio"]),
        margin_px=int(payload["margin_px"]),
        anchor=payload.get("anchor", "right"),
        motions=list(payload.get("motions", ["idle", "jump", "sway", "kiss"])),
    )


def compute_target_height(screen_height: int, display_ratio: float) -> int:
    return max(180, round(screen_height * display_ratio))


def compute_initial_position(
    screen_width: int,
    screen_height: int,
    *,
    pet_width: int,
    pet_height: int,
    margin_px: int,
    anchor: str = "right",
) -> tuple[int, int]:
    if anchor == "left":
        x = max(0, margin_px)
    else:
        x = max(0, screen_width - pet_width - margin_px)
    y = max(0, screen_height - pet_height - margin_px)
    return (x, y)
