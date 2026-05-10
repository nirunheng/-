from __future__ import annotations

import argparse
import io
from pathlib import Path

from PIL import Image

from .asset_pipeline import build_svg_wrapper, enhance_subject_image, normalize_subject, write_manifest


def default_remove_bytes(payload: bytes) -> bytes:
    from rembg import remove

    return remove(payload)


def run_pipeline(
    *,
    source_path: Path,
    output_dir: Path,
    remove_bytes_fn=default_remove_bytes,
    target_height: int = 960,
    display_ratio: float = 0.21,
    margin_px: int = 32,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cutout_bytes = remove_bytes_fn(source_path.read_bytes())
    cutout = Image.open(io.BytesIO(cutout_bytes)).convert("RGBA")
    normalized = normalize_subject(cutout, target_height=target_height, padding=24)
    normalized = enhance_subject_image(normalized)

    png_path = output_dir / "pet.png"
    normalized.save(png_path)

    svg_path = output_dir / "pet.svg"
    svg_path.write_text(
        build_svg_wrapper(png_path.read_bytes(), normalized.width, normalized.height),
        encoding="utf-8",
    )

    manifest_path = output_dir / "manifest.json"
    return write_manifest(
        manifest_path,
        png_name=png_path.name,
        svg_name=svg_path.name,
        image_size=(normalized.width, normalized.height),
        display_ratio=display_ratio,
        margin_px=margin_px,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate desktop pet assets from a photo")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target-height", type=int, default=960)
    parser.add_argument("--display-ratio", type=float, default=0.21)
    parser.add_argument("--margin-px", type=int, default=32)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.source.exists():
        raise SystemExit(f"Missing source image: {args.source}")

    run_pipeline(
        source_path=args.source,
        output_dir=args.output_dir,
        target_height=args.target_height,
        display_ratio=args.display_ratio,
        margin_px=args.margin_px,
    )
    print(f"Assets generated in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
