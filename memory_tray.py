#!/usr/bin/env python3
"""Memory Tray Monitor — shows live RAM usage in the system tray."""

import os
import subprocess
import sys

import psutil
from PIL import Image, ImageDraw, ImageFont
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon, QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
UPDATE_INTERVAL = 2000  # milliseconds
ICON_SIZE = 64
TEXT_COLOR = (255, 255, 255)
COLORS = {
    "green": (50, 205, 50),
    "yellow": (255, 215, 0),
    "red": (255, 69, 58),
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AUTOSTART_FILE = os.path.expanduser("~/.config/autostart/memory-tray.desktop")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_color(percent: float):
    if percent < 80:
        return COLORS["green"]
    elif percent < 92:
        return COLORS["yellow"]
    else:
        return COLORS["red"]


def create_icon(percent: float) -> Image.Image:
    """Render a small tray icon with the percentage on a colored background."""
    bg = get_color(percent)
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), bg)
    draw = ImageDraw.Draw(img)

    font_size = 20
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

    text = f"{int(percent)}%"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (ICON_SIZE - text_w) // 2
    text_y = (ICON_SIZE - text_h) // 2 - 2

    # subtle dark outline for readability on all colors
    outline_color = (0, 0, 0, 128)
    for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        draw.text((text_x + dx, text_y + dy), text, fill=outline_color, font=font)
    draw.text((text_x, text_y), text, fill=TEXT_COLOR, font=font)

    return img


def pil_to_qicon(img: Image.Image) -> QIcon:
    """Convert a PIL Image to a QIcon."""
    data = img.tobytes("raw", "RGBA")
    qimage = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
    pixmap = QPixmap.fromImage(qimage)
    return QIcon(pixmap)


def enable_autostart():
    os.makedirs(os.path.dirname(AUTOSTART_FILE), exist_ok=True)
    with open(AUTOSTART_FILE, "w") as f:
        f.write(
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Memory Tray\n"
            f"Exec={SCRIPT_DIR}/run.sh\n"
            "Hidden=false\n"
            "NoDisplay=false\n"
            "X-GNOME-Autostart-enabled=true\n"
        )
    os.chmod(AUTOSTART_FILE, 0o755)


def disable_autostart():
    if os.path.exists(AUTOSTART_FILE):
        os.remove(AUTOSTART_FILE)


def autostart_status() -> str:
    return "enabled" if os.path.exists(AUTOSTART_FILE) else "disabled"


# ---------------------------------------------------------------------------
# Tray logic
# ---------------------------------------------------------------------------

class MemoryTray:
    def __init__(self, app: QApplication):
        self.app = app
        self.tray = QSystemTrayIcon()
        self.tray.setToolTip("Memory Tray")

        # Right-click menu
        self.menu = QMenu()
        self.menu.addAction("off", self.on_off)
        self.menu.addAction("autoon", self.on_autoon)
        self.menu.addAction("autooff", self.on_autooff)
        self.menu.addAction("kill", self.on_kill)
        self.tray.setContextMenu(self.menu)

        # Also handle left-click activation (optional)
        self.tray.activated.connect(self.on_activated)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(UPDATE_INTERVAL)

        self.update()
        self.tray.show()

    def update(self):
        mem = psutil.virtual_memory()
        percent = mem.percent
        img = create_icon(percent)
        self.tray.setIcon(pil_to_qicon(img))
        self.tray.setToolTip(
            f"RAM: {percent:.1f}% used\n"
            f"({mem.used // (1024 ** 2)} MB / {mem.total // (1024 ** 2)} MB)\n"
            f"Autostart: {autostart_status()}"
        )

    def on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        # Left click can also trigger an action if desired
        pass

    def on_off(self):
        self.tray.hide()
        self.app.quit()

    def on_autoon(self):
        enable_autostart()
        self.update()

    def on_autooff(self):
        disable_autostart()
        self.update()

    def on_kill(self):
        try:
            subprocess.run(
                ["pkill", "-9", "-f", f"python3 {SCRIPT_DIR}/memory_tray.py"],
                capture_output=True,
            )
        except Exception:
            pass
        self.tray.hide()
        self.app.quit()
        os._exit(1)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("System tray is not available", file=sys.stderr)
        sys.exit(1)

    tray = MemoryTray(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
