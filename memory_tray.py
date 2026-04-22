#!/usr/bin/env python3
"""Memory Tray Monitor — shows live RAM usage in the system tray."""

import os
import subprocess
import sys
import threading
import time

import psutil
from PIL import Image, ImageDraw, ImageFont
import pystray

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
UPDATE_INTERVAL = 2  # seconds
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

    # Try to load a font; fall back to default if unavailable
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
    def __init__(self):
        self._icon = None
        self._running = True
        self._thread = None

    def _update(self):
        mem = psutil.virtual_memory()
        percent = mem.percent
        new_image = create_icon(percent)
        if self._icon:
            self._icon.icon = new_image
            self._icon.title = (
                f"RAM: {percent:.1f}% used "
                f"({mem.used // (1024 ** 2)} MB / {mem.total // (1024 ** 2)} MB)\n"
                f"Autostart: {autostart_status()}"
            )

    def _loop(self):
        while self._running:
            try:
                self._update()
            except Exception as e:
                print(f"Update error: {e}", file=sys.stderr)
            time.sleep(UPDATE_INTERVAL)

    def _on_off(self, icon, item):
        self._running = False
        icon.stop()

    def _on_autoon(self, icon, item):
        enable_autostart()
        self._update()

    def _on_autooff(self, icon, item):
        disable_autostart()
        self._update()

    def _on_kill(self, icon, item):
        # Force kill this process and any sibling python processes for this script
        try:
            subprocess.run(
                ["pkill", "-9", "-f", f"python3 {SCRIPT_DIR}/memory_tray.py"],
                capture_output=True,
            )
        except Exception:
            pass
        self._running = False
        icon.stop()
        os._exit(1)

    def run(self):
        initial_percent = psutil.virtual_memory().percent
        menu = pystray.Menu(
            pystray.MenuItem("off", self._on_off),
            pystray.MenuItem("autoon", self._on_autoon),
            pystray.MenuItem("autooff", self._on_autooff),
            pystray.MenuItem("kill", self._on_kill),
        )
        self._icon = pystray.Icon(
            "memory-tray",
            icon=create_icon(initial_percent),
            title=f"RAM: {initial_percent:.1f}% used",
            menu=menu,
        )
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._icon.run()


if __name__ == "__main__":
    tray = MemoryTray()
    tray.run()
