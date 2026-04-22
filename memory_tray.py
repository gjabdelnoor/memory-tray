#!/usr/bin/env python3
"""Memory Tray Monitor — shows live RAM usage in the system tray."""

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
BG_COLOR = (30, 30, 30)
TEXT_COLOR = (255, 255, 255)
COLORS = {
    "green": (50, 205, 50),
    "yellow": (255, 215, 0),
    "red": (255, 69, 58),
}

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
    """Render a small tray icon with the percentage and a status dot."""
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), BG_COLOR)
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
    draw.text((text_x, text_y), text, fill=TEXT_COLOR, font=font)

    # Status dot on the right edge, vertically centered
    dot_radius = 5
    dot_x = ICON_SIZE - dot_radius - 4
    dot_y = ICON_SIZE // 2
    draw.ellipse(
        [dot_x - dot_radius, dot_y - dot_radius,
         dot_x + dot_radius, dot_y + dot_radius],
        fill=get_color(percent)
    )

    return img


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
            self._icon.title = f"RAM: {percent:.1f}% used ({mem.used // (1024**2)} MB / {mem.total // (1024**2)} MB)"

    def _loop(self):
        while self._running:
            try:
                self._update()
            except Exception as e:
                print(f"Update error: {e}", file=sys.stderr)
            time.sleep(UPDATE_INTERVAL)

    def _on_refresh(self, icon, item):
        self._update()

    def _on_exit(self, icon, item):
        self._running = False
        icon.stop()

    def run(self):
        initial_percent = psutil.virtual_memory().percent
        menu = pystray.Menu(
            pystray.MenuItem("Refresh", self._on_refresh),
            pystray.MenuItem("Quit", self._on_exit),
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
