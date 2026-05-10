import json
import tempfile
import unittest
from pathlib import Path

from windows_app.animation import MotionEffect, MotionPhase, build_default_script, ease_in_out_sine, sample_phase
from windows_app.config import compute_initial_position, compute_target_height, load_manifest


class RuntimeMathTests(unittest.TestCase):
    def test_load_manifest_exposes_expected_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "png_name": "pet.png",
                        "svg_name": "pet.svg",
                        "image_size": {"width": 360, "height": 720},
                        "display_ratio": 0.21,
                        "margin_px": 32,
                        "anchor": "right",
                        "motions": ["idle", "jump", "sway"],
                    }
                ),
                encoding="utf-8",
            )

            config = load_manifest(path)

        self.assertEqual(config.png_name, "pet.png")
        self.assertEqual(config.image_size, (360, 720))
        self.assertEqual(config.display_ratio, 0.21)

    def test_load_manifest_defaults_include_kiss_motion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "png_name": "pet.png",
                        "svg_name": "pet.svg",
                        "image_size": {"width": 360, "height": 720},
                        "display_ratio": 0.21,
                        "margin_px": 32,
                        "anchor": "right",
                    }
                ),
                encoding="utf-8",
            )

            config = load_manifest(path)

        self.assertEqual(config.motions, ["idle", "jump", "sway", "kiss"])

    def test_compute_target_height_uses_display_ratio(self) -> None:
        self.assertEqual(compute_target_height(1440, 0.21), 302)

    def test_compute_initial_position_anchors_to_right_edge(self) -> None:
        point = compute_initial_position(1920, 1080, pet_width=280, pet_height=520, margin_px=32)
        self.assertEqual(point, (1608, 528))

    def test_compute_initial_position_supports_left_anchor(self) -> None:
        point = compute_initial_position(
            1920,
            1080,
            pet_width=280,
            pet_height=520,
            margin_px=32,
            anchor="left",
        )
        self.assertEqual(point, (32, 528))

    def test_default_script_contains_required_motion_names(self) -> None:
        names = [phase.name for phase in build_default_script()]
        self.assertEqual(names, ["idle", "jump-up", "jump-down", "sway-out", "sway-back", "kiss"])

    def test_default_script_uses_round_trip_jump_sequence(self) -> None:
        names = [phase.name for phase in build_default_script()]
        self.assertEqual(names[1:3], ["jump-up", "jump-down"])

    def test_default_script_uses_round_trip_sway_sequence(self) -> None:
        names = [phase.name for phase in build_default_script()]
        self.assertEqual(names[3:5], ["sway-out", "sway-back"])

    def test_jump_round_trip_ends_back_at_anchor(self) -> None:
        jump_up = MotionPhase(name="jump-up", duration_ms=360, dx=0, dy=-34, rotation_deg=0.0, scale=1.0)
        jump_down = MotionPhase(name="jump-down", duration_ms=360, dx=0, dy=0, rotation_deg=0.0, scale=1.0)

        self.assertEqual(sample_phase(jump_up, elapsed_ms=360)[1], -34)
        self.assertEqual(sample_phase(jump_down, elapsed_ms=360)[1], 0)

    def test_jump_down_first_tick_stays_between_peak_and_anchor(self) -> None:
        jump_down = next(phase for phase in build_default_script() if phase.name == "jump-down")

        self.assertLess(sample_phase(jump_down, elapsed_ms=40)[1], 0)

    def test_sway_back_first_tick_stays_between_peak_and_anchor(self) -> None:
        sway_back = next(phase for phase in build_default_script() if phase.name == "sway-back")

        self.assertLess(sample_phase(sway_back, elapsed_ms=40)[0], 0)

    def test_sample_phase_eases_to_peak_offset(self) -> None:
        phase = MotionPhase(name="jump", duration_ms=800, dx=0, dy=-24, rotation_deg=0.0, scale=1.0)
        self.assertAlmostEqual(ease_in_out_sine(0.5), 0.5, places=3)
        dx, dy, rotation, scale, effect = sample_phase(phase, elapsed_ms=400)
        self.assertEqual(dx, 0)
        self.assertEqual(dy, -12)
        self.assertEqual(rotation, 0.0)
        self.assertEqual(scale, 1.0)
        self.assertIsNone(effect)

    def test_sample_phase_defaults_to_zero_origin_when_start_values_absent(self) -> None:
        phase = MotionPhase(name="sway", duration_ms=800, dx=-8, dy=0, rotation_deg=-2.0, scale=1.0)

        dx, dy, rotation, scale, effect = sample_phase(phase, elapsed_ms=400)

        self.assertEqual((dx, dy, scale, effect), (-4, 0, 1.0, None))
        self.assertAlmostEqual(rotation, -1.0)

    def test_default_script_contains_kiss_motion(self) -> None:
        names = [phase.name for phase in build_default_script()]
        self.assertEqual(names, ["idle", "jump-up", "jump-down", "sway-out", "sway-back", "kiss"])

    def test_default_jump_motion_uses_stronger_vertical_offset(self) -> None:
        jump = next(phase for phase in build_default_script() if phase.name == "jump-up")
        self.assertEqual(jump.dy, -34)

    def test_kiss_phase_emits_heart_effect_metadata(self) -> None:
        kiss = MotionPhase(
            name="kiss",
            duration_ms=900,
            dx=0,
            dy=-4,
            rotation_deg=0.0,
            scale=1.0,
            effect_name="heart",
            effect_dx=36,
            effect_dy=-18,
        )

        dx, dy, rotation, scale, effect = sample_phase(kiss, elapsed_ms=450)

        self.assertEqual((dx, dy, rotation, scale), (0, -2, 0.0, 1.0))
        self.assertEqual(effect, MotionEffect(name="heart", offset=(18, -9)))

    def test_sample_phase_rejects_non_positive_duration(self) -> None:
        phase = MotionPhase(name="idle", duration_ms=0, dx=0, dy=0, rotation_deg=0.0, scale=1.0)

        with self.assertRaisesRegex(ValueError, "duration_ms must be positive"):
            sample_phase(phase, elapsed_ms=0)


if __name__ == "__main__":
    unittest.main()
