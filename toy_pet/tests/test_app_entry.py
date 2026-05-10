import unittest
from pathlib import Path

import windows_app.app as app_module
from windows_app.animation import MotionEffect, build_default_script, sample_phase
from windows_app.app import (
    advance_animation,
    build_info_lines,
    build_info_font_point_size,
    build_menu_labels,
    build_parser,
    build_single_motion_script,
    build_status_summary,
    build_tick_snapshot,
    clamp_scale,
    dispatch_menu_action,
    format_elapsed_seconds,
    simulate_script_cycles,
)
from windows_app.config import PetConfig


class AppEntryTests(unittest.TestCase):
    def test_run_windows_wrapper_uses_module_entrypoint(self) -> None:
        wrapper = (Path(__file__).resolve().parents[1] / "run_windows.bat").read_text(encoding="utf-8")

        self.assertIn('set "PYTHONPATH=%PROJECT_DIR%"', wrapper)
        self.assertIn('python -m windows_app.app --manifest "%MANIFEST%"', wrapper)

    def test_run_windows_wrapper_checks_pillow_dependency(self) -> None:
        wrapper = (Path(__file__).resolve().parents[1] / "run_windows.bat").read_text(encoding="utf-8")

        self.assertIn('python -m pip show Pillow >nul 2>&1', wrapper)
        self.assertIn('Missing Pillow. Run:', wrapper)

    def test_parser_defaults_to_assets_manifest(self) -> None:
        parser = build_parser()
        args = parser.parse_args([])
        self.assertEqual(args.manifest, Path("assets/manifest.json"))
        self.assertFalse(args.dry_run)

    def test_status_summary_mentions_png_and_position(self) -> None:
        config = PetConfig(
            root_dir=Path("assets"),
            png_name="pet.png",
            svg_name="pet.svg",
            image_size=(360, 720),
            display_ratio=0.21,
            margin_px=32,
            anchor="right",
            motions=["idle", "jump", "sway"],
        )
        summary = build_status_summary(config, position=(1608, 528), target_height=302)
        self.assertIn("pet.png", summary)
        self.assertIn("1608,528", summary)
        self.assertIn("302", summary)

    def test_format_elapsed_seconds_uses_hh_mm_ss(self) -> None:
        self.assertEqual(format_elapsed_seconds(3723), "01:02:03")

    def test_format_elapsed_seconds_handles_zero(self) -> None:
        self.assertEqual(format_elapsed_seconds(0), "00:00:00")

    def test_format_elapsed_seconds_clamps_negative_values(self) -> None:
        self.assertEqual(format_elapsed_seconds(-12), "00:00:00")

    def test_format_elapsed_seconds_truncates_fractional_seconds(self) -> None:
        self.assertEqual(format_elapsed_seconds(75.9), "00:01:15")

    def test_format_elapsed_seconds_handles_nan(self) -> None:
        self.assertEqual(format_elapsed_seconds(float("nan")), "00:00:00")

    def test_format_elapsed_seconds_handles_inf(self) -> None:
        self.assertEqual(format_elapsed_seconds(float("inf")), "00:00:00")

    def test_build_info_lines_hides_timer_when_requested(self) -> None:
        lines = build_info_lines(
            name="黄诗宇",
            session_minutes=75,
            total_minutes=600,
            show_session_time=False,
            show_total_time=False,
        )
        self.assertEqual(lines, ["黄诗宇"])

    def test_build_info_lines_shows_name_and_study_timer(self) -> None:
        lines = build_info_lines(
            name="黄诗宇",
            session_minutes=75,
            total_minutes=600,
            show_session_time=True,
            show_total_time=False,
        )
        self.assertEqual(lines, ["黄诗宇", "陪你学习已经：1小时15分钟"])

    def test_build_menu_labels_matches_enhancement_spec(self) -> None:
        self.assertEqual(
            build_menu_labels(),
            [
                "自动循环",
                "Idle",
                "Jump",
                "Sway",
                "Kiss",
                "摸摸头",
                "开启/关闭自动睡觉",
                "显示/隐藏本次陪伴时间",
                "显示/隐藏累计陪伴时间",
                "缩放大一点",
                "缩放小一点",
                "重置位置",
                "修改名字",
                "退出",
            ],
        )

    def test_build_menu_labels_includes_stats_actions(self) -> None:
        self.assertIn("摸摸头", build_menu_labels())
        self.assertIn("开启/关闭自动睡觉", build_menu_labels())
        self.assertIn("显示/隐藏本次陪伴时间", build_menu_labels())
        self.assertIn("显示/隐藏累计陪伴时间", build_menu_labels())

    def test_build_status_lines_shows_affection_and_sleepiness(self) -> None:
        self.assertEqual(
            app_module.build_status_lines(affection=7, sleepiness=0.45),
            ["亲密度：7", "困倦值：45%"],
        )

    def test_build_info_lines_can_include_total_companion_time(self) -> None:
        lines = build_info_lines(
            name="黄诗宇",
            session_minutes=135,
            total_minutes=600,
            show_session_time=True,
            show_total_time=True,
        )
        self.assertEqual(lines, ["黄诗宇", "陪你学习已经：2小时15分钟", "累计陪伴：10小时0分钟"])

    def test_clamp_scale_limits_runtime_scale_range(self) -> None:
        self.assertEqual(clamp_scale(0.2), 0.6)
        self.assertEqual(clamp_scale(1.0), 1.0)
        self.assertEqual(clamp_scale(2.5), 1.6)

    def test_build_single_motion_script_keeps_only_requested_state(self) -> None:
        script = build_single_motion_script("Kiss")
        self.assertEqual([phase.name for phase in script], ["kiss"])

    def test_build_single_motion_script_keeps_jump_as_round_trip_pair(self) -> None:
        script = build_single_motion_script("Jump")

        self.assertEqual([phase.name for phase in script], ["jump-up", "jump-down"])

    def test_build_single_motion_script_keeps_sway_as_round_trip_pair(self) -> None:
        script = build_single_motion_script("Sway")

        self.assertEqual([phase.name for phase in script], ["sway-out", "sway-back"])

    def test_build_info_font_point_size_scales_with_runtime_factor(self) -> None:
        small = build_info_font_point_size(0.6)
        medium = build_info_font_point_size(1.0)
        large = build_info_font_point_size(1.6)

        self.assertLess(small, medium)
        self.assertLess(medium, large)
        self.assertGreaterEqual(small, 8)
        self.assertLessEqual(large, 16)

    def test_dispatch_menu_action_switches_script_and_resets_phase_timing(self) -> None:
        result = dispatch_menu_action(
            label="Kiss",
            script=build_default_script(),
            phase_index=2,
            elapsed_ms=120,
            pet_name="黄诗宇",
            show_session_time=True,
            show_total_time=False,
            auto_sleep_enabled=True,
            scale_factor=1.0,
            affection=0,
        )

        self.assertEqual([phase.name for phase in result["script"]], ["kiss"])
        self.assertEqual(result["phase_index"], 0)
        self.assertEqual(result["elapsed_ms"], 0)
        self.assertFalse(result["request_layout"])

    def test_dispatch_menu_action_handles_layout_and_window_flags(self) -> None:
        scaled = dispatch_menu_action(
            label="缩放大一点",
            script=build_default_script(),
            phase_index=0,
            elapsed_ms=0,
            pet_name="黄诗宇",
            show_session_time=True,
            show_total_time=False,
            auto_sleep_enabled=True,
            scale_factor=1.55,
            affection=0,
        )
        toggled_session = dispatch_menu_action(
            label="显示/隐藏本次陪伴时间",
            script=build_default_script(),
            phase_index=0,
            elapsed_ms=0,
            pet_name="黄诗宇",
            show_session_time=True,
            show_total_time=False,
            auto_sleep_enabled=True,
            scale_factor=1.0,
            affection=0,
        )
        toggled_total = dispatch_menu_action(
            label="显示/隐藏累计陪伴时间",
            script=build_default_script(),
            phase_index=0,
            elapsed_ms=0,
            pet_name="黄诗宇",
            show_session_time=True,
            show_total_time=False,
            auto_sleep_enabled=True,
            scale_factor=1.0,
            affection=0,
        )
        reset = dispatch_menu_action(
            label="重置位置",
            script=build_default_script(),
            phase_index=0,
            elapsed_ms=0,
            pet_name="黄诗宇",
            show_session_time=True,
            show_total_time=False,
            auto_sleep_enabled=True,
            scale_factor=1.0,
            affection=0,
        )
        closed = dispatch_menu_action(
            label="退出",
            script=build_default_script(),
            phase_index=0,
            elapsed_ms=0,
            pet_name="黄诗宇",
            show_session_time=True,
            show_total_time=False,
            auto_sleep_enabled=True,
            scale_factor=1.0,
            affection=0,
        )

        self.assertEqual(scaled["scale_factor"], 1.6)
        self.assertTrue(scaled["request_layout"])
        self.assertFalse(toggled_session["show_session_time"])
        self.assertFalse(toggled_session["show_total_time"])
        self.assertTrue(toggled_session["request_layout"])
        self.assertTrue(toggled_total["show_session_time"])
        self.assertTrue(toggled_total["show_total_time"])
        self.assertTrue(toggled_total["request_layout"])
        self.assertTrue(reset["reset_position"])
        self.assertTrue(closed["should_close"])

    def test_build_tick_snapshot_returns_runtime_view_state(self) -> None:
        snapshot = build_tick_snapshot(
            script=build_single_motion_script("Kiss"),
            phase_index=0,
            elapsed_ms=0,
            anchor_pos=(1608, 528),
            name="黄诗宇",
            affection=7,
            sleepiness=0.45,
            is_sleeping=False,
            auto_sleep_enabled=True,
            sleep_elapsed_minutes=0,
            session_minutes=135,
            total_minutes=600,
            show_session_time=True,
            show_total_time=True,
            delta_minutes=0,
        )

        self.assertEqual(snapshot["position"], (1608, 528))
        self.assertEqual(snapshot["phase_index"], 0)
        self.assertEqual(snapshot["elapsed_ms"], 40)
        self.assertEqual(snapshot["info_lines"], ["黄诗宇", "陪你学习已经：2小时15分钟", "累计陪伴：10小时0分钟"])
        self.assertEqual(snapshot["status_lines"], ["亲密度：7", "困倦值：45%"])
        self.assertTrue(snapshot["show_heart"])
        self.assertEqual(snapshot["prompt_text"], "")
        self.assertFalse(snapshot["should_hide_window"])

    def test_build_tick_snapshot_can_hide_session_time_without_hiding_total(self) -> None:
        snapshot = build_tick_snapshot(
            script=build_single_motion_script("Kiss"),
            phase_index=0,
            elapsed_ms=0,
            anchor_pos=(1608, 528),
            name="黄诗宇",
            affection=0,
            sleepiness=0.0,
            is_sleeping=False,
            auto_sleep_enabled=True,
            sleep_elapsed_minutes=0,
            session_minutes=135,
            total_minutes=600,
            show_session_time=False,
            show_total_time=True,
            delta_minutes=0,
        )

        self.assertEqual(snapshot["info_lines"], ["黄诗宇", "累计陪伴：10小时0分钟"])

    def test_dispatch_menu_action_can_raise_affection(self) -> None:
        result = dispatch_menu_action(
            label="摸摸头",
            script=build_default_script(),
            phase_index=0,
            elapsed_ms=0,
            pet_name="黄诗宇",
            show_session_time=True,
            show_total_time=False,
            auto_sleep_enabled=True,
            scale_factor=1.0,
            affection=7,
        )

        self.assertEqual(result["affection"], 8)

    def test_dispatch_menu_action_toggles_auto_sleep(self) -> None:
        result = dispatch_menu_action(
            label="开启/关闭自动睡觉",
            script=build_default_script(),
            phase_index=0,
            elapsed_ms=0,
            pet_name="黄诗宇",
            show_session_time=True,
            show_total_time=False,
            auto_sleep_enabled=True,
            scale_factor=1.0,
            affection=0,
        )

        self.assertFalse(result["auto_sleep_enabled"])

    def test_build_tick_snapshot_shows_sleep_prompt_before_hiding(self) -> None:
        snapshot = build_tick_snapshot(
            script=build_default_script(),
            phase_index=0,
            elapsed_ms=0,
            anchor_pos=(1608, 528),
            name="黄诗宇",
            affection=5,
            sleepiness=0.99,
            is_sleeping=False,
            auto_sleep_enabled=True,
            sleep_elapsed_minutes=0,
            session_minutes=181,
            total_minutes=900,
            show_session_time=True,
            show_total_time=True,
            delta_minutes=10,
        )

        self.assertFalse(snapshot["should_hide_window"])
        self.assertIn("睡", snapshot["prompt_text"])
        self.assertFalse(snapshot["is_sleeping"])
        self.assertEqual(snapshot["sleep_elapsed_minutes"], 40)

    def test_build_tick_snapshot_keeps_showing_prompt_across_multiple_40ms_ticks(self) -> None:
        snapshot = {
            "phase_index": 0,
            "elapsed_ms": 0,
            "sleepiness": 0.99,
            "is_sleeping": False,
            "sleep_elapsed_minutes": 0,
        }

        for _ in range(5):
            snapshot = build_tick_snapshot(
                script=build_default_script(),
                phase_index=snapshot["phase_index"],
                elapsed_ms=snapshot["elapsed_ms"],
                anchor_pos=(1608, 528),
                name="黄诗宇",
                affection=5,
                sleepiness=snapshot["sleepiness"],
                is_sleeping=snapshot["is_sleeping"],
                auto_sleep_enabled=True,
                sleep_elapsed_minutes=snapshot["sleep_elapsed_minutes"],
                session_minutes=181,
                total_minutes=900,
                show_session_time=True,
                show_total_time=True,
                delta_minutes=0,
            )

        self.assertFalse(snapshot["should_hide_window"])
        self.assertIn("睡", snapshot["prompt_text"])
        self.assertFalse(snapshot["is_sleeping"])

    def test_build_tick_snapshot_keeps_sleep_prompt_stable_when_auto_sleep_disabled(self) -> None:
        snapshot = {
            "phase_index": 0,
            "elapsed_ms": 0,
            "sleepiness": 0.99,
            "is_sleeping": False,
            "sleep_elapsed_minutes": 0,
        }

        for _ in range(5):
            snapshot = build_tick_snapshot(
                script=build_default_script(),
                phase_index=snapshot["phase_index"],
                elapsed_ms=snapshot["elapsed_ms"],
                anchor_pos=(1608, 528),
                name="黄诗宇",
                affection=5,
                sleepiness=snapshot["sleepiness"],
                is_sleeping=snapshot["is_sleeping"],
                auto_sleep_enabled=False,
                sleep_elapsed_minutes=snapshot["sleep_elapsed_minutes"],
                session_minutes=181,
                total_minutes=900,
                show_session_time=True,
                show_total_time=True,
                delta_minutes=0,
            )

        self.assertIn("睡", snapshot["prompt_text"])
        self.assertFalse(snapshot["should_hide_window"])
        self.assertFalse(snapshot["is_sleeping"])

    def test_build_tick_snapshot_hides_only_after_stable_sleep_prompt_window(self) -> None:
        prompt_snapshot = {
            "phase_index": 0,
            "elapsed_ms": 0,
            "sleepiness": 0.99,
            "is_sleeping": False,
            "sleep_elapsed_minutes": 0,
        }

        for _ in range(5):
            prompt_snapshot = build_tick_snapshot(
                script=build_default_script(),
                phase_index=prompt_snapshot["phase_index"],
                elapsed_ms=prompt_snapshot["elapsed_ms"],
                anchor_pos=(1608, 528),
                name="黄诗宇",
                affection=5,
                sleepiness=prompt_snapshot["sleepiness"],
                is_sleeping=prompt_snapshot["is_sleeping"],
                auto_sleep_enabled=True,
                sleep_elapsed_minutes=prompt_snapshot["sleep_elapsed_minutes"],
                session_minutes=181,
                total_minutes=900,
                show_session_time=True,
                show_total_time=True,
                delta_minutes=0,
            )

        hidden_snapshot = prompt_snapshot
        for _ in range(40):
            hidden_snapshot = build_tick_snapshot(
                script=build_default_script(),
                phase_index=hidden_snapshot["phase_index"],
                elapsed_ms=hidden_snapshot["elapsed_ms"],
                anchor_pos=(1608, 528),
                name="黄诗宇",
                affection=5,
                sleepiness=hidden_snapshot["sleepiness"],
                is_sleeping=hidden_snapshot["is_sleeping"],
                auto_sleep_enabled=True,
                sleep_elapsed_minutes=hidden_snapshot["sleep_elapsed_minutes"],
                session_minutes=182,
                total_minutes=901,
                show_session_time=True,
                show_total_time=True,
                delta_minutes=0,
            )

        self.assertIn("睡", prompt_snapshot["prompt_text"])
        self.assertFalse(prompt_snapshot["should_hide_window"])
        self.assertTrue(hidden_snapshot["should_hide_window"])

    def test_app_source_persists_only_when_state_payload_changes(self) -> None:
        app_source = (Path(__file__).resolve().parents[1] / "windows_app" / "app.py").read_text(encoding="utf-8")

        self.assertIn("def build_persisted_state_payload", app_source)
        self.assertIn("def persist_state_if_changed", app_source)
        self.assertIn("if payload == self._persisted_state_cache:", app_source)
        self.assertIn("self.persist_state_if_changed()", app_source)

    def test_tick_wiring_passes_script_to_build_tick_snapshot_by_keyword(self) -> None:
        app_source = (Path(__file__).resolve().parents[1] / "windows_app" / "app.py").read_text(encoding="utf-8")

        self.assertIn("build_tick_snapshot(\n                script=self._script,", app_source)
        self.assertIn("affection=self._affection", app_source)
        self.assertIn("sleepiness=self._sleepiness", app_source)
        self.assertIn("is_sleeping=self._is_sleeping", app_source)
        self.assertIn("auto_sleep_enabled=self._auto_sleep_enabled", app_source)
        self.assertIn("sleep_elapsed_minutes=self._sleep_elapsed_minutes", app_source)
        self.assertIn("session_minutes=session_minutes", app_source)
        self.assertIn("show_session_time=self._show_session_time", app_source)
        self.assertIn("show_total_time=self._show_total_time", app_source)
        self.assertIn("delta_minutes=delta_minutes", app_source)

    def test_apply_layout_uses_minute_based_info_lines_contract(self) -> None:
        app_source = (Path(__file__).resolve().parents[1] / "windows_app" / "app.py").read_text(encoding="utf-8")

        self.assertIn("build_info_lines(\n                        name=self._pet_name,", app_source)
        self.assertIn("session_minutes=self._last_tick_minutes", app_source)
        self.assertIn("total_minutes=self._total_companion_seconds // 60", app_source)
        self.assertIn("show_session_time=self._show_session_time", app_source)
        self.assertIn("show_total_time=self._show_total_time", app_source)

    def test_app_source_wires_persisted_runtime_state_into_window(self) -> None:
        app_source = (Path(__file__).resolve().parents[1] / "windows_app" / "app.py").read_text(encoding="utf-8")

        self.assertIn('state_path = Path.home() / ".girlfriend-terminal-pet" / "state.json"', app_source)
        self.assertIn("persisted_state = load_pet_state(state_path)", app_source)
        self.assertIn('self._affection = int(persisted_state["affection"])', app_source)
        self.assertIn('self._auto_sleep_enabled = bool(persisted_state["auto_sleep_enabled"])', app_source)
        self.assertIn('self._total_companion_seconds = int(persisted_state["total_companion_seconds"])', app_source)

    def test_app_source_renders_and_updates_left_top_stats_block(self) -> None:
        app_source = (Path(__file__).resolve().parents[1] / "windows_app" / "app.py").read_text(encoding="utf-8")

        self.assertIn("self.stats_label = QLabel(self.sprite_host)", app_source)
        self.assertIn("self.stats_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)", app_source)
        self.assertIn('self.stats_label.setText("\\n".join(build_status_lines(affection=self._affection, sleepiness=self._sleepiness)))', app_source)
        self.assertIn('self.stats_label.setText("\\n".join(snapshot["status_lines"]))', app_source)
        self.assertIn("self.stats_label.move(8, 8)", app_source)

    def test_app_source_persists_and_hides_sleeping_runtime_state(self) -> None:
        app_source = (Path(__file__).resolve().parents[1] / "windows_app" / "app.py").read_text(encoding="utf-8")

        self.assertIn("self.setVisible(not snapshot[\"should_hide_window\"])", app_source)
        self.assertIn('if snapshot["prompt_text"]:', app_source)
        self.assertIn("save_pet_state(", app_source)
        self.assertIn("total_companion_seconds=self._total_companion_seconds", app_source)

    def test_default_script_does_not_accumulate_drift_across_cycles(self) -> None:
        positions = simulate_script_cycles(build_default_script(), start_pos=(1608, 528), cycles=2)

        self.assertEqual(positions[0], positions[1])

    def test_jump_round_trip_transition_does_not_snap_back_to_anchor(self) -> None:
        script = build_single_motion_script("Jump")

        _peak_position, phase_index, elapsed_ms = advance_animation(
            script,
            phase_index=0,
            elapsed_ms=320,
            anchor_pos=(1608, 528),
        )
        position, _phase_index, _elapsed_ms = advance_animation(
            script,
            phase_index=phase_index,
            elapsed_ms=elapsed_ms,
            anchor_pos=(1608, 528),
        )

        self.assertNotEqual(position, (1608, 528))
        self.assertGreater(position[1], 528 - 34)

    def test_sway_round_trip_transition_does_not_snap_back_to_anchor(self) -> None:
        script = build_single_motion_script("Sway")

        _peak_position, phase_index, elapsed_ms = advance_animation(
            script,
            phase_index=0,
            elapsed_ms=560,
            anchor_pos=(1608, 528),
        )
        position, _phase_index, _elapsed_ms = advance_animation(
            script,
            phase_index=phase_index,
            elapsed_ms=elapsed_ms,
            anchor_pos=(1608, 528),
        )

        self.assertNotEqual(position, (1608, 528))
        self.assertGreaterEqual(position[0], 1608 - 8)
        self.assertLess(position[0], 1608)

    def test_advance_animation_carries_remainder_into_next_phase(self) -> None:
        script = build_default_script()

        position, phase_index, elapsed_ms = advance_animation(
            script,
            phase_index=0,
            elapsed_ms=1480,
            anchor_pos=(1608, 528),
        )
        next_position, next_phase_index, next_elapsed_ms = advance_animation(
            script,
            phase_index=phase_index,
            elapsed_ms=elapsed_ms,
            anchor_pos=(1608, 528),
        )

        self.assertEqual(position, (1608, 528))
        self.assertEqual(phase_index, 1)
        self.assertEqual(elapsed_ms, 20)
        self.assertEqual(next_phase_index, 1)
        self.assertEqual(next_elapsed_ms, 60)
        self.assertLess(next_position[1], 528)

    def test_advance_animation_handles_effect_metadata_from_sample_phase(self) -> None:
        position, phase_index, elapsed_ms = advance_animation(
            build_default_script(),
            phase_index=3,
            elapsed_ms=0,
            anchor_pos=(1608, 528),
        )

        self.assertEqual(position, (1608, 528))
        self.assertEqual(phase_index, 3)
        self.assertEqual(elapsed_ms, 40)

    def test_sample_phase_exposes_stable_effect_type_for_app_layer(self) -> None:
        kiss = build_default_script()[-1]

        _dx, _dy, _rotation, _scale, effect = sample_phase(kiss, elapsed_ms=450)

        self.assertIsInstance(effect, MotionEffect)

    def test_build_sprite_host_layout_keeps_kiss_heart_inside_host_bounds(self) -> None:
        self.assertTrue(hasattr(app_module, "build_sprite_host_layout"))

        layout = app_module.build_sprite_host_layout(
            sprite_size=(200, 200),
            heart_size=(28, 28),
            effect_offset=(36, -18),
        )

        self.assertEqual(layout["host_size"], (288, 206))
        self.assertEqual(layout["sprite_pos"], (44, 6))
        self.assertEqual(layout["heart_pos"], (260, 0))

    def test_build_sprite_host_layout_accounts_for_round_heart_padding(self) -> None:
        layout = app_module.build_sprite_host_layout(
            sprite_size=(200, 200),
            heart_size=(36, 32),
            effect_offset=(36, -18),
        )

        self.assertGreaterEqual(layout["host_size"][0], 292)
        self.assertGreaterEqual(layout["host_size"][1], 206)

    def test_build_default_window_layout_uses_expanded_host_width_for_right_anchor(self) -> None:
        self.assertTrue(hasattr(app_module, "build_default_window_layout"))

        layout = app_module.build_default_window_layout(
            screen_size=(1920, 1080),
            image_size=(400, 800),
            display_ratio=0.25,
            margin_px=32,
            anchor="right",
            heart_size=(36, 32),
            effect_offset=(36, -18),
        )

        self.assertEqual(layout["target_size"], (135, 270))
        self.assertEqual(layout["host_layout"]["host_size"], (239, 276))
        self.assertEqual(layout["position"], (1649, 772))

    def test_app_source_reuses_default_window_layout_for_dry_run_and_gui_defaults(self) -> None:
        app_source = (Path(__file__).resolve().parents[1] / "windows_app" / "app.py").read_text(encoding="utf-8")

        self.assertIn("default_layout = build_default_window_layout(", app_source)
        self.assertIn("self._default_layout = build_default_window_layout(", app_source)

    def test_app_source_uses_rounder_heart_path_drawing(self) -> None:
        app_source = (Path(__file__).resolve().parents[1] / "windows_app" / "app.py").read_text(encoding="utf-8")

        self.assertIn("QPainterPath", app_source)
        self.assertIn("cubicTo", app_source)


if __name__ == "__main__":
    unittest.main()
