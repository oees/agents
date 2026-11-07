"""Write a render to disk, owning only what the lock says oees-agents wrote.

`.oees-agents.lock` records, for every owned file, the sha256 of the bytes
written, and for every managed block the sha256 of the block itself. A file
or block whose bytes no longer match the lock was changed by someone else:
it is listed as a conflict and left alone unless `force` is set. Files the
lock owns that the new render no longer produces are removed, so disabling
a kit cleans up after it. Symlinks and malformed markers are never forced.
"""

import hashlib
import logging
import os
import tempfile
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import tomli_w

from oees_agents.blocks import BlockError, extract, remove, size_warning, splice
from oees_agents.output import ManagedBlock, Output

LOCK_NAME = ".oees-agents.lock"
LOCK_VERSION = 1

logger = logging.getLogger(__name__)


class WriterError(ValueError):
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
    for path in output.paths:
        _check_inside(path)
    builder = _Builder(root, lock, force)
    for path, data in output.files.items():
        builder.file(path, data)
    for path, block in output.blocks.items():
        builder.block(path, block)
    for path in sorted(set(lock.files) - output.paths):
        builder.drop_file(path)
    for path in sorted(set(lock.blocks) - output.paths):
        builder.drop_block(path)
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
    write_lock(root, pending.lock)


def sync(root: Path, output: Output, force: bool = False) -> Plan:
    pending = plan(root, output, read_lock(root), force)
    apply(root, pending)
    return pending


class _Builder:
    def __init__(self, root: Path, lock: Lock, force: bool) -> None:
        self.root, self.lock, self.force = root, lock, force
        self.writes: dict[str, bytes] = {}
        self.unblocked: dict[str, bytes] = {}
        self.deletes: list[str] = []
        self.conflicts: list[Conflict] = []
        self.unchanged: list[str] = []
        self.warnings: list[str] = []
        self.files: dict[str, str] = {}
        self.blocks: dict[str, str] = {}

    def file(self, path: str, data: bytes) -> None:
        current = self._read(path)
        if isinstance(current, _Unsafe):
            self._keep(path, self.lock.files, self.files)
            return
        locked = self.lock.files.get(path)
        if current == data:
            self.unchanged.append(path)
        elif current is None or digest(current) == locked or self.force:
            self.writes[path] = data
        else:
            self._conflict(path, locked, self.lock.files, self.files)
            return
        self.files[path] = digest(data)

    def block(self, path: str, block: ManagedBlock) -> None:
        current = self._read(path)
        if isinstance(current, _Unsafe):
            self._keep(path, self.lock.blocks, self.blocks)
            return
        try:
            data = splice(current, block)
            old_block = extract(current) if current is not None else None
        except BlockError as error:
            self.conflicts.append(Conflict(path, str(error)))
            self._keep(path, self.lock.blocks, self.blocks)
            return
        warning = size_warning(path, data, block)
        if warning:
            self.warnings.append(warning)
        locked = self.lock.blocks.get(path)
        if current == data:
            self.unchanged.append(path)
        elif old_block is None or locked is None or digest(old_block) == locked or self.force:
            self.writes[path] = data
        else:
            self._conflict(path, locked, self.lock.blocks, self.blocks, inside_block=True)
            return
        new_block = extract(data)
        assert new_block is not None  # splice always leaves exactly one block
        self.blocks[path] = digest(new_block)

    def drop_file(self, path: str) -> None:
        current = self._read(path)
        if isinstance(current, _Unsafe):
            self._keep(path, self.lock.files, self.files)
        elif current is None:
            return
        elif digest(current) == self.lock.files[path] or self.force:
            self.deletes.append(path)
        else:
            self._conflict(path, self.lock.files[path], self.lock.files, self.files)

    def drop_block(self, path: str) -> None:
        current = self._read(path)
        if isinstance(current, _Unsafe):
            self._keep(path, self.lock.blocks, self.blocks)
            return
        try:
            old_block = extract(current) if current is not None else None
        except BlockError as error:
            self.conflicts.append(Conflict(path, str(error)))
            self._keep(path, self.lock.blocks, self.blocks)
            return
        if current is None or old_block is None:
            return
        if digest(old_block) == self.lock.blocks[path] or self.force:
            self.unblocked[path] = remove(current)
        else:
            self._conflict(
                path, self.lock.blocks[path], self.lock.blocks, self.blocks, inside_block=True
            )

    def build(self) -> Plan:
        return Plan(
            writes=dict(sorted(self.writes.items())),
            deletes=tuple(sorted(self.deletes)),
            unblocks=dict(sorted(self.unblocked.items())),
            conflicts=tuple(sorted(self.conflicts, key=lambda conflict: conflict.path)),
            unchanged=tuple(sorted(self.unchanged)),
            warnings=tuple(self.warnings),
            lock=Lock(
                files=dict(sorted(self.files.items())), blocks=dict(sorted(self.blocks.items()))
            ),
        )

    def _read(self, path: str) -> "bytes | _Unsafe | None":
        target = self.root / path
        for parent in [*reversed(PurePosixPath(path).parents)][1:]:
            if (self.root / parent).is_symlink():
                self.conflicts.append(
                    Conflict(path, f"{parent} is a symlink; refusing to follow it")
                )
                return _UNSAFE
        if target.is_symlink() or (target.exists() and not target.is_file()):
            self.conflicts.append(Conflict(path, "is a symlink or not a regular file; refusing it"))
            return _UNSAFE
        return target.read_bytes() if target.exists() else None

    def _conflict(
        self,
        path: str,
        locked: str | None,
        previous: Mapping[str, str],
        kept: dict[str, str],
        inside_block: bool = False,
    ) -> None:
        if locked is None:
            reason = "exists and was not written by oees-agents; use --force to replace it"
        elif inside_block:
            reason = "managed block modified since oees-agents wrote it; use --force to replace it"
        else:
            reason = "modified since oees-agents wrote it; use --force to replace it"
        self.conflicts.append(Conflict(path, reason))
        self._keep(path, previous, kept)

    @staticmethod
    def _keep(path: str, previous: Mapping[str, str], kept: dict[str, str]) -> None:
        if path in previous:
            kept[path] = previous[path]


class _Unsafe:
    pass


_UNSAFE = _Unsafe()


def _check_inside(path: str) -> None:
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise WriterError(f"refusing to write outside the project: {path}")


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
