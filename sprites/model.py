"""Sprite grid logic and persistence. Pure Python, no Tk, so it is testable without a display."""
import json
from pathlib import Path

Grid = list[list[str | None]]  # grid[y][x] is a "#rrggbb" color, or None for a transparent pixel


def blank(n: int) -> Grid:
    """Return an empty n×n grid."""
    return [[None] * n for _ in range(n)]


def resample(g: Grid, new: int) -> Grid:
    """Return the same picture on a finer or coarser grid of size `new`.

    Growing turns every pixel into a k×k block, so the picture is unchanged.
    Shrinking merges each k×k block into one pixel: painted when at least half
    the block is painted, with the block's most common color. Sizes are powers
    of 2, so k is always a whole number.
    """
    m = len(g)
    if new >= m:
        k = new // m
        return [[g[y // k][x // k] for x in range(new)] for y in range(new)]
    k = m // new
    out = []
    for y in range(new):
        row = []
        for x in range(new):
            block = [g[y * k + j][x * k + i] for j in range(k) for i in range(k)]
            painted = [c for c in block if c]
            row.append(max(set(painted), key=painted.count) if len(painted) * 2 >= len(block) else None)
        out.append(row)
    return out


def save(path: Path, n: int, grid: Grid) -> None:
    """Write a character file."""
    path.write_text(json.dumps({"n": n, "grid": grid}))


def load(path: Path) -> tuple[int, Grid]:
    """Read a character file, returning its size and grid."""
    data = json.loads(path.read_text())
    return data["n"], data["grid"]
