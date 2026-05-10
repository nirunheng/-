import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from girlfriend_terminal_pet.prepare_asset import build_parser, main, run_pipeline


class PrepareAssetTests(unittest.TestCase):
    def test_requirements_wsl_exists_for_wrapper_install_step(self) -> None:
        requirements = Path(__file__).resolve().parents[1] / "requirements-wsl.txt"

        self.assertTrue(requirements.exists())

    def test_prepare_asset_wrapper_contains_expected_commands(self) -> None:
        wrapper = (Path(__file__).resolve().parents[1] / "prepare_asset.sh").read_text(encoding="utf-8")

        self.assertIn('requirements-wsl.txt', wrapper)
        self.assertIn('--break-system-packages', wrapper)
        self.assertIn('PYTHONPATH="$PROJECT_DIR/src"', wrapper)
        self.assertIn('python3 -m girlfriend_terminal_pet.prepare_asset', wrapper)
        self.assertIn('--source "$PROJECT_DIR/../new_hh/hh.jpg"', wrapper)
        self.assertIn('--output-dir "$PROJECT_DIR/assets"', wrapper)

    def test_prepare_asset_wrapper_is_executable(self) -> None:
        wrapper_path = Path(__file__).resolve().parents[1] / "prepare_asset.sh"

        self.assertTrue(os.access(wrapper_path, os.X_OK))

    def make_source(self, path: Path) -> None:
        image = Image.new("RGB", (40, 60), (255, 255, 255))
        for x in range(8, 32):
            for y in range(6, 54):
                image.putpixel((x, y), (90, 60, 140))
        image.save(path)

    def fake_remove(self, payload: bytes) -> bytes:
        return payload

    def test_run_pipeline_writes_png_svg_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            output_dir = root / "assets"
            self.make_source(source)

            result = run_pipeline(
                source_path=source,
                output_dir=output_dir,
                remove_bytes_fn=self.fake_remove,
                target_height=300,
                display_ratio=0.22,
                margin_px=28,
            )

            self.assertTrue((output_dir / "pet.png").exists())
            self.assertTrue((output_dir / "pet.svg").exists())
            self.assertTrue((output_dir / "manifest.json").exists())
            self.assertEqual(result["png_name"], "pet.png")

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["display_ratio"], 0.22)
            self.assertEqual(manifest["margin_px"], 28)

    def test_run_pipeline_preserves_expected_output_names_and_saved_image_size(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            output_dir = root / "assets"
            self.make_source(source)

            result = run_pipeline(
                source_path=source,
                output_dir=output_dir,
                remove_bytes_fn=self.fake_remove,
                target_height=300,
            )

            png_path = output_dir / "pet.png"
            svg_path = output_dir / "pet.svg"
            manifest_path = output_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            saved = Image.open(png_path)
            baseline = Image.open(source).convert("RGBA").resize(saved.size, Image.Resampling.LANCZOS)

            self.assertEqual(sorted(path.name for path in output_dir.iterdir()), ["manifest.json", "pet.png", "pet.svg"])
            self.assertEqual(result["png_name"], "pet.png")
            self.assertEqual(result["svg_name"], "pet.svg")
            self.assertEqual(manifest["png_name"], "pet.png")
            self.assertEqual(manifest["svg_name"], "pet.svg")
            self.assertEqual(manifest["image_size"], {"width": saved.width, "height": saved.height})
            self.assertNotEqual(list(saved.getdata()), list(baseline.getdata()))
            self.assertIn("data:image/png;base64,", svg_path.read_text(encoding="utf-8"))

    def test_build_parser_uses_documented_defaults(self) -> None:
        args = build_parser().parse_args(["--source", "source.png", "--output-dir", "assets"])

        self.assertEqual(args.target_height, 960)
        self.assertEqual(args.display_ratio, 0.21)
        self.assertEqual(args.margin_px, 32)

    def test_main_exits_when_source_image_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_source = root / "missing.png"
            output_dir = root / "assets"

            with mock.patch.object(
                sys,
                "argv",
                [
                    "prepare_asset",
                    "--source",
                    str(missing_source),
                    "--output-dir",
                    str(output_dir),
                ],
            ):
                with self.assertRaises(SystemExit) as error:
                    main()

        self.assertEqual(str(error.exception), f"Missing source image: {missing_source}")

    def test_main_runs_pipeline_prints_success_and_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            output_dir = root / "assets"
            self.make_source(source)

            with mock.patch.object(
                sys,
                "argv",
                [
                    "prepare_asset",
                    "--source",
                    str(source),
                    "--output-dir",
                    str(output_dir),
                ],
            ):
                with mock.patch("girlfriend_terminal_pet.prepare_asset.run_pipeline") as run_pipeline_mock:
                    with mock.patch("builtins.print") as print_mock:
                        result = main()

        run_pipeline_mock.assert_called_once_with(
            source_path=source,
            output_dir=output_dir,
            target_height=960,
            display_ratio=0.21,
            margin_px=32,
        )
        print_mock.assert_called_once_with(f"Assets generated in {output_dir}")
        self.assertEqual(result, 0)

    def test_main_passes_non_default_cli_values_to_run_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            output_dir = root / "assets"
            self.make_source(source)

            with mock.patch.object(
                sys,
                "argv",
                [
                    "prepare_asset",
                    "--source",
                    str(source),
                    "--output-dir",
                    str(output_dir),
                    "--target-height",
                    "720",
                    "--display-ratio",
                    "0.33",
                    "--margin-px",
                    "18",
                ],
            ):
                with mock.patch("girlfriend_terminal_pet.prepare_asset.run_pipeline") as run_pipeline_mock:
                    with mock.patch("builtins.print"):
                        main()

        run_pipeline_mock.assert_called_once_with(
            source_path=source,
            output_dir=output_dir,
            target_height=720,
            display_ratio=0.33,
            margin_px=18,
        )


if __name__ == "__main__":
    unittest.main()
