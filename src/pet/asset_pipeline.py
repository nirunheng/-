from __future__ import annotations

import base64
import json
from pathlib import Path

from PIL import Image, ImageEnhance


def crop_to_subject(image: Image.Image, padding: int = 24) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("image has no visible subject")

    left, top, right, bottom = bbox
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(image.width, right + padding)
    bottom = min(image.height, bottom + padding)
    return image.crop((left, top, right, bottom))


def normalize_subject(image: Image.Image, target_height: int = 960, padding: int = 24) -> Image.Image:
    cropped = crop_to_subject(image, padding=padding)
    scale = target_height / cropped.height
    target_width = max(1, round(cropped.width * scale))
    return cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)


def enhance_subject_image(image: Image.Image) -> Image.Image:
    enhanced = image.convert("RGBA")
    enhanced = ImageEnhance.Contrast(enhanced).enhance(1.08)
    enhanced = ImageEnhance.Color(enhanced).enhance(1.12)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.15)
    enhanced = ImageEnhance.Brightness(enhanced).enhance(1.03)
    return enhanced


def build_svg_wrapper(png_bytes: bytes, width: int, height: int) -> str:
    payload = base64.b64encode(png_bytes).decode("ascii")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><image href="data:image/png;base64,{payload}" width="{width}" height="{height}"/></svg>'''


def write_manifest(
    manifest_path: Path,
    *,
    png_name: str,
    svg_name: str,
    image_size: tuple[int, int],
    display_ratio: float,
    margin_px: int,
) -> dict[str, object]:
    payload = {
        "png_name": png_name,
        "svg_name": svg_name,
        "image_size": {"width": image_size[0], "height": image_size[1]},
        "display_ratio": display_ratio,
        "margin_px": margin_px,
        "anchor": "right",
        "motions": ["idle", "jump", "sway", "kiss"],
    }
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload
