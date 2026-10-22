"""Export a sprite grid as SVG, PNG or GIF."""
import tkinter as tk
from pathlib import Path

from .model import Grid


def to_svg(grid: Grid, n: int) -> str:
    """Return the grid as an SVG string, one 1×1 rect per painted pixel."""
    rects = "".join(f'<rect x="{x}" y="{y}" width="1" height="1" fill="{c}"/>'
                    for y, r in enumerate(grid) for x, c in enumerate(r) if c)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" width="{n * 16}" height="{n * 16}" '
            f'shape-rendering="crispEdges">{rects}</svg>')


def write(path: str, grid: Grid, n: int, scale: int) -> None:
    """Write the grid to `path`; the extension (svg, gif, else png) picks the format.

    `scale` zooms raster output by a whole factor. SVG is vector and ignores it.
    """
    fmt = Path(path).suffix.lower().lstrip(".")
    if fmt == "svg":
        Path(path).write_text(to_svg(grid, n))
        return
    img = tk.PhotoImage(width=n, height=n)
    for y in range(n):
        for x in range(n):
            if c := grid[y][x]:
                img.put(c, (x, y))
            else:
                img.transparency_set(x, y, True)
    if scale > 1:
        img = img.zoom(scale)
    img.write(path, format="gif" if fmt == "gif" else "png")
