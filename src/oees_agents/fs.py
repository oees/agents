"""Write and remove files under a root, so a failure never leaves half a file."""

import os
import tempfile
from pathlib import Path


def write_atomic(target: Path, data: bytes) -> None:
    """Replace `target` in one step, keeping its permissions."""
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        if target.exists():
            os.chmod(temporary, target.stat().st_mode & 0o777)
        else:
            os.chmod(temporary, 0o644)
        os.replace(temporary, target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def remove_file(root: Path, path: str) -> None:
    """Delete `path` and every directory it leaves empty, up to but not including `root`."""
    target = root / path
    target.unlink(missing_ok=True)
    parent = target.parent
    while parent != root and parent.is_dir() and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent
