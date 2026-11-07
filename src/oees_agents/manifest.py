"""Read, write and validate the committed `.oees-agents.toml` manifest."""

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, TypeVar, cast, get_args

import tomli_w

MANIFEST_NAME = ".oees-agents.toml"
MANIFEST_VERSION = 1

Target = Literal["claude", "cursor", "codex"]
BlastRadius = Literal["internal", "customer-facing", "regulated"]
SubagentTier = Literal["none", "core", "extended"]

TARGETS: tuple[Target, ...] = get_args(Target)
BLAST_RADII: tuple[BlastRadius, ...] = get_args(BlastRadius)
SUBAGENT_TIERS: tuple[SubagentTier, ...] = get_args(SubagentTier)


class ManifestError(ValueError):
    """The manifest is not valid TOML or does not match the schema."""


@dataclass(frozen=True)
class Project:
    name: str
    description: str
    users: str
    blast_radius: BlastRadius
    default_branch: str
    check: str
    check_fast: str


@dataclass(frozen=True)
class Extras:
    commands: bool = True
    subagents: SubagentTier = "core"
    loops: tuple[str, ...] = ()


@dataclass(frozen=True)
class Manifest:
    source: str
    targets: tuple[Target, ...]
    project: Project | None
    defaults: tuple[str, ...]
    kits: tuple[str, ...] = ()
    extras: Extras = field(default_factory=Extras)
    version: int = MANIFEST_VERSION


T = TypeVar("T")
C = TypeVar("C", bound=str)

_TOP_KEYS = {"version", "source", "targets", "project", "rules", "kits", "extras"}
_PROJECT_KEYS = (
    "name",
    "description",
    "users",
    "blast_radius",
    "default_branch",
    "check",
    "check_fast",
)


def parse_manifest(text: str) -> Manifest:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ManifestError(f"manifest is not valid TOML: {error}") from error
    _reject_unknown(data, _TOP_KEYS, "")

    version = _get(data, "version", int, "")
    if version != MANIFEST_VERSION:
        raise ManifestError(f"version: expected {MANIFEST_VERSION}, got {version}")

    rules = _table(data, "rules", {"defaults"})
    kits = _table(data, "kits", {"enabled"})
    extras = _table(data, "extras", {"commands", "subagents", "loops"})

    return Manifest(
        version=version,
        source=_get(data, "source", str, ""),
        targets=_choices(_strings(data, "targets", ""), TARGETS, "targets"),
        project=_project(data["project"]) if "project" in data else None,
        defaults=_strings(rules, "defaults", "rules."),
        kits=_strings(kits, "enabled", "kits.", default=()),
        extras=Extras(
            commands=_get(extras, "commands", bool, "extras.", default=True),
            subagents=_choice(
                _get(extras, "subagents", str, "extras.", default="core"),
                SUBAGENT_TIERS,
                "extras.subagents",
            ),
            loops=_strings(extras, "loops", "extras.", default=()),
        ),
    )


def dump_manifest(manifest: Manifest) -> str:
    data: dict[str, Any] = {
        "version": manifest.version,
        "source": manifest.source,
        "targets": list(manifest.targets),
    }
    if manifest.project is not None:
        data["project"] = {key: getattr(manifest.project, key) for key in _PROJECT_KEYS}
    data["rules"] = {"defaults": list(manifest.defaults)}
    data["kits"] = {"enabled": list(manifest.kits)}
    data["extras"] = {
        "commands": manifest.extras.commands,
        "subagents": manifest.extras.subagents,
        "loops": list(manifest.extras.loops),
    }
    return tomli_w.dumps(data)


def read_manifest(path: Path) -> Manifest:
    return parse_manifest(path.read_text(encoding="utf-8"))


def write_manifest(path: Path, manifest: Manifest) -> None:
    path.write_text(dump_manifest(manifest), encoding="utf-8")


_SOURCE_LINE = re.compile(r'^source = ".*"$', re.MULTILINE)


def set_source(text: str, source: str) -> str:
    """Change the pinned source without rewriting the rest, so comments survive."""
    line = tomli_w.dumps({"source": source}).strip()
    updated, count = _SOURCE_LINE.subn(lambda _: line, text)
    if count != 1:
        raise ManifestError('source: expected exactly one top-level `source = "..."` line')
    parse_manifest(updated)
    return updated


def _project(value: object) -> Project:
    if not isinstance(value, dict):
        raise ManifestError("project: expected a table")
    _reject_unknown(value, set(_PROJECT_KEYS), "project.")
    fields = {key: _get(value, key, str, "project.") for key in _PROJECT_KEYS}
    fields["blast_radius"] = _choice(fields["blast_radius"], BLAST_RADII, "project.blast_radius")
    return Project(**cast(dict[str, Any], fields))


def _table(data: Mapping[str, object], key: str, allowed: set[str]) -> Mapping[str, object]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ManifestError(f"{key}: expected a table")
    _reject_unknown(value, allowed, f"{key}.")
    return cast(Mapping[str, object], value)


def _reject_unknown(data: Mapping[str, object], allowed: set[str], prefix: str) -> None:
    for key in data:
        if key not in allowed:
            raise ManifestError(f"unknown key '{prefix}{key}'")


_MISSING = object()


def _get(
    data: Mapping[str, object], key: str, kind: type[T], prefix: str, default: object = _MISSING
) -> T:
    if key not in data:
        if default is _MISSING:
            raise ManifestError(f"{prefix}{key}: required")
        return cast(T, default)
    value = data[key]
    if type(value) is not kind:
        raise ManifestError(f"{prefix}{key}: expected {kind.__name__}, got {value!r}")
    return value


def _strings(
    data: Mapping[str, object], key: str, prefix: str, default: object = _MISSING
) -> tuple[str, ...]:
    value = _get(data, key, list, prefix, default=default)
    if not all(isinstance(item, str) for item in value):
        raise ManifestError(f"{prefix}{key}: expected a list of strings")
    return tuple(value)


def _choice(value: str, allowed: tuple[C, ...], key: str) -> C:
    if value not in allowed:
        raise ManifestError(f"{key}: expected one of {', '.join(allowed)}, got {value!r}")
    return value


def _choices(values: tuple[str, ...], allowed: tuple[C, ...], key: str) -> tuple[C, ...]:
    return tuple(_choice(value, allowed, key) for value in values)
