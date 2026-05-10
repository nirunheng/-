import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from girlfriend_terminal_pet.asset_pipeline import (
    build_svg_wrapper,
    crop_to_subject,
    enhance_subject_image,
    normalize_subject,
    write_manifest,
)


class AssetPipelineTests(unittest.TestCase):
    def make_subject(self) -> Image.Image:
        image = Image.new("RGBA", (100, 120), (0, 0, 0, 0))
        for x in range(20, 80):
            for y in range(15, 95):
                image.putpixel((x, y), (120, 80, 200, 255))
        return image

    def test_crop_to_subject_keeps_requested_padding(self) -> None:
        cropped = crop_to_subject(self.make_subject(), padding=8)
        self.assertEqual(cropped.size, (76, 96))
        self.assertEqual(cropped.getbbox(), (8, 8, 68, 88))

    def test_crop_to_subject_uses_alpha_channel_bbox(self) -> None:
        image = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        image.putpixel((0, 0), (255, 0, 0, 0))
        image.putpixel((4, 5), (10, 20, 30, 255))

        with mock.patch.object(
            image,
            "getbbox",
            side_effect=AssertionError("crop_to_subject should use alpha channel bbox"),
        ):
            cropped = crop_to_subject(image, padding=0)

        self.assertEqual(cropped.size, (1, 1))
        self.assertEqual(cropped.getpixel((0, 0)), (10, 20, 30, 255))

    def test_normalize_subject_scales_to_target_height(self) -> None:
        normalized = normalize_subject(self.make_subject(), target_height=240, padding=0)
        self.assertEqual(normalized.height, 240)
        self.assertEqual(normalized.width, 180)

    def test_enhance_subject_image_changes_pixel_values(self) -> None:
        image = Image.new("RGBA", (2, 2), (120, 100, 90, 255))

        enhanced = enhance_subject_image(image)

        self.assertNotEqual(list(image.getdata()), list(enhanced.getdata()))

    def test_enhance_subject_image_preserves_size_and_mode(self) -> None:
        image = self.make_subject()

        enhanced = enhance_subject_image(image)

        self.assertEqual(enhanced.size, image.size)
        self.assertEqual(enhanced.mode, "RGBA")

    def test_build_svg_wrapper_embeds_png_dimensions(self) -> None:
        svg = build_svg_wrapper(b"png-bytes", width=320, height=480)
        self.assertIn('width="320"', svg)
        self.assertIn('height="480"', svg)
        self.assertIn("data:image/png;base64,", svg)

    def test_write_manifest_records_relative_asset_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            manifest_path = output_dir / "manifest.json"
            write_manifest(
                manifest_path,
                png_name="pet.png",
                svg_name="pet.svg",
                image_size=(420, 720),
                display_ratio=0.21,
                margin_px=32,
            )
            data = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(data["png_name"], "pet.png")
        self.assertEqual(data["svg_name"], "pet.svg")
        self.assertEqual(data["image_size"], {"width": 420, "height": 720})
        self.assertEqual(data["display_ratio"], 0.21)
        self.assertEqual(data["margin_px"], 32)
        self.assertEqual(data["anchor"], "right")
        self.assertEqual(data["motions"], ["idle", "jump", "sway", "kiss"])

    def test_checked_in_manifest_matches_runtime_default_motions(self) -> None:
        manifest_path = Path(__file__).resolve().parents[1] / "assets" / "manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(data["motions"], ["idle", "jump", "sway", "kiss"])


if __name__ == "__main__":
    unittest.main()
