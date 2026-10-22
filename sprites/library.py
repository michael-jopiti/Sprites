"""On-disk library layout: library/<project>/<collection>/<character>.json."""
from pathlib import Path

LIBRARY = Path(__file__).resolve().parent.parent / "library"


def valid(name: str) -> bool:
    """Return True if `name` is safe to use as a file or folder name."""
    return bool(name) and not any(c in name for c in "/\\:") and not name.startswith(".")


def depth(path: Path, library: Path = LIBRARY) -> int:
    """Return how deep `path` sits in the library: 1 project, 2 collection, 3 character."""
    return len(Path(path).relative_to(library).parts)
