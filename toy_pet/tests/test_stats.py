import unittest

from windows_app.stats import (
    build_companion_time_label,
    build_sleep_prompt_text,
    build_total_companion_label,
    evolve_sleep_cycle,
    format_hours_minutes,
)


class StatsTests(unittest.TestCase):
    def test_format_hours_minutes_uses_hour_minute_text(self) -> None:
        self.assertEqual(format_hours_minutes(135), "2小时15分钟")

    def test_build_companion_time_label_uses_new_copy(self) -> None:
        self.assertEqual(build_companion_time_label(135), "陪你学习已经：2小时15分钟")

    def test_build_total_companion_label_uses_total_copy(self) -> None:
        self.assertEqual(build_total_companion_label(600), "累计陪伴：10小时0分钟")

    def test_evolve_sleep_cycle_rises_sleepiness_while_awake(self) -> None:
        next_state = evolve_sleep_cycle(
            sleepiness=0.0,
            is_sleeping=False,
            auto_sleep_enabled=True,
            sleep_elapsed_minutes=0,
            delta_minutes=120,
        )

        self.assertGreater(next_state["sleepiness"], 0.0)
        self.assertFalse(next_state["is_sleeping"])

    def test_evolve_sleep_cycle_enters_sleep_after_threshold(self) -> None:
        next_state = evolve_sleep_cycle(
            sleepiness=0.97,
            is_sleeping=False,
            auto_sleep_enabled=True,
            sleep_elapsed_minutes=0,
            delta_minutes=15,
        )

        self.assertTrue(next_state["should_warn"])
        self.assertTrue(next_state["is_sleeping"])

    def test_evolve_sleep_cycle_does_not_auto_sleep_when_disabled(self) -> None:
        next_state = evolve_sleep_cycle(
            sleepiness=0.97,
            is_sleeping=False,
            auto_sleep_enabled=False,
            sleep_elapsed_minutes=0,
            delta_minutes=15,
        )

        self.assertTrue(next_state["should_warn"])
        self.assertFalse(next_state["is_sleeping"])

    def test_evolve_sleep_cycle_recovers_after_sleep_duration(self) -> None:
        next_state = evolve_sleep_cycle(
            sleepiness=1.0,
            is_sleeping=True,
            auto_sleep_enabled=True,
            sleep_elapsed_minutes=19,
            delta_minutes=2,
        )

        self.assertFalse(next_state["is_sleeping"])
        self.assertLess(next_state["sleepiness"], 0.5)

    def test_evolve_sleep_cycle_clamps_bad_sleepiness_input(self) -> None:
        awake_state = evolve_sleep_cycle(
            sleepiness=-2.0,
            is_sleeping=False,
            auto_sleep_enabled=False,
            sleep_elapsed_minutes=0,
            delta_minutes=0,
        )
        sleeping_state = evolve_sleep_cycle(
            sleepiness=5.0,
            is_sleeping=True,
            auto_sleep_enabled=True,
            sleep_elapsed_minutes=0,
            delta_minutes=0,
        )

        self.assertEqual(awake_state["sleepiness"], 0.0)
        self.assertEqual(sleeping_state["sleepiness"], 1.0)

    def test_build_sleep_prompt_text_mentions_sleep(self) -> None:
        self.assertIn("睡", build_sleep_prompt_text())


if __name__ == "__main__":
    unittest.main()
