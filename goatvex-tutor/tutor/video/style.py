"""GoatVex visual language: one place for colors, sizes and layout.

Every scene template uses these names, so the whole course looks consistent:
pivots are always gold, the row/term being changed is always teal, results
that were just computed glow green, warnings are coral.
"""

from __future__ import annotations

import manimpango
from manim import config

# ---------------------------------------------------------------- colors (3B1B-like dark palette)
BACKGROUND = "#0f1117"
TEXT = "#ece9e1"           # main text / math
MUTED = "#8b8f9a"          # secondary text, unchanged rows
PIVOT = "#f5c542"          # pivots / leading 1s / the "source" of an operation
CHANGE = "#3fc1c9"         # the row, term or entry being changed
RESULT = "#7bd88f"         # freshly computed result, checkmarks
WARNING = "#ff7a6b"        # zero rows, contradictions, "not defined"
ACCENT = "#b392f0"         # geometry: second object (plane 2, vector v …)
ACCENT_2 = "#f78c6c"       # geometry: third object
SERIES = [CHANGE, ACCENT, ACCENT_2, PIVOT]  # colors for equations/lines/planes 1, 2, 3, 4
CAPTION_BG = "#000000"
CAPTION_BG_OPACITY = 0.55

# ---------------------------------------------------------------- sizes
TITLE_SIZE = 40
BODY_SIZE = 30
SMALL_SIZE = 24
CAPTION_SIZE = 24
MATH_SIZE = 44
MATRIX_SIZE = 40
OP_LABEL_SIZE = 40

# ---------------------------------------------------------------- layout (Manim units; frame is 14.22 × 8)
FRAME_W = config.frame_width
FRAME_H = config.frame_height
MARGIN = 0.35
TITLE_Y = 3.45                      # baseline area for titles
CONTENT_TOP = 2.95                  # content must stay below this…
CAPTION_TOP = -2.75                 # …and above this (captions live below)
CAPTION_Y = -3.35
CONTENT_LEFT = -FRAME_W / 2 + MARGIN
CONTENT_RIGHT = FRAME_W / 2 - MARGIN

# ---------------------------------------------------------------- timing
STEP_PAUSE = 0.6                    # quiet beat after each step, so it can sink in
TRANSFORM_TIME = 1.2

_PREFERRED_FONTS = ["Segoe UI", "DejaVu Sans", "Noto Sans", "Helvetica", "Arial"]


def font() -> str:
    """First available font that has Unicode subscripts (R₂ → R₂ − 3R₁) and math symbols."""
    available = set(manimpango.list_fonts())
    for f in _PREFERRED_FONTS:
        if f in available:
            return f
    return ""
