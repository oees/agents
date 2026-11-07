"""A content tree in the target layout of the restructure plan, for tests that must
not depend on the real content while it is being reorganised."""

from pathlib import Path

import pytest

CONDUCT = ("conduct", "data-protection", "secrets")
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
LOOPS = ("tier-0-daily-health-scan", "tier-1-increase-test-coverage")


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
    for name in LOOPS:
        write(root / "content/loops" / f"{name}.md", f"# {name}\n\n## Steps\n\nDo it.\n")
    return root


@pytest.fixture
def content_root(tmp_path: Path) -> Path:
    return build_content_tree(tmp_path / "agents")
