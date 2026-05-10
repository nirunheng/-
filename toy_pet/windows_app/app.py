from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from PIL import Image

from windows_app.animation import build_default_script, sample_phase
from windows_app.config import compute_initial_position, compute_target_height, load_manifest
from windows_app.persist import load_pet_state, save_pet_state
from windows_app.stats import (
    build_companion_time_label,
    build_sleep_prompt_text,
    build_total_companion_label,
    evolve_sleep_cycle,
)


TICK_MS = 40
HEART_SIZE = (36, 32)
SLEEP_PROMPT_MS = 1200


def build_sprite_host_layout(
    *,
    sprite_size: tuple[int, int],
    heart_size: tuple[int, int],
    effect_offset: tuple[int, int],
) -> dict[str, tuple[int, int]]:
    sprite_width, sprite_height = sprite_size
    heart_width, heart_height = heart_size
    heart_x = sprite_width - 20 + effect_offset[0]
    heart_y = 12 + effect_offset[1]

    horizontal_padding = max(0, -heart_x, heart_x + heart_width - sprite_width)
    top_padding = max(0, -heart_y)
    sprite_pos = (horizontal_padding, top_padding)

    return {
        "host_size": (sprite_width + (horizontal_padding * 2), sprite_height + top_padding),
        "sprite_pos": sprite_pos,
        "heart_pos": (sprite_pos[0] + heart_x, sprite_pos[1] + heart_y),
    }


def collect_default_heart_offset() -> tuple[int, int]:
    max_heart_offset = (0, 0)
    for phase in build_default_script():
        if phase.effect_name == "heart":
            max_heart_offset = (
                max(max_heart_offset[0], phase.effect_dx),
                min(max_heart_offset[1], phase.effect_dy),
            )
    return max_heart_offset


def build_default_window_layout(
    *,
    screen_size: tuple[int, int],
    image_size: tuple[int, int],
    display_ratio: float,
    margin_px: int,
    anchor: str,
    heart_size: tuple[int, int] = HEART_SIZE,
    effect_offset: tuple[int, int] | None = None,
) -> dict[str, tuple[int, int] | dict[str, tuple[int, int]] | int]:
    screen_width, screen_height = screen_size
    image_width, image_height = image_size
    target_height = compute_target_height(screen_height, display_ratio)
    scale = target_height / image_height
    target_width = max(1, round(image_width * scale))
    host_layout = build_sprite_host_layout(
        sprite_size=(target_width, target_height),
        heart_size=heart_size,
        effect_offset=collect_default_heart_offset() if effect_offset is None else effect_offset,
    )
    position = compute_initial_position(
        screen_width,
        screen_height,
        pet_width=host_layout["host_size"][0],
        pet_height=host_layout["host_size"][1],
        margin_px=margin_px,
        anchor=anchor,
    )
    return {
        "target_height": target_height,
        "target_size": (target_width, target_height),
        "host_layout": host_layout,
        "position": position,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the girlfriend desktop pet")
    parser.add_argument("--manifest", type=Path, default=Path("assets/manifest.json"))
    parser.add_argument("--dry-run", action="store_true")
    return parser


def build_status_summary(config, *, position: tuple[int, int], target_height: int) -> str:
    return (
        f"png={config.png_name} pos={position[0]},{position[1]} "
        f"target_height={target_height} motions={','.join(config.motions)}"
    )


def format_elapsed_seconds(total_seconds: int) -> str:
    if not math.isfinite(total_seconds):
        total_seconds = 0
    total_seconds = max(0, int(total_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def build_info_lines(
    *,
    name: str,
    session_minutes: int,
    total_minutes: int,
    show_session_time: bool,
    show_total_time: bool,
) -> list[str]:
    lines = [name]
    if show_session_time:
        lines.append(build_companion_time_label(session_minutes))
    if show_total_time:
        lines.append(build_total_companion_label(total_minutes))
    return lines


def build_status_lines(*, affection: int, sleepiness: float) -> list[str]:
    value = max(0, min(100, round(sleepiness * 100)))
    return [f"亲密度：{affection}", f"困倦值：{value}%"]


def build_menu_labels() -> list[str]:
    return [
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
    ]


def clamp_scale(value: float) -> float:
    return min(1.6, max(0.6, value))


def build_single_motion_script(label: str):
    script = build_default_script()
    if label.lower() == "jump":
        return [phase for phase in script if phase.name in {"jump-up", "jump-down"}]
    if label.lower() == "sway":
        return [phase for phase in script if phase.name in {"sway-out", "sway-back"}]
    mapping = {phase.name.lower(): phase for phase in script}
    return [mapping[label.lower()]]


def build_info_font_point_size(scale_factor: float) -> int:
    clamped = clamp_scale(scale_factor)
    return max(8, min(16, round(10 * clamped)))


def build_persisted_state_payload(
    *,
    affection: int,
    total_companion_seconds: int,
    auto_sleep_enabled: bool,
    show_session_time: bool,
    show_total_time: bool,
) -> dict[str, object]:
    return {
        "affection": affection,
        "total_companion_seconds": total_companion_seconds,
        "auto_sleep_enabled": auto_sleep_enabled,
        "show_session_time": show_session_time,
        "show_total_time": show_total_time,
    }


def dispatch_menu_action(
    *,
    label: str,
    script,
    phase_index: int,
    elapsed_ms: int,
    pet_name: str,
    show_session_time: bool,
    show_total_time: bool,
    auto_sleep_enabled: bool,
    scale_factor: float,
    affection: int,
) -> dict[str, object]:
    result = {
        "script": script,
        "phase_index": phase_index,
        "elapsed_ms": elapsed_ms,
        "pet_name": pet_name,
        "show_session_time": show_session_time,
        "show_total_time": show_total_time,
        "auto_sleep_enabled": auto_sleep_enabled,
        "scale_factor": scale_factor,
        "affection": affection,
        "request_layout": False,
        "reset_position": False,
        "should_close": False,
        "prompt_name": False,
    }

    if label == "摸摸头":
        result["affection"] = affection + 1
        result["request_layout"] = True
    elif label == "开启/关闭自动睡觉":
        result["auto_sleep_enabled"] = not auto_sleep_enabled
        result["request_layout"] = True
    elif label in {"显示/隐藏陪伴时间", "显示/隐藏本次陪伴时间"}:
        result["show_session_time"] = not show_session_time
        result["request_layout"] = True
    elif label == "显示/隐藏累计陪伴时间":
        result["show_total_time"] = not show_total_time
        result["request_layout"] = True
    elif label == "自动循环":
        result["script"] = build_default_script()
        result["phase_index"] = 0
        result["elapsed_ms"] = 0
    elif label in {"Idle", "Jump", "Sway", "Kiss"}:
        result["script"] = build_single_motion_script(label)
        result["phase_index"] = 0
        result["elapsed_ms"] = 0
    elif label == "缩放大一点":
        result["scale_factor"] = clamp_scale(scale_factor + 0.1)
        result["request_layout"] = True
    elif label == "缩放小一点":
        result["scale_factor"] = clamp_scale(scale_factor - 0.1)
        result["request_layout"] = True
    elif label == "重置位置":
        result["reset_position"] = True
    elif label == "修改名字":
        result["prompt_name"] = True
    elif label == "退出":
        result["should_close"] = True

    return result


def build_tick_snapshot(
    *,
    script,
    phase_index: int,
    elapsed_ms: int,
    anchor_pos: tuple[int, int],
    name: str,
    affection: int,
    sleepiness: float,
    is_sleeping: bool,
    auto_sleep_enabled: bool,
    sleep_elapsed_minutes: int,
    session_minutes: int,
    total_minutes: int,
    show_session_time: bool,
    show_total_time: bool,
    delta_minutes: int,
) -> dict[str, object]:
    is_showing_sleep_prompt = not is_sleeping and sleep_elapsed_minutes > 0

    if is_showing_sleep_prompt:
        next_prompt_elapsed = sleep_elapsed_minutes + TICK_MS
        if auto_sleep_enabled and next_prompt_elapsed >= SLEEP_PROMPT_MS:
            sleep_state = {
                "sleepiness": max(float(sleepiness), 1.0),
                "is_sleeping": True,
                "sleep_elapsed_minutes": 0,
                "should_warn": False,
            }
        else:
            sleep_state = {
                "sleepiness": sleepiness,
                "is_sleeping": False,
                "sleep_elapsed_minutes": next_prompt_elapsed,
                "should_warn": True,
            }
    else:
        sleep_state = evolve_sleep_cycle(
            sleepiness=sleepiness,
            is_sleeping=is_sleeping,
            auto_sleep_enabled=auto_sleep_enabled,
            sleep_elapsed_minutes=sleep_elapsed_minutes,
            delta_minutes=delta_minutes,
        )
        if sleep_state["should_warn"] and not is_sleeping and sleep_elapsed_minutes == 0:
            sleep_state["is_sleeping"] = False
            sleep_state["sleep_elapsed_minutes"] = TICK_MS

    if sleep_state["is_sleeping"]:
        return {
            "position": anchor_pos,
            "phase_index": phase_index,
            "elapsed_ms": elapsed_ms,
            "info_lines": build_info_lines(
                name=name,
                session_minutes=session_minutes,
                total_minutes=total_minutes,
                show_session_time=show_session_time,
                show_total_time=show_total_time,
            ),
            "status_lines": build_status_lines(affection=affection, sleepiness=sleep_state["sleepiness"]),
            "effect": None,
            "show_heart": False,
            "prompt_text": build_sleep_prompt_text() if sleep_state["should_warn"] else "",
            "should_hide_window": True,
            "sleepiness": sleep_state["sleepiness"],
            "is_sleeping": True,
            "sleep_elapsed_minutes": sleep_state["sleep_elapsed_minutes"],
        }

    position, next_phase_index, next_elapsed_ms = advance_animation(
        script,
        phase_index=phase_index,
        elapsed_ms=elapsed_ms,
        anchor_pos=anchor_pos,
    )
    phase = script[next_phase_index - 1] if next_elapsed_ms == 0 else script[next_phase_index]
    _dx, _dy, _rotation, _scale, effect = sample_phase(
        phase,
        elapsed_ms=max(TICK_MS, next_elapsed_ms or phase.duration_ms),
    )
    return {
        "position": position,
        "phase_index": next_phase_index,
        "elapsed_ms": next_elapsed_ms,
        "info_lines": build_info_lines(
            name=name,
            session_minutes=session_minutes,
            total_minutes=total_minutes,
            show_session_time=show_session_time,
            show_total_time=show_total_time,
        ),
        "status_lines": build_status_lines(affection=affection, sleepiness=sleep_state["sleepiness"]),
        "effect": effect,
        "show_heart": bool(effect and effect.name == "heart"),
        "prompt_text": build_sleep_prompt_text() if sleep_state["should_warn"] else "",
        "should_hide_window": False,
        "sleepiness": sleep_state["sleepiness"],
        "is_sleeping": False,
        "sleep_elapsed_minutes": sleep_state["sleep_elapsed_minutes"],
    }


def advance_animation(
    script,
    *,
    phase_index: int,
    elapsed_ms: int,
    anchor_pos: tuple[int, int],
    step_ms: int = TICK_MS,
) -> tuple[tuple[int, int], int, int]:
    phase = script[phase_index]
    next_elapsed_ms = elapsed_ms + step_ms
    while next_elapsed_ms > phase.duration_ms:
        next_elapsed_ms -= phase.duration_ms
        phase_index = (phase_index + 1) % len(script)
        phase = script[phase_index]

    if next_elapsed_ms == phase.duration_ms:
        dx, dy, _rotation, _scale, _effect = sample_phase(phase, elapsed_ms=phase.duration_ms)
        position = (anchor_pos[0] + dx, anchor_pos[1] + dy)
        phase_index = (phase_index + 1) % len(script)
        next_elapsed_ms = 0
    else:
        dx, dy, _rotation, _scale, _effect = sample_phase(phase, elapsed_ms=next_elapsed_ms)
        position = (anchor_pos[0] + dx, anchor_pos[1] + dy)

    return position, phase_index, next_elapsed_ms


def simulate_script_cycles(script, *, start_pos: tuple[int, int], cycles: int) -> list[tuple[int, int]]:
    positions: list[tuple[int, int]] = []
    phase_index = 0
    elapsed_ms = 0
    position = start_pos

    while len(positions) < cycles:
        position, phase_index, elapsed_ms = advance_animation(
            script,
            phase_index=phase_index,
            elapsed_ms=elapsed_ms,
            anchor_pos=start_pos,
        )
        if phase_index == 0 and elapsed_ms == 0:
            positions.append(position)

    return positions


def main() -> int:
    args = build_parser().parse_args()
    manifest_path = args.manifest
    if not manifest_path.exists():
        raise SystemExit(f"Missing manifest: {manifest_path}")

    config = load_manifest(manifest_path)
    if not config.png_path.exists():
        raise SystemExit(f"Missing PNG asset: {config.png_path}")

    with Image.open(config.png_path) as image:
        image = image.copy()

    script = build_default_script()
    state_path = Path.home() / ".girlfriend-terminal-pet" / "state.json"
    persisted_state = load_pet_state(state_path)

    if args.dry_run:
        default_layout = build_default_window_layout(
            screen_size=(1920, 1080),
            image_size=(image.width, image.height),
            display_ratio=config.display_ratio,
            margin_px=config.margin_px,
            anchor=config.anchor,
        )
        print(
            build_status_summary(
                config,
                position=default_layout["position"],
                target_height=default_layout["target_height"],
            )
        )
        return 0

    import time

    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
    from PyQt5.QtWidgets import QApplication, QInputDialog, QLabel, QMenu, QVBoxLayout, QWidget

    class HeartOverlay(QLabel):
        def __init__(self, parent: QWidget) -> None:
            super().__init__(parent)
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.hide()

        def set_heart(self, visible: bool) -> None:
            self.setVisible(visible)
            if visible:
                self.resize(*HEART_SIZE)
                self.update()

        def paintEvent(self, event) -> None:
            _ = event
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            path = QPainterPath()
            path.moveTo(18, 28)
            path.cubicTo(4, 18, 2, 8, 10, 6)
            path.cubicTo(14, 5, 17, 7, 18, 10)
            path.cubicTo(19, 7, 22, 5, 26, 6)
            path.cubicTo(34, 8, 32, 18, 18, 28)

            painter.setPen(QPen(QColor(255, 255, 255, 180), 1.4))
            painter.setBrush(QColor(255, 102, 160))
            painter.drawPath(path)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 190, 220, 180))
            painter.drawEllipse(12, 8, 5, 4)

    class PetWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            self.setAttribute(Qt.WA_TranslucentBackground, True)

            self._pet_name = "pet"
            self._affection = int(persisted_state["affection"])
            self._sleepiness = 0.0
            self._is_sleeping = False
            self._sleep_elapsed_minutes = 0
            self._auto_sleep_enabled = bool(persisted_state["auto_sleep_enabled"])
            self._show_session_time = bool(persisted_state["show_session_time"])
            self._show_total_time = bool(persisted_state["show_total_time"])
            self._total_companion_seconds = int(persisted_state["total_companion_seconds"])
            self._last_tick_minutes = 0
            self._persisted_state_cache = build_persisted_state_payload(
                affection=self._affection,
                total_companion_seconds=self._total_companion_seconds,
                auto_sleep_enabled=self._auto_sleep_enabled,
                show_session_time=self._show_session_time,
                show_total_time=self._show_total_time,
            )
            self._scale_factor = 1.0
            self._started_at = time.monotonic()
            self._drag_offset = None
            self._phase_index = 0
            self._elapsed_ms = 0
            self._script = build_default_script()
            self._sprite_origin = (0, 0)

            self._root = QVBoxLayout(self)
            self._root.setContentsMargins(0, 0, 0, 0)
            self._root.setSpacing(6)

            self.sprite_host = QWidget(self)
            self.sprite_host.setAttribute(Qt.WA_TranslucentBackground, True)
            self.sprite_label = QLabel(self.sprite_host)
            self.heart_label = HeartOverlay(self.sprite_host)
            self.stats_label = QLabel(self.sprite_host)
            self.stats_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            self.stats_label.setStyleSheet(
                "color: white; background: rgba(0, 0, 0, 95); border-radius: 8px; padding: 6px 8px;"
            )
            self.stats_label.setFont(QFont("Microsoft YaHei UI", 8))
            self._root.addWidget(self.sprite_host, alignment=Qt.AlignHCenter)

            self.info_label = QLabel(self)
            self.info_label.setAlignment(Qt.AlignCenter)
            self.info_label.setStyleSheet(
                "color: white; background: rgba(0, 0, 0, 110); border-radius: 10px; padding: 8px 10px;"
            )
            self.info_label.setFont(QFont("Microsoft YaHei UI", 10))
            self._root.addWidget(self.info_label)

            self._base_pixmap = QPixmap(str(config.png_path))
            screen = QApplication.primaryScreen().availableGeometry()
            self._default_layout = build_default_window_layout(
                screen_size=(screen.width(), screen.height()),
                image_size=(self._base_pixmap.width(), self._base_pixmap.height()),
                display_ratio=config.display_ratio,
                margin_px=config.margin_px,
                anchor=config.anchor,
            )
            self._default_pos = self._default_layout["position"]
            self.move(*self._default_pos)
            self._anchor_pos = self.pos()

            self.apply_layout()

            self.timer = QTimer(self)
            self.timer.timeout.connect(self.tick)
            self.timer.start(TICK_MS)

        def apply_layout(self) -> None:
            screen = QApplication.primaryScreen().availableGeometry()
            previous_default_pos = self._default_pos
            should_keep_default_anchor = self.pos() == previous_default_pos
            target_height = round(compute_target_height(screen.height(), config.display_ratio) * self._scale_factor)
            scaled = self._base_pixmap.scaledToHeight(target_height, Qt.SmoothTransformation)
            layout = build_sprite_host_layout(
                sprite_size=(scaled.width(), scaled.height()),
                heart_size=HEART_SIZE,
                effect_offset=collect_default_heart_offset(),
            )
            self.sprite_label.setPixmap(scaled)
            self._sprite_origin = layout["sprite_pos"]
            self.sprite_label.move(*self._sprite_origin)
            self.sprite_label.resize(scaled.size())
            self.sprite_host.setFixedSize(*layout["host_size"])
            self.info_label.setFont(QFont("Microsoft YaHei UI", build_info_font_point_size(self._scale_factor)))
            self.info_label.setText(
                "\n".join(
                    build_info_lines(
                        name=self._pet_name,
                        session_minutes=self._last_tick_minutes,
                        total_minutes=self._total_companion_seconds // 60,
                        show_session_time=self._show_session_time,
                        show_total_time=self._show_total_time,
                    )
                )
            )
            self.stats_label.setText("\n".join(build_status_lines(affection=self._affection, sleepiness=self._sleepiness)))
            self.stats_label.adjustSize()
            self.stats_label.move(8, 8)
            self.adjustSize()
            self._default_pos = compute_initial_position(
                screen.width(),
                screen.height(),
                pet_width=layout["host_size"][0],
                pet_height=self.height(),
                margin_px=config.margin_px,
                anchor=config.anchor,
            )
            if should_keep_default_anchor:
                self.move(*self._default_pos)
                self._anchor_pos = self.pos()

        def persist_state_if_changed(self) -> None:
            payload = build_persisted_state_payload(
                affection=self._affection,
                total_companion_seconds=self._total_companion_seconds,
                auto_sleep_enabled=self._auto_sleep_enabled,
                show_session_time=self._show_session_time,
                show_total_time=self._show_total_time,
            )
            if payload == self._persisted_state_cache:
                return
            save_pet_state(state_path, payload)
            self._persisted_state_cache = payload

        def contextMenuEvent(self, event) -> None:
            menu = QMenu(self)
            for label in build_menu_labels():
                menu.addAction(label)

            chosen = menu.exec_(event.globalPos())
            if chosen is None:
                return

            label = chosen.text()
            update = dispatch_menu_action(
                label=label,
                script=self._script,
                phase_index=self._phase_index,
                elapsed_ms=self._elapsed_ms,
                pet_name=self._pet_name,
                show_session_time=self._show_session_time,
                show_total_time=self._show_total_time,
                auto_sleep_enabled=self._auto_sleep_enabled,
                scale_factor=self._scale_factor,
                affection=self._affection,
            )
            self._script = update["script"]
            self._phase_index = update["phase_index"]
            self._elapsed_ms = update["elapsed_ms"]
            self._show_session_time = update["show_session_time"]
            self._show_total_time = update["show_total_time"]
            self._auto_sleep_enabled = update["auto_sleep_enabled"]
            self._scale_factor = update["scale_factor"]
            self._affection = update["affection"]
            self.persist_state_if_changed()

            if update["reset_position"]:
                self.move(*self._default_pos)
                self._anchor_pos = self.pos()
            elif update["prompt_name"]:
                value, accepted = QInputDialog.getText(self, "修改名字", "桌宠名字：", text=self._pet_name)
                if accepted and value.strip():
                    self._pet_name = value.strip()
                    self.apply_layout()
            elif update["request_layout"]:
                self.apply_layout()
            elif update["should_close"]:
                self.close()

        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
                self._anchor_pos = self.pos()

        def mouseMoveEvent(self, event):
            if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
                self.move(event.globalPos() - self._drag_offset)
                self._anchor_pos = self.pos()

        def mouseReleaseEvent(self, event):
            self._drag_offset = None
            self._anchor_pos = self.pos()

        def tick(self):
            session_minutes = int((time.monotonic() - self._started_at) / 60)
            delta_minutes = max(0, session_minutes - self._last_tick_minutes)
            if not self._is_sleeping:
                self._total_companion_seconds += delta_minutes * 60
            snapshot = build_tick_snapshot(
                script=self._script,
                phase_index=self._phase_index,
                elapsed_ms=self._elapsed_ms,
                anchor_pos=(self._anchor_pos.x(), self._anchor_pos.y()),
                name=self._pet_name,
                affection=self._affection,
                sleepiness=self._sleepiness,
                is_sleeping=self._is_sleeping,
                auto_sleep_enabled=self._auto_sleep_enabled,
                sleep_elapsed_minutes=self._sleep_elapsed_minutes,
                session_minutes=session_minutes,
                total_minutes=self._total_companion_seconds // 60,
                show_session_time=self._show_session_time,
                show_total_time=self._show_total_time,
                delta_minutes=delta_minutes,
            )
            self._last_tick_minutes = session_minutes
            self._phase_index = snapshot["phase_index"]
            self._elapsed_ms = snapshot["elapsed_ms"]
            self._sleepiness = snapshot["sleepiness"]
            self._is_sleeping = snapshot["is_sleeping"]
            self._sleep_elapsed_minutes = snapshot["sleep_elapsed_minutes"]

            self.move(*snapshot["position"])
            self.stats_label.setText("\n".join(snapshot["status_lines"]))
            self.info_label.setText("\n".join(snapshot["info_lines"]))
            if snapshot["prompt_text"]:
                self.info_label.setText(snapshot["prompt_text"])
            self.setVisible(not snapshot["should_hide_window"])
            self.persist_state_if_changed()

            effect = snapshot["effect"]
            if snapshot["show_heart"] and effect is not None:
                self.heart_label.move(
                    self._sprite_origin[0] + self.sprite_label.width() - 20 + effect.offset[0],
                    self._sprite_origin[1] + 12 + effect.offset[1],
                )
                self.heart_label.set_heart(True)
            else:
                self.heart_label.set_heart(False)

    app = QApplication(sys.argv)
    window = PetWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
