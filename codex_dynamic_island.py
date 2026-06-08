from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PYQT5_QT_BIN = Path(sys.executable).resolve().parent / "Lib" / "site-packages" / "PyQt5" / "Qt5" / "bin"
if PYQT5_QT_BIN.exists():
    os.add_dll_directory(str(PYQT5_QT_BIN))
    os.environ["PATH"] = f"{PYQT5_QT_BIN}{os.pathsep}{os.environ.get('PATH', '')}"

from PyQt5.QtCore import QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRect, QSize, Qt, QTimer, pyqtProperty
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QPushButton,
    QWidget,
)


APP_DIR = Path(__file__).resolve().parent
STATE_FILE = APP_DIR / "codex_status.json"
CONFIG_FILE = APP_DIR / "dynamic_island_config.json"


@dataclass(frozen=True)
class Theme:
    title: str
    detail: str
    color: str
    panel: str


THEMES = {
    "working": Theme("Codex 正在工作", "正在处理任务", "#ffd166", "rgba(48, 36, 18, 190)"),
    "decision": Theme("需要你决策", "等待确认或补充信息", "#ff4d6d", "rgba(52, 19, 28, 190)"),
    "done": Theme("任务已完成", "可以验收结果", "#51f28b", "rgba(17, 41, 26, 190)"),
    "idle": Theme("Codex 待命", "等待新的任务", "#9aa4b2", "rgba(23, 27, 34, 190)"),
}

DEFAULT_STATE = {"status": "idle", "message": "Codex 待命", "updated_at": 0, "source": "manual"}
DEFAULT_CONFIG = {"topmost": True, "expanded": True, "x": None, "y": None}


class IslandPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._accent = QColor("#9aa4b2")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

    def set_accent(self, color: str) -> None:
        self._accent = QColor(color)
        self.update()

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect().adjusted(0, 0, -1, -1)
        radius = max(24, rect.height() / 2)
        accent = QColor(self._accent)
        accent.setAlpha(26)

        gradient = QRadialGradient(QPointF(rect.width() * 0.18, rect.height() * 0.26), max(rect.width(), rect.height()) * 0.72)
        gradient.setColorAt(0.0, accent)
        gradient.setColorAt(0.32, QColor(18, 21, 25, 250))
        gradient.setColorAt(1.0, QColor(5, 5, 7, 252))

        painter.setPen(QPen(QColor(255, 255, 255, 28), 1))
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, radius, radius)


class StatusLamp(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = QColor("#9aa4b2")
        self._breath = 1.0
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def get_breath(self) -> float:
        return self._breath

    def set_breath(self, value: float) -> None:
        self._breath = max(0.0, min(1.0, float(value)))
        self.update()

    breath = pyqtProperty(float, fget=get_breath, fset=set_breath)

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        size = min(self.width(), self.height())
        outer_rect = QRect(0, 0, size, size).adjusted(1, 1, -1, -1)
        outer_rect.moveCenter(self.rect().center())

        outer = QColor(self._color)
        outer.setAlpha(52 + int(58 * self._breath))
        painter.setPen(Qt.NoPen)
        painter.setBrush(outer)
        painter.drawEllipse(outer_rect)

        inner_size = min(22, max(16, size - 16))
        inner_rect = QRect(0, 0, inner_size, inner_size)
        inner_rect.moveCenter(self.rect().center())
        inner = QColor(self._color)
        inner.setAlpha(235)
        painter.setBrush(inner)
        painter.drawEllipse(inner_rect)

        painter.setPen(QPen(QColor(255, 255, 255, 70), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(inner_rect.adjusted(0, 0, -1, -1))

        highlight_size = 6
        highlight = QRect(inner_rect.left() + 6, inner_rect.top() + 5, highlight_size, highlight_size)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 135))
        painter.drawEllipse(highlight)


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(default)
    return {**default, **value}


def save_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


class DynamicIsland(QWidget):
    EXPANDED_SIZE = QSize(468, 124)
    COMPACT_SIZE = QSize(190, 58)
    WINDOW_PADDING = 3
    SNAP_DISTANCE = 84
    EDGE_GAP = 10

    def __init__(self) -> None:
        super().__init__()
        self.config = load_json(CONFIG_FILE, DEFAULT_CONFIG)
        self.state = load_json(STATE_FILE, DEFAULT_STATE)
        self.status = self.normalize_status(self.state.get("status"))
        self.expanded = bool(self.config["expanded"])
        self.topmost = bool(self.config["topmost"])
        self.drag_offset = QPoint()
        self.animating = False
        self.animation_target_expanded: bool | None = None
        self.animation: QPropertyAnimation | None = None
        self.content_visible_during_animation = True
        self.current_island_size = QSize(self.EXPANDED_SIZE if self.expanded else self.COMPACT_SIZE)

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        self.setWindowFlags(self.build_flags())

        self.root = IslandPanel(self)
        self.root.setObjectName("root")
        self.root.setGraphicsEffect(None)

        self.lamp = StatusLamp(self.root)
        self.lamp.setObjectName("lamp")
        self.breath_animation = QPropertyAnimation(self.lamp, b"breath", self)
        self.breath_animation.setDuration(1300)
        self.breath_animation.setStartValue(0.0)
        self.breath_animation.setEndValue(1.0)
        self.breath_animation.setEasingCurve(QEasingCurve.InOutSine)
        self.breath_animation.setLoopCount(1)
        self.breath_animation.finished.connect(self.reverse_breath)

        self.title_label = QLabel(self.root)
        self.title_label.setObjectName("title")
        self.title_label.setFont(QFont("Microsoft YaHei UI", 15, QFont.DemiBold))
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.message_label = QLabel(self.root)
        self.message_label.setObjectName("message")
        self.message_label.setFont(QFont("Microsoft YaHei UI", 9))
        self.message_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.meta_label = QLabel(self.root)
        self.meta_label.setObjectName("meta")
        self.meta_label.setFont(QFont("Microsoft YaHei UI", 8))
        self.meta_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.compact_label = QLabel(self.root)
        self.compact_label.setObjectName("compact")
        self.compact_label.setFont(QFont("Microsoft YaHei UI", 12, QFont.DemiBold))
        self.compact_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.topmost_button = QPushButton(self.root)
        self.topmost_button.setObjectName("topmostButton")
        self.topmost_button.setCursor(Qt.PointingHandCursor)
        self.topmost_button.clicked.connect(self.toggle_topmost)

        self.close_button = QPushButton("×", self.root)
        self.close_button.setObjectName("closeButton")
        self.close_button.setCursor(Qt.PointingHandCursor)
        self.close_button.clicked.connect(self.close)

        self.resize_to_state(initial=True)
        self.place_initial()
        self.apply_theme()
        self.sync_content()
        QTimer.singleShot(0, self.refresh_styles)
        QTimer.singleShot(80, self.refresh_styles)

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_state)
        self.poll_timer.start(250)

    def build_flags(self) -> Qt.WindowFlags:
        flags = Qt.FramelessWindowHint
        if self.topmost:
            flags |= Qt.WindowStaysOnTopHint
        return flags

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        QTimer.singleShot(0, self.refresh_styles)

    def resize_to_state(self, initial: bool = False) -> None:
        self.setFixedSize(self.padded_window_size(self.EXPANDED_SIZE))
        self.current_island_size = QSize(self.EXPANDED_SIZE if self.expanded else self.COMPACT_SIZE)
        self.root.setGeometry(self.root_rect_for_size(self.current_island_size))
        self.layout_children()
        self.apply_theme()
        if not initial:
            self.update()

    def place_initial(self) -> None:
        x = self.config.get("x")
        y = self.config.get("y")
        screen = QApplication.primaryScreen().availableGeometry()
        if not isinstance(x, int) or not isinstance(y, int):
            x = screen.x() + (screen.width() - self.EXPANDED_SIZE.width()) // 2
            y = screen.y() + 18
        self.move(x - self.root.x(), y - self.root.y())

    def normalize_status(self, value: Any) -> str:
        value = str(value or "idle")
        return value if value in THEMES else "idle"

    def poll_state(self) -> None:
        new_state = load_json(STATE_FILE, DEFAULT_STATE)
        new_status = self.normalize_status(new_state.get("status"))
        if new_state != self.state or new_status != self.status:
            self.state = new_state
            self.status = new_status
            self.apply_theme()
            self.sync_content()
            self.update_breathing()
            self.update()
        else:
            self.meta_label.setText(self.meta_text())

    def apply_theme(self) -> None:
        theme = THEMES[self.status]
        self.root.set_accent(theme.color)
        self.lamp.set_color(theme.color)
        self.root.setStyleSheet(
            f"""
            QFrame#root {{
                background: transparent;
                border: none;
            }}
            QLabel#title {{
                color: #f7f8fb;
                background: transparent;
            }}
            QLabel#message {{
                color: #b0b6c2;
                background: transparent;
            }}
            QLabel#meta {{
                color: #697180;
                background: transparent;
            }}
            QLabel#compact {{
                color: #f7f8fb;
                background: transparent;
            }}
            QPushButton#topmostButton {{
                color: {theme.color};
                background-color: {theme.panel};
                border: 1px solid rgba(255, 255, 255, 24);
                border-radius: 14px;
                font: 600 8pt "Microsoft YaHei UI";
            }}
            QPushButton#topmostButton:hover {{
                border: 1px solid rgba(255, 255, 255, 55);
            }}
            QPushButton#closeButton {{
                color: #858b96;
                background: transparent;
                border: none;
                font: 700 14pt "Segoe UI";
            }}
            QPushButton#closeButton:hover {{
                color: #fda4af;
            }}
            """
        )

    def sync_content(self) -> None:
        theme = THEMES[self.status]
        message = str(self.state.get("message") or theme.detail)
        if len(message) > 32:
            message = message[:31] + "..."

        self.title_label.setText(theme.title)
        self.message_label.setText(message)
        self.meta_label.setText(self.meta_text())
        self.compact_label.setText({"working": "工作中", "decision": "等待", "done": "完成", "idle": "待命"}.get(self.status, "待命"))
        self.topmost_button.setText("置顶" if self.topmost else "普通")
        self.layout_children()
        self.refresh_styles()
        self.update_breathing()

    def update_breathing(self) -> None:
        should_breathe = self.status in {"working", "decision"}
        if should_breathe and self.breath_animation.state() != QPropertyAnimation.Running:
            self.breath_animation.setDirection(QPropertyAnimation.Forward)
            self.breath_animation.start()
        elif not should_breathe:
            if self.breath_animation.state() == QPropertyAnimation.Running:
                self.breath_animation.stop()
            self.lamp.set_breath(1.0)

    def reverse_breath(self) -> None:
        if self.status not in {"working", "decision"}:
            self.lamp.set_breath(1.0)
            return
        direction = self.breath_animation.direction()
        next_direction = QPropertyAnimation.Backward if direction == QPropertyAnimation.Forward else QPropertyAnimation.Forward
        self.breath_animation.setDirection(next_direction)
        self.breath_animation.start()

    def refresh_styles(self) -> None:
        self.title_label.setStyleSheet("color: #f7f8fb; background: transparent;")
        self.message_label.setStyleSheet("color: #b0b6c2; background: transparent;")
        self.meta_label.setStyleSheet("color: #697180; background: transparent;")
        self.compact_label.setStyleSheet("color: #f7f8fb; background: transparent;")
        self.close_button.setStyleSheet("color: #858b96; background: transparent; border: none;")
        for widget in (
            self.title_label,
            self.message_label,
            self.meta_label,
            self.compact_label,
            self.topmost_button,
            self.close_button,
        ):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def layout_children(self) -> None:
        w = self.root.width()
        h = self.root.height()
        center_y = h // 2
        display_expanded = self.expanded
        show_content = not (self.animating and not self.content_visible_during_animation)
        if not show_content:
            self.title_label.hide()
            self.message_label.hide()
            self.meta_label.hide()
            self.compact_label.hide()
            self.topmost_button.hide()
            self.close_button.hide()
        if display_expanded:
            lamp_wrap_size = 48
            lamp_x = 30
            lamp_y = center_y - lamp_wrap_size // 2

            text_x = 92
            title_h = 32
            message_h = 24
            meta_h = 22
            text_gap = 0
            text_group_h = title_h + message_h + meta_h + text_gap * 2
            text_top = center_y - text_group_h // 2 + 2

            self.lamp.setGeometry(lamp_x, lamp_y, lamp_wrap_size, lamp_wrap_size)
            self.title_label.setGeometry(text_x, text_top, 270, title_h)
            self.message_label.setGeometry(text_x, text_top + title_h + text_gap, 270, message_h)
            self.meta_label.setGeometry(text_x, text_top + title_h + message_h + text_gap * 2, 325, meta_h)
            self.topmost_button.setGeometry(w - 102, center_y - 30, 58, 28)
            self.close_button.setGeometry(w - 82, center_y + 14, 34, 28)
            self.lamp.show()
            self.title_label.setVisible(show_content)
            self.message_label.setVisible(show_content)
            self.meta_label.setVisible(show_content)
            self.topmost_button.setVisible(show_content)
            self.close_button.setVisible(show_content)
            self.compact_label.hide()
        else:
            lamp_wrap_size = 38
            lamp_x = 19
            lamp_y = center_y - lamp_wrap_size // 2

            self.lamp.setGeometry(lamp_x, lamp_y, lamp_wrap_size, lamp_wrap_size)
            self.compact_label.setGeometry(68, 0, w - 82, h)
            self.lamp.show()
            self.compact_label.setVisible(show_content)
            self.title_label.hide()
            self.message_label.hide()
            self.meta_label.hide()
            self.topmost_button.hide()
            self.close_button.hide()

    def layout_animation_frame(self) -> None:
        h = self.root.height()
        center_y = h // 2
        if self.expanded:
            lamp_size = 48
            lamp_x = 30
        else:
            lamp_size = 38
            lamp_x = 19
        self.lamp.setGeometry(lamp_x, center_y - lamp_size // 2, lamp_size, lamp_size)
        self.lamp.show()

    def root_rect_for_size(self, size: QSize) -> QRect:
        return QRect(
            self.WINDOW_PADDING + (self.EXPANDED_SIZE.width() - size.width()) // 2,
            self.WINDOW_PADDING,
            size.width(),
            size.height(),
        )

    def padded_window_size(self, size: QSize) -> QSize:
        padding = self.WINDOW_PADDING * 2
        return QSize(size.width() + padding, size.height() + padding)

    def meta_text(self) -> str:
        source = str(self.state.get("source") or "manual")
        return f"{source} · {self.relative_time()} · 双击折叠 · 右键置顶"

    def relative_time(self) -> str:
        updated_at = self.state.get("updated_at")
        if not isinstance(updated_at, int) or updated_at <= 0:
            return "未更新"
        seconds = max(0, int(time.time()) - updated_at)
        if seconds < 60:
            return f"{seconds}秒前"
        if seconds < 3600:
            return f"{seconds // 60}分钟前"
        return f"{seconds // 3600}小时前"

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self.toggle_topmost()
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self.drag_offset)
            event.accept()

    def mouseReleaseEvent(self, _event) -> None:  # type: ignore[override]
        self.snap_to_edge()

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.toggle_expanded()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_T:
            self.toggle_topmost()

    def toggle_expanded(self) -> None:
        if self.animating:
            return
        self.animation_target_expanded = not self.expanded
        self.expanded = self.animation_target_expanded
        self.config["expanded"] = self.expanded
        save_json(CONFIG_FILE, self.config)

        self.animating = True
        self.content_visible_during_animation = False
        self.layout_children()

        start = self.root.geometry()
        size = self.EXPANDED_SIZE if self.expanded else self.COMPACT_SIZE
        target = self.root_rect_for_size(size)

        self.animation = QPropertyAnimation(self.root, b"geometry", self)
        self.animation.setDuration(260)
        self.animation.setStartValue(start)
        self.animation.setEndValue(target)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.valueChanged.connect(lambda _value: self.layout_animation_frame())
        self.animation.finished.connect(lambda: self.finish_expanded_animation(target))
        self.animation.start(QPropertyAnimation.DeleteWhenStopped)

    def finish_expanded_animation(self, target: QRect) -> None:
        self.root.setGeometry(target)
        self.current_island_size = target.size()
        self.animating = False
        self.animation_target_expanded = None
        self.animation = None
        self.content_visible_during_animation = True
        self.apply_theme()
        self.sync_content()
        self.save_position()

    def toggle_topmost(self) -> None:
        self.topmost = not self.topmost
        self.config["topmost"] = self.topmost
        save_json(CONFIG_FILE, self.config)
        pos = self.pos()
        self.setWindowFlags(self.build_flags())
        self.move(pos)
        self.show()
        self.sync_content()

    def snap_to_edge(self) -> None:
        screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        g = self.visible_geometry()
        gap = self.EDGE_GAP
        options = [
            (abs(g.left() - area.left()), area.left() + gap, g.y()),
            (abs(area.right() - g.right()), area.right() - g.width() - gap + 1, g.y()),
            (abs(g.top() - area.top()), g.x(), area.top() + gap),
            (abs(area.bottom() - g.bottom()), g.x(), area.bottom() - g.height() - gap + 1),
        ]
        distance, x, y = min(options, key=lambda item: item[0])
        if distance > self.SNAP_DISTANCE:
            x = max(area.left() + gap, min(g.x(), area.right() - g.width() - gap + 1))
            y = max(area.top() + gap, min(g.y(), area.bottom() - g.height() - gap + 1))
        target = QPoint(x - self.root.x(), y - self.root.y())
        animation = QPropertyAnimation(self, b"pos", self)
        animation.setDuration(170)
        animation.setStartValue(self.pos())
        animation.setEndValue(target)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.finished.connect(self.save_position)
        animation.start(QPropertyAnimation.DeleteWhenStopped)

    def visible_geometry(self) -> QRect:
        root = self.root.geometry()
        return QRect(self.x() + root.x(), self.y() + root.y(), root.width(), root.height())

    def save_position(self) -> None:
        visible = self.visible_geometry()
        self.config["x"] = visible.x()
        self.config["y"] = visible.y()
        save_json(CONFIG_FILE, self.config)


def main() -> int:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    window = DynamicIsland()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
