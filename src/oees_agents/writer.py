"""Write a render to disk, owning only what the lock says oees-agents wrote.

`.oees-agents.lock` records, for every owned file, the sha256 of the bytes
written, and for every managed block the sha256 of the block itself. A file
or block whose bytes no longer match the lock was changed by someone else:
it is listed as a conflict and left alone unless `force` is set. Files the
lock owns that the new render no longer produces are removed, so disabling
a kit cleans up after it. Symlinks and malformed markers are never forced.

An optional file (Claude Code's settings.json) is written only where the
project has no file of its own. A project's own file there is listed in
`own`, never a conflict, so `check` passes; `force` replaces it.
"""

import hashlib
import logging
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import partial
from pathlib import Path, PurePosixPath
from typing import Literal

import tomli_w

from oees_agents.blocks import BlockError, extract, remove, size_warning, splice
from oees_agents.errors import OeesAgentsError
from oees_agents.fs import remove_file, write_atomic
from oees_agents.output import ManagedBlock, Output

LOCK_NAME = ".oees-agents.lock"
LOCK_VERSION = 1

logger = logging.getLogger(__name__)


class WriterError(OeesAgentsError):
    """The render or the lock cannot be applied at all."""


@dataclass(frozen=True)
class Lock:
    files: Mapping[str, str]
    blocks: Mapping[str, str]


@dataclass(frozen=True)
class Conflict:
    path: str
    reason: str


@dataclass(frozen=True)
class Plan:
    writes: Mapping[str, bytes]
    deletes: tuple[str, ...]
    unblocks: Mapping[str, bytes]
    conflicts: tuple[Conflict, ...]
    unchanged: tuple[str, ...]
    warnings: tuple[str, ...]
    lock: Lock
    own: tuple[str, ...] = ()
    """Optional paths where the project keeps a file of its own."""

    @property
    def is_clean(self) -> bool:
        return not (self.writes or self.deletes or self.unblocks or self.conflicts)


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def read_lock(root: Path) -> Lock | None:
    path = root / LOCK_NAME
    if not path.exists():
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise WriterError(f"{LOCK_NAME} is not valid TOML: {error}") from error
    if data.get("version") != LOCK_VERSION or set(data) - {"version", "files", "blocks"}:
        raise WriterError(f"{LOCK_NAME} has an unsupported version or unknown keys")
    files, blocks = data.get("files", {}), data.get("blocks", {})
    for table in (files, blocks):
        if not isinstance(table, dict) or not all(isinstance(v, str) for v in table.values()):
            raise WriterError(f"{LOCK_NAME} maps paths to anything but hashes")
        for locked_path in table:
            _check_inside(locked_path)
    return Lock(files=files, blocks=blocks)


def write_lock(root: Path, lock: Lock) -> None:
    data = {
        "version": LOCK_VERSION,
        "files": dict(sorted(lock.files.items())),
        "blocks": dict(sorted(lock.blocks.items())),
    }
    write_atomic(root / LOCK_NAME, tomli_w.dumps(data).encode("utf-8"))


def plan(root: Path, output: Output, lock: Lock | None, force: bool = False) -> Plan:
    root = root.resolve()
    lock = lock or Lock(files={}, blocks={})
    # The lock is committed, so its paths are as untrusted as the render's.
    for path in {*output.paths, *lock.files, *lock.blocks}:
        _check_inside(path)
    builder = _Builder(root, lock, force)
    for path, data in output.files.items():
        optional = path in output.optional
        builder.attempt("files", path, partial(builder.file, path, data, optional))
    for path, block in output.blocks.items():
        builder.attempt("blocks", path, partial(builder.block, path, block))
    for path in sorted(set(lock.files) - output.paths):
        builder.attempt("files", path, partial(builder.drop_file, path))
    for path in sorted(set(lock.blocks) - output.paths):
        builder.attempt("blocks", path, partial(builder.drop_block, path))
    return builder.build()


def apply(root: Path, pending: Plan) -> None:
    root = root.resolve()
    for path, data in pending.writes.items():
        write_atomic(root / path, data)
        logger.info("wrote file", extra={"path": path, "bytes": len(data)})
    for path, data in pending.unblocks.items():
        if data:
            write_atomic(root / path, data)
        else:
            remove_file(root, path)
        logger.info("removed managed block", extra={"path": path})
    for path in pending.deletes:
        remove_file(root, path)
        logger.info("removed file", extra={"path": path})
    for conflict in pending.conflicts:
        logger.warning(
            "left file untouched", extra={"path": conflict.path, "reason": conflict.reason}
        )
    for path in pending.own:
        logger.info("kept the project's own file", extra={"path": path})
    write_lock(root, pending.lock)


def sync(root: Path, output: Output, force: bool = False) -> Plan:
    pending = plan(root, output, read_lock(root), force)
    apply(root, pending)
    return pending


class _Refused(Exception):
    """A path the builder leaves alone; the message is the reason the user sees."""


Table = Literal["files", "blocks"]


class _Builder:
    def __init__(self, root: Path, lock: Lock, force: bool) -> None:
        self.root, self.lock, self.force = root, lock, force
        self.writes: dict[str, bytes] = {}
        self.unblocked: dict[str, bytes] = {}
        self.deletes: list[str] = []
        self.conflicts: list[Conflict] = []
        self.unchanged: list[str] = []
        self.own: list[str] = []
        self.warnings: list[str] = []
        self.locked: dict[Table, dict[str, str]] = {"files": {}, "blocks": {}}

    def attempt(self, table: Table, path: str, action: Callable[[], None]) -> None:
        """Run one step for `path`; on refusal, record why and keep its lock entry."""
        try:
            action()
        except (_Refused, BlockError) as refused:
            self.conflicts.append(Conflict(path, str(refused)))
            previous = getattr(self.lock, table)
            if path in previous:
                self.locked[table][path] = previous[path]

    def file(self, path: str, data: bytes, optional: bool) -> None:
        current = self._read(path)
        locked = self.lock.files.get(path)
        same = current is not None and _same(current, data)
        if optional and current is not None and not same and locked is None and not self.force:
            self.own.append(path)
            return
        if same:
            self.unchanged.append(path)
        elif current is None or _matches(current, locked) or self.force:
            self.writes[path] = data
        else:
            raise _Refused(_edited(locked, "file"))
        self.locked["files"][path] = digest(data)

    def block(self, path: str, block: ManagedBlock) -> None:
        current = self._read(path)
        data = splice(current, block)
        old_block = extract(current) if current is not None else None
        locked = self.lock.blocks.get(path)
        if current == data:
            self.unchanged.append(path)
        elif old_block is None or locked is None or _matches(old_block, locked) or self.force:
            self.writes[path] = data
        else:
            raise _Refused(_edited(locked, "managed block"))
        warning = size_warning(path, data, block)
        if warning:
            self.warnings.append(warning)
        new_block = extract(data)
        assert new_block is not None  # splice always leaves exactly one block
        self.locked["blocks"][path] = digest(_lf(new_block))

    def drop_file(self, path: str) -> None:
        current = self._read(path)
        if current is None:
            return
        if not (_matches(current, self.lock.files[path]) or self.force):
            raise _Refused(_edited(self.lock.files[path], "file"))
        self.deletes.append(path)

    def drop_block(self, path: str) -> None:
        current = self._read(path)
        old_block = extract(current) if current is not None else None
        if current is None or old_block is None:
            return
        if not (_matches(old_block, self.lock.blocks[path]) or self.force):
            raise _Refused(_edited(self.lock.blocks[path], "managed block"))
        self.unblocked[path] = remove(current)

    def build(self) -> Plan:
        return Plan(
            writes=dict(sorted(self.writes.items())),
            deletes=tuple(sorted(self.deletes)),
            unblocks=dict(sorted(self.unblocked.items())),
            conflicts=tuple(sorted(self.conflicts, key=lambda conflict: conflict.path)),
            unchanged=tuple(sorted(self.unchanged)),
            warnings=tuple(self.warnings),
            own=tuple(sorted(self.own)),
            lock=Lock(
                files=dict(sorted(self.locked["files"].items())),
                blocks=dict(sorted(self.locked["blocks"].items())),
            ),
        )

    def _read(self, path: str) -> bytes | None:
        """The bytes at `path`, None if it is absent; refuses anything but a regular file."""
        target = self.root / path
        for parent in [*reversed(PurePosixPath(path).parents)][1:]:
            if (self.root / parent).is_symlink():
                raise _Refused(f"{parent} is a symlink; refusing to follow it")
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise _Refused("is a symlink or not a regular file; refusing it")
        return target.read_bytes() if target.exists() else None


def _edited(locked: str | None, what: str) -> str:
    if locked is None:
        return "exists and was not written by oees-agents; use --force to replace it"
    if what == "file":
        return "modified since oees-agents wrote it; use --force to replace it"
    return f"{what} modified since oees-agents wrote it; use --force to replace it"


def _same(current: bytes, data: bytes) -> bool:
    """Equal, or equal once Git on Windows (core.autocrlf) has turned LF into CRLF."""
    return current == data or _lf(current) == data


def _matches(current: bytes, locked: str | None) -> bool:
    return locked in (digest(current), digest(_lf(current)))


def _lf(data: bytes) -> bytes:
    """Git on Windows may check text out with CRLF; that is not an edit."""
    return data.replace(b"\r\n", b"\n")


def _check_inside(path: str) -> None:
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise WriterError(f"refusing to write outside the project: {path}")
