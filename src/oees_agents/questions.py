"""The questions `init` asks, each answerable by a flag so it can run unattended."""

import os
import re
import subprocess
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

import questionary
import typer

from oees_agents.manifest import (
    BLAST_RADII,
    SUBAGENT_TIERS,
    TARGETS,
    BlastRadius,
    Extras,
    Project,
    SubagentTier,
    Target,
)

DEFAULT_CHECK = "make check"
DEFAULT_CHECK_FAST = "make check-fast"
_SKIPPED_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".tox", "dist", "build"}
_SCAN_LIMIT = 5_000


class QuestionError(ValueError):
    """An answer or flag value is not one of the allowed choices."""


class Prompter(Protocol):
    def text(self, message: str, default: str) -> str: ...

    def select(self, message: str, choices: Sequence[str], default: str) -> str: ...

    def checkbox(
        self, message: str, choices: Sequence[str], default: Sequence[str]
    ) -> list[str]: ...


@dataclass(frozen=True)
class Flags:
    targets: tuple[str, ...] | None = None
    name: str | None = None
    description: str | None = None
    users: str | None = None
    blast_radius: str | None = None
    default_branch: str | None = None
    check: str | None = None
    check_fast: str | None = None
    kits: tuple[str, ...] | None = None
    no_defaults: tuple[str, ...] | None = None
    subagents: str | None = None
    loops: tuple[str, ...] | None = None
    commands: bool = True


@dataclass(frozen=True)
class Suggestions:
    targets: tuple[Target, ...]
    name: str
    default_branch: str
    kits: tuple[str, ...]


@dataclass(frozen=True)
class Answers:
    targets: tuple[Target, ...]
    project: Project
    defaults: tuple[str, ...]
    kits: tuple[str, ...]
    extras: Extras


def ask(
    flags: Flags,
    suggestions: Suggestions,
    *,
    defaults: Sequence[str],
    kits: Sequence[str],
    loops: Sequence[str],
    prompter: Prompter | None,
) -> Answers:
    """Answer every question from its flag, else the prompter, else its default.

    Without a prompter (`--yes`), the description and users have no sensible
    default and must come from their flags.
    """
    asker = _Asker(prompter)
    targets = asker.many("Targets", TARGETS, flags.targets, suggestions.targets, "target")
    name = asker.text("Project name", flags.name, suggestions.name, "--name")
    description = asker.text("One-paragraph description", flags.description, None, "--description")
    users = asker.text("Who uses it", flags.users, None, "--users")
    blast_radius = asker.one(
        "Blast radius", BLAST_RADII, flags.blast_radius, "internal", "blast radius"
    )
    branch = asker.text(
        "Default branch", flags.default_branch, suggestions.default_branch, "--default-branch"
    )
    check = asker.text("Full check command", flags.check, DEFAULT_CHECK, "--check")
    check_fast = asker.text(
        "Fast check command", flags.check_fast, DEFAULT_CHECK_FAST, "--check-fast"
    )
    chosen_kits = asker.many("Kits", kits, flags.kits, suggestions.kits, "kit")
    if flags.no_defaults is not None:
        _check_known(flags.no_defaults, defaults, "default")
        kept = tuple(name for name in defaults if name not in flags.no_defaults)
    else:
        kept = asker.many("Defaults to keep", defaults, None, defaults, "default")
    subagents = asker.one("Subagents", SUBAGENT_TIERS, flags.subagents, "core", "subagents")
    chosen_loops = asker.many("Loops", loops, flags.loops, (), "loop")
    return Answers(
        targets=cast(tuple[Target, ...], targets),
        project=Project(
            name=name,
            description=description,
            users=users,
            blast_radius=cast(BlastRadius, blast_radius),
            default_branch=branch,
            check=check,
            check_fast=check_fast,
        ),
        defaults=kept,
        kits=chosen_kits,
        extras=Extras(
            commands=flags.commands,
            subagents=cast(SubagentTier, subagents),
            loops=chosen_loops,
        ),
    )


class _Asker:
    def __init__(self, prompter: Prompter | None) -> None:
        self.prompter = prompter

    def text(self, message: str, flag: str | None, default: str | None, option: str) -> str:
        if flag is not None:
            value = flag
        elif self.prompter is not None:
            value = self.prompter.text(message, default or "")
        elif default is not None:
            value = default
        else:
            raise QuestionError(f"{option} is required when running without prompts")
        if not value.strip():
            raise QuestionError(f"{message} cannot be empty ({option})")
        return value.strip()

    def one(
        self, message: str, choices: Sequence[str], flag: str | None, default: str, kind: str
    ) -> str:
        if flag is not None:
            value = flag
        elif self.prompter is not None:
            value = self.prompter.select(message, choices, default)
        else:
            value = default
        if value not in choices:
            raise QuestionError(f"{kind} must be one of {', '.join(choices)}, not {value!r}")
        return value

    def many(
        self,
        message: str,
        choices: Sequence[str],
        flag: tuple[str, ...] | None,
        default: Sequence[str],
        kind: str,
    ) -> tuple[str, ...]:
        if flag is not None:
            values: Sequence[str] = flag
        elif self.prompter is not None:
            values = self.prompter.checkbox(message, choices, default)
        else:
            values = default
        _check_known(values, choices, kind)
        return tuple(dict.fromkeys(values))


def _check_known(values: Sequence[str], choices: Sequence[str], kind: str) -> None:
    for value in values:
        if value not in choices:
            raise QuestionError(
                f"unknown {kind} {value!r}; choose from {', '.join(choices) or 'none'}"
            )


def detect(root: Path, kits: Sequence[str]) -> Suggestions:
    found = tuple(target for target, present in _target_markers(root) if present)
    return Suggestions(
        targets=found or TARGETS,
        name=root.resolve().name,
        default_branch=_default_branch(root),
        kits=tuple(kit for kit in _kit_hints(root) if kit in kits),
    )


def _target_markers(root: Path) -> Iterator[tuple[Target, bool]]:
    yield "claude", (root / ".claude").is_dir() or (root / "CLAUDE.md").is_file()
    yield "cursor", (root / ".cursor").is_dir()
    yield "codex", (root / "AGENTS.md").is_file()


def _default_branch(root: Path) -> str:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "symbolic-ref",
                "--quiet",
                "--short",
                "refs/remotes/origin/HEAD",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "main"
    branch = result.stdout.strip()
    return branch.removeprefix("origin/") if result.returncode == 0 and branch else "main"


def _kit_hints(root: Path) -> list[str]:
    hints: list[str] = []
    files = list(_walk(root))
    if any(path.name == "manage.py" for path in files):
        hints.append("django-drf")
    manifests = [
        p
        for p in files
        if p.name == "pyproject.toml" or re.fullmatch(r"requirements.*\.txt", p.name)
    ]
    if any(re.search(r"\bfastapi\b", _read(path), re.IGNORECASE) for path in manifests):
        hints.append("fastapi")
    templates = [p for p in files if p.suffix == ".html" and "templates" in p.parts]
    if any("hx-" in _read(path) for path in templates):
        hints.append("htmx-alpine")
    return hints


def _walk(root: Path) -> Iterator[Path]:
    seen = 0
    for directory, subdirectories, names in os.walk(root):
        subdirectories[:] = [name for name in subdirectories if name not in _SKIPPED_DIRS]
        for name in names:
            seen += 1
            if seen > _SCAN_LIMIT:
                return
            yield Path(directory) / name


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


class LinePrompter:
    """Plain line prompts, used when stdin is not a terminal (pipes, CI, tests)."""

    def text(self, message: str, default: str) -> str:
        return str(typer.prompt(message, default=default, show_default=bool(default)))

    def select(self, message: str, choices: Sequence[str], default: str) -> str:
        answer = str(typer.prompt(f"{message} ({'/'.join(choices)})", default=default)).strip()
        if answer not in choices:
            raise QuestionError(f"{answer!r} is not one of {', '.join(choices)}")
        return answer

    def checkbox(self, message: str, choices: Sequence[str], default: Sequence[str]) -> list[str]:
        prompt = (
            f"{message} [{', '.join(choices) or 'none available'}] (comma-separated, - for none)"
        )
        answer = str(typer.prompt(prompt, default=", ".join(default) or "-")).strip()
        if answer == "-":
            return []
        values = [value.strip() for value in answer.split(",") if value.strip()]
        _check_known(values, choices, "choice")
        return values


class QuestionaryPrompter:
    """Arrow-key prompts for an interactive terminal."""

    def text(self, message: str, default: str) -> str:
        return _answered(questionary.text(message, default=default).ask())

    def select(self, message: str, choices: Sequence[str], default: str) -> str:
        return _answered(questionary.select(message, choices=list(choices), default=default).ask())

    def checkbox(self, message: str, choices: Sequence[str], default: Sequence[str]) -> list[str]:
        options = [questionary.Choice(choice, checked=choice in default) for choice in choices]
        answer = questionary.checkbox(message, choices=options).ask()
        if answer is None:
            raise typer.Abort
        return [str(value) for value in answer]


def _answered(answer: object) -> str:
    if answer is None:
        raise typer.Abort
    return str(answer)


def default_prompter() -> Prompter:
    return QuestionaryPrompter() if sys.stdin.isatty() else LinePrompter()
