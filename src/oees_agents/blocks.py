"""Splice a managed block into a file the project also edits.

Everything outside the markers belongs to the project and is kept byte for
byte. Files with an unclosed, orphaned, duplicated or reversed marker are
refused rather than guessed at, and so are symlinks and non-files.
"""

from pathlib import Path

from oees_agents.output import ManagedBlock

BEGIN = "<!-- BEGIN OEES SHARED RULES -->"
END = "<!-- END OEES SHARED RULES -->"


class BlockError(ValueError):
    """A file cannot safely receive the managed block."""


def read_target(path: Path) -> bytes | None:
    if path.is_symlink():
        raise BlockError(f"refusing to replace a symlink: {path}")
    if not path.exists():
        return None
    if not path.is_file():
        raise BlockError(f"refusing to replace something that is not a regular file: {path}")
    return path.read_bytes()


def merge(path: Path, block: ManagedBlock) -> tuple[bytes, list[str]]:
    """The bytes `path` should hold with `block` in place; never writes."""
    data = splice(read_target(path), block)
    warning = size_warning(path.name, data, block)
    return data, [warning] if warning else []


def size_warning(name: str, data: bytes, block: ManagedBlock) -> str | None:
    if block.max_bytes is None or len(data) <= block.max_bytes:
        return None
    return f"{name} is {len(data)} bytes, over the {block.max_bytes}-byte limit"


def splice(existing: bytes | None, block: ManagedBlock) -> bytes:
    existing = existing or b""
    newline = b"\r\n" if b"\r\n" in existing else b"\n"
    rendered = _render(block.body, newline)
    span = _find(existing)
    if span is not None:
        start, end = span
        return existing[:start] + rendered + existing[end:]
    if not existing:
        return rendered
    if block.placement == "top":
        return rendered + newline + existing
    separator = b"" if existing.endswith(b"\n") else newline
    return existing + separator + newline + rendered


def extract(data: bytes) -> bytes | None:
    span = _find(data)
    return None if span is None else data[span[0] : span[1]]


def remove(data: bytes) -> bytes:
    span = _find(data)
    if span is None:
        return data
    newline = b"\r\n" if b"\r\n" in data else b"\n"
    before, after = data[: span[0]], data[span[1] :]
    if not before and after.startswith(newline):
        after = after[len(newline) :]
    elif before.endswith(newline * 2):
        before = before[: -len(newline)]
    result = before + after
    return result if result.strip() else b""


def _render(body: str, newline: bytes) -> bytes:
    text = f"{BEGIN}\n\n{body.strip(chr(10))}\n\n{END}\n"
    return text.encode("utf-8").replace(b"\n", newline)


def _find(data: bytes) -> tuple[int, int] | None:
    """Byte span from the start of the BEGIN line to the end of the END line."""
    begins: list[int] = []
    ends: list[int] = []
    offset = 0
    for line in data.splitlines(keepends=True):
        text = line.rstrip(b"\r\n")
        if text == BEGIN.encode():
            begins.append(offset)
        elif text == END.encode():
            ends.append(offset + len(line))
        offset += len(line)
    if not begins and not ends:
        return None
    if len(begins) != 1 or len(ends) != 1 or begins[0] > ends[0]:
        raise BlockError("malformed or multiple shared-rule markers; leaving the file unchanged")
    return begins[0], ends[0]
