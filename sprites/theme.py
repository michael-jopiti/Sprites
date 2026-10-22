"""Design tokens: palette, grid sizes and fonts.

The UI is ink on paper. Only sprite pixels and the spectrum strip carry color.
"""
from tkinter import font as tkfont
from types import SimpleNamespace

GRID_SIZES = [8, 16, 32, 64]  # powers of 2, so resampling between them is always a whole-number ratio
SCALES = ["1×", "8×", "16×"]  # export zoom factors
COLORS = ["#000000", "#ffffff", "#ff3b30", "#ff9500", "#ffcc00", "#34c759", "#007aff", "#af52de", "#a2845e", "#8e8e93"]
SPECTRUM = ["#2b3cff", "#a64bf4", "#ff4f8b", "#ff9a3c", "#ffd84d"]  # gradient stops of the decorative strip

K, W, BG = "#000000", "#ffffff", "#e8e8e6"  # ink, white (canvas), paper
FONT = "Helvetica Neue"

fonts = SimpleNamespace()  # filled by load_fonts(); a Tk root must exist first


def load_fonts():
    """Create the shared fonts. Call once, after the Tk root exists."""
    fonts.small = tkfont.Font(family=FONT, size=10, weight="bold")
    fonts.body = tkfont.Font(family=FONT, size=13)
    fonts.bold = tkfont.Font(family=FONT, size=13, weight="bold")
    fonts.title = tkfont.Font(family=FONT, size=30, weight="bold")
    fonts.num = tkfont.Font(family=FONT, size=44)
