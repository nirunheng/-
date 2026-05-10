import json
import tempfile
import unittest
from pathlib import Path

from windows_app.persist import DEFAULT_STATE, load_pet_state, save_pet_state


class PersistTests(unittest.TestCase):
    def test_load_pet_state_returns_defaults_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pet-state.json"
            state = load_pet_state(path)

        self.assertEqual(state, DEFAULT_STATE)

    def test_load_pet_state_returns_defaults_when_file_is_corrupted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pet-state.json"
            path.write_text("{not-json", encoding="utf-8")

            state = load_pet_state(path)

        self.assertEqual(state, DEFAULT_STATE)

    def test_load_pet_state_returns_defaults_when_json_root_is_not_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pet-state.json"
            path.write_text("1", encoding="utf-8")

            state = load_pet_state(path)

        self.assertEqual(state, DEFAULT_STATE)

    def test_load_pet_state_reads_total_companion_seconds_from_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pet-state.json"
            path.write_text(
                json.dumps({"affection": 3, "total_companion_seconds": 321}, ensure_ascii=False),
                encoding="utf-8",
            )

            state = load_pet_state(path)

        self.assertEqual(state["total_companion_seconds"], 321)

    def test_load_pet_state_sanitizes_known_field_types(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pet-state.json"
            path.write_text(
                json.dumps(
                    {
                        "affection": "7",
                        "total_companion_seconds": -5,
                        "auto_sleep_enabled": "yes",
                        "show_session_time": 1,
                        "show_total_time": None,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            state = load_pet_state(path)

        self.assertEqual(
            state,
            {
                "affection": 0,
                "total_companion_seconds": 0,
                "auto_sleep_enabled": True,
                "show_session_time": True,
                "show_total_time": False,
            },
        )

    def test_save_pet_state_persists_affection_and_total_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pet-state.json"
            payload = {
                "affection": 7,
                "total_companion_seconds": 135,
                "auto_sleep_enabled": True,
                "show_session_time": True,
                "show_total_time": False,
            }
            save_pet_state(path, payload)
            saved = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(saved, payload)


if __name__ == "__main__":
    unittest.main()
