"""Detect and migrate a project installed by the old `scripts/init-repo.sh`.

A file is removed only when its bytes match a version this repository once
shipped at that path (`legacy_hashes.json`, generated from the git history by
`scripts/generate_legacy_hashes.py`). Legacy-looking files the project edited
are kept and listed; everything else is never looked at. Symlinks are never
followed, read through or deleted.
"""

import hashlib
import json
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Literal

from oees_agents.blocks import BEGIN
from oees_agents.content import Content
from oees_agents.manifest import MANIFEST_NAME, TARGETS, Extras, Manifest, Target
from oees_agents.writer import remove_file, write_atomic

logger = logging.getLogger(__name__)

OLD_RULE_DEFAULTS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "tdd": ("tdd",),
        "git": ("git",),
        "observability": ("observability",),
        "migrations": ("migrations",),
        "standards": ("standards", "api"),
        "code-quality": ("quality-gates",),
        "secrets": (),
        "no-inline-imports": (),
        "conduct": (),
        "data-protection": (),
        "api": ("api",),
        "quality-gates": ("quality-gates",),
    }
)

KNOWN_HASHES: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        path: frozenset(hashes)
        for path, hashes in json.loads(
            files("oees_agents").joinpath("legacy_hashes.json").read_text(encoding="utf-8")
        ).items()
    }
)

CLAUDE_MD = ".claude/CLAUDE.md"
SETTINGS_JSON = ".claude/settings.json"
AGENTS_MD = "AGENTS.md"
_IMPORT = re.compile(rb"@rules/([a-z0-9-]+)\.md")
_SOURCE = re.compile(
    rb"<!-- Source: (?:rules|content/conduct|content/defaults)/([a-z0-9-]+)\.md -->"
)
_CANDIDATES = tuple(
    sorted({*KNOWN_HASHES, *(f".claude/rules/{name}.md" for name in OLD_RULE_DEFAULTS)})
)

Kind = Literal["missing", "file", "unsafe"]


class LegacyError(ValueError):
    """A legacy install cannot be migrated safely; nothing was changed."""


@dataclass(frozen=True)
class LegacyInstall:
    targets: tuple[Target, ...]
    defaults: tuple[str, ...]
    loops: tuple[str, ...]
    commands: bool
    removable: tuple[str, ...]
    kept: tuple[str, ...]
    claude_md: bytes | None


def detect(root: Path, content: Content) -> LegacyInstall | None:
    """What the old installer left in `root`, or None if it left nothing; never writes."""
    root = root.resolve()
    if (root / MANIFEST_NAME).exists():
        return None
    found = {path: kind for path in _CANDIDATES if (kind := _kind(root, path)) != "missing"}
    removable = tuple(path for path, kind in found.items() if _is_known(root, path, kind))
    present = tuple(path for path in found if path in removable or path != SETTINGS_JSON)
    claude_md, imported = _strip_imports(_read(root, CLAUDE_MD))
    agents_md = _read(root, AGENTS_MD)
    rules = {
        *imported,
        *(Path(path).stem for path in present if path.startswith(".claude/rules/")),
        *(match.decode() for match in _SOURCE.findall(agents_md or b"")),
    }
    has = {
        "claude": bool(imported) or any(path.startswith(".claude/") for path in present),
        "cursor": any(path.startswith(".cursor/rules/") for path in present),
        "codex": agents_md is not None and _has_marker(agents_md),
    }
    targets = tuple(target for target in TARGETS if has[target])
    if not targets:
        return None
    implied = {default for rule in rules for default in OLD_RULE_DEFAULTS.get(rule, ())}
    return LegacyInstall(
        targets=targets,
        defaults=tuple(name for name in content.defaults if name in implied),
        loops=tuple(name for name in content.loops if f".claude/loops/{name}.md" in present),
        commands=any(path.startswith(".claude/commands/") for path in present),
        removable=removable,
        kept=tuple(path for path in present if path not in removable),
        claude_md=claude_md if imported else None,
    )


def migrate(root: Path, install: LegacyInstall) -> None:
    """Delete `install.removable` and rewrite CLAUDE.md; checks everything before changing any."""
    root = root.resolve()
    for path in install.removable:
        kind = _kind(root, path) if path in KNOWN_HASHES else "unsafe"
        if not _is_known(root, path, kind):
            raise LegacyError(f"{path} is not an unedited legacy file any more; nothing removed")
    if install.claude_md is not None and _kind(root, CLAUDE_MD) == "unsafe":
        raise LegacyError(f"{CLAUDE_MD} is a symlink or not a regular file; nothing removed")
    for path in install.removable:
        remove_file(root, path)
        logger.info("removed legacy file", extra={"path": path})
    if install.claude_md is not None and install.claude_md.strip():
        write_atomic(root / CLAUDE_MD, install.claude_md)
        logger.info("removed legacy rule imports", extra={"path": CLAUDE_MD})
    elif install.claude_md is not None:
        remove_file(root, CLAUDE_MD)
        logger.info("removed legacy file", extra={"path": CLAUDE_MD})
    for path in install.kept:
        logger.warning(
            "kept legacy file",
            extra={"path": path, "reason": "not an unedited copy of a version oees-agents shipped"},
        )


def legacy_manifest(install: LegacyInstall, source: str) -> Manifest:
    return Manifest(
        source=source,
        targets=install.targets,
        project=None,
        defaults=install.defaults,
        extras=Extras(commands=install.commands, subagents="none", loops=install.loops),
    )


def _kind(root: Path, path: str) -> Kind:
    parents = [*PurePosixPath(path).parents][:-1]
    if any((root / parent).is_symlink() for parent in parents) or (root / path).is_symlink():
        return "unsafe"
    if not (root / path).exists():
        return "missing"
    return "file" if (root / path).is_file() else "unsafe"


def _is_known(root: Path, path: str, kind: Kind) -> bool:
    if kind != "file":
        return False
    return hashlib.sha256((root / path).read_bytes()).hexdigest() in KNOWN_HASHES.get(path, ())


def _read(root: Path, path: str) -> bytes | None:
    return (root / path).read_bytes() if _kind(root, path) == "file" else None


def _strip_imports(data: bytes | None) -> tuple[bytes, set[str]]:
    kept: list[bytes] = []
    imported: set[str] = set()
    for line in (data or b"").splitlines(keepends=True):
        match = _IMPORT.fullmatch(line.strip())
        if match and match[1].decode() in OLD_RULE_DEFAULTS:
            imported.add(match[1].decode())
        else:
            kept.append(line)
    return b"".join(kept), imported


def _has_marker(data: bytes) -> bool:
    return any(line.strip() == BEGIN.encode() for line in data.splitlines())
