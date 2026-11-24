"""Shared fixtures: an isolated home directory and git, and a small content tree."""

import os
import shutil
from pathlib import Path

import pytest

from oees_agents.manifest import Project
from oees_agents.output import Output
from oees_agents.scope import project_layout

REPO = Path(__file__).resolve().parents[1]
IN_PROJECT = project_layout(Path("project"))
"""A project install; target renderers read only its tool directories, not its root."""
CONTEXT_TEMPLATE = "content/blocks/project-context.md"
CONTEXT_BEGIN = "<!-- BEGIN OEES PROJECT CONTEXT -->"
PROJECT = Project(
    name="portal",
    description="B2B multi-tenant platform where partners and vendors sell energy products.",
    users="external partners, vendors, OEES operations",
    blast_radius="customer-facing",
    default_branch="main",
    check="make check",
    check_fast="make check-fast",
)
CONDUCT = ("conduct", "data-protection", "language", "secrets")
DEFAULTS = ("tdd", "git", "observability", "migrations", "api", "standards", "quality-gates")
COMMAND_SKILLS = ("commit", "code-review", "plan", "pr-tidy", "test", "shipped")
PATTERN_SKILLS = ("python-patterns", "typescript-patterns")
SKILLS = (*COMMAND_SKILLS, *PATTERN_SKILLS, "reviewing", "personal-data")
KITS = ("django-drf", "fastapi", "htmx-alpine")
CORE_SUBAGENTS = (
    "test-writer",
    "implementer",
    "simplifier",
    "functional-reviewer",
    "engineering-reviewer",
    "security-reviewer",
)
EXTENDED_SUBAGENTS = (
    "migration-reviewer",
    "infra-implementer",
    "infra-reviewer",
    "ui-reviewer",
    "documentation-writer",
    "docs-verifier",
)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def build_content_tree(root: Path) -> Path:
    for name in CONDUCT:
        write(
            root / "content/conduct" / f"{name}.md",
            f"---\ndescription: {name} conduct\n---\n\n# {name.title()}\n\nAlways {name}.\n",
        )
    for name in DEFAULTS:
        write(
            root / "content/defaults" / f"{name}.md",
            f"---\ndescription: {name} default\n---\n\n# {name.title()}\n\n"
            "Default for OEES projects. A project opts out in its manifest.\n",
        )
    for name in SKILLS:
        write(
            root / "skills" / name / "SKILL.md",
            f"---\nname: {name}\ndescription: Use for {name}: the {name} skill.\n---\n\n"
            f"# {name}\n\nHow to {name}.\n",
        )
    for name in COMMAND_SKILLS:
        write(
            root / "commands" / f"{name}.md",
            f"---\nname: {name}\ndescription: Run {name}.\n---\n\n@../skills/{name}/SKILL.md\n",
        )
    for name in KITS:
        write(
            root / "content/kits" / name / "SKILL.md",
            f"---\nname: {name}\ndescription: The {name} stack kit.\n---\n\n# {name}\n",
        )
        write(root / "content/kits" / name / "templates/Makefile", "check:\n\ttrue\n")
    for tier, names in (("core", CORE_SUBAGENTS), ("extended", EXTENDED_SUBAGENTS)):
        for name in names:
            write(
                root / "content/subagents" / tier / f"{name}.md",
                f'---\nname: {name}\ndescription: "Use for {name}: in a fresh context."\n'
                "tools: Read, Grep, Glob\nmodel: inherit\nskills:\n  - reviewing\n---\n\n"
                f"# {name}\n",
            )
    (root / CONTEXT_TEMPLATE).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / CONTEXT_TEMPLATE, root / CONTEXT_TEMPLATE)
    return root


@pytest.fixture
def content_root(tmp_path: Path) -> Path:
    return build_content_tree(tmp_path / "agents")


@pytest.fixture(autouse=True)
def home(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Give every test its own home directory and a git with no user or system config.

    A machine install writes into the home directory, and the CLI reads it to
    find one; no test may see or change the real one.
    """
    path = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(path))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "test@example.com")
    return path


def under(output: Output, prefix: str) -> set[str]:
    return {path for path in output.paths if path.startswith(prefix)}
