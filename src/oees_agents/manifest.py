"""Read, write and validate the committed `.oees-agents.toml` manifest."""

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, TypeVar, cast, get_args

import tomli_w

from oees_agents.errors import OeesAgentsError
from oees_agents.fs import write_atomic

MANIFEST_NAME = ".oees-agents.toml"
MANIFEST_VERSION = 1

Scope = Literal["project", "machine"]
Target = Literal["claude", "cursor", "codex"]
BlastRadius = Literal["internal", "customer-facing", "regulated"]
SubagentTier = Literal["none", "core", "extended"]

SCOPES: tuple[Scope, ...] = get_args(Scope)
NO_MACHINE_CURSOR = "Cursor has no machine-wide rules; install it in each project instead"
TARGETS: tuple[Target, ...] = get_args(Target)
MACHINE_TARGETS: tuple[Target, ...] = ("claude", "codex")
"""Cursor reads rule files only from a project, so a machine install leaves it out."""
BLAST_RADII: tuple[BlastRadius, ...] = get_args(BlastRadius)
SUBAGENT_TIERS: tuple[SubagentTier, ...] = get_args(SubagentTier)
SUBAGENTS_LOADED: dict[SubagentTier, tuple[str, ...]] = {
    "none": (),
    "core": ("core",),
    "extended": ("core", "extended"),
}
"""The content subagent sets each tier loads: a tier includes the ones below it."""


class ManifestError(OeesAgentsError):
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


@dataclass(frozen=True)
class Manifest:
    source: str
    targets: tuple[Target, ...]
    project: Project | None
    defaults: tuple[str, ...]
    kits: tuple[str, ...] = ()
    extras: Extras = field(default_factory=Extras)
    version: int = MANIFEST_VERSION
    scope: Scope = "project"


T = TypeVar("T")
C = TypeVar("C", bound=str)

_TOP_KEYS = {"version", "source", "scope", "targets", "project", "rules", "kits", "extras"}
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

    scope = _choice(_get(data, "scope", str, "", default="project"), SCOPES, "scope")
    targets = _choices(_targets(data), TARGETS, "targets")
    if scope == "machine":
        _check_machine(data, targets)
    rules = _table(data, "rules", {"defaults"})
    kits = _table(data, "kits", {"enabled"})
    extras = _table(data, "extras", {"commands", "subagents"})

    return Manifest(
        version=version,
        source=_get(data, "source", str, ""),
        scope=scope,
        targets=targets,
        project=_project(data["project"]) if "project" in data else None,
        defaults=_unique(_strings(rules, "defaults", "rules."), "rules.defaults"),
        kits=_unique(_strings(kits, "enabled", "kits.", default=()), "kits.enabled"),
        extras=Extras(
            commands=_get(extras, "commands", bool, "extras.", default=True),
            subagents=_choice(
                _get(extras, "subagents", str, "extras.", default="core"),
                SUBAGENT_TIERS,
                "extras.subagents",
            ),
        ),
    )


def dump_manifest(manifest: Manifest) -> str:
    data: dict[str, Any] = {
        "version": manifest.version,
        "source": manifest.source,
    }
    if manifest.scope != "project":
        data["scope"] = manifest.scope
    data["targets"] = list(manifest.targets)
    if manifest.project is not None:
        data["project"] = {key: getattr(manifest.project, key) for key in _PROJECT_KEYS}
    data["rules"] = {"defaults": list(manifest.defaults)}
    data["kits"] = {"enabled": list(manifest.kits)}
    data["extras"] = {
        "commands": manifest.extras.commands,
        "subagents": manifest.extras.subagents,
    }
    return tomli_w.dumps(data)


def read_manifest(path: Path) -> Manifest:
    return parse_manifest(path.read_text(encoding="utf-8"))


def write_manifest(path: Path, manifest: Manifest) -> None:
    write_atomic(path, dump_manifest(manifest).encode("utf-8"))


# A top-level `source` key and its string value; whatever follows (a comment) stays.
_SOURCE_VALUE = re.compile(
    r"""^(source[ \t]*=[ \t]*)(?:"(?:[^"\\\n]|\\.)*"(?!")|'[^'\n]*'(?!'))""", re.MULTILINE
)


def set_source(text: str, source: str) -> str:
    """Change the pinned source without rewriting the rest, so comments survive."""
    value = tomli_w.dumps({"source": source}).strip().removeprefix("source = ")
    updated, count = _SOURCE_VALUE.subn(lambda match: match.group(1) + value, text)
    if count != 1:
        raise ManifestError('source: expected exactly one top-level `source = "..."` line')
    parse_manifest(updated)
    return updated


def _project(value: object) -> Project:
    if not isinstance(value, dict):
        raise ManifestError("project: expected a table")
    _reject_unknown(value, set(_PROJECT_KEYS), "project.")
    fields = {key: _get(value, key, str, "project.") for key in _PROJECT_KEYS}
    if not fields["name"].strip():
        raise ManifestError("project.name: must not be empty")
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


def _check_machine(data: Mapping[str, object], targets: tuple[Target, ...]) -> None:
    if "project" in data:
        raise ManifestError("project: a machine install has no project; remove [project]")
    if "cursor" in targets:
        raise ManifestError(f"targets: {NO_MACHINE_CURSOR}")


def _targets(data: Mapping[str, object]) -> tuple[str, ...]:
    targets = _unique(_strings(data, "targets", ""), "targets")
    if not targets:
        raise ManifestError("targets: list at least one target")
    return targets


def _unique(values: tuple[str, ...], key: str) -> tuple[str, ...]:
    repeated = sorted({value for value in values if values.count(value) > 1})
    if repeated:
        raise ManifestError(f"{key}: {', '.join(repeated)} listed more than once")
    return values


def _choice(value: str, allowed: tuple[C, ...], key: str) -> C:
    if value not in allowed:
        raise ManifestError(f"{key}: expected one of {', '.join(allowed)}, got {value!r}")
    return value


def _choices(values: tuple[str, ...], allowed: tuple[C, ...], key: str) -> tuple[C, ...]:
    return tuple(_choice(value, allowed, key) for value in values)
