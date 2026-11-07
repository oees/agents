"""Each kit in this repository renders on its own for every target."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from oees_agents.content import Content, load_content, parse_frontmatter
from oees_agents.lint import lint_content
from oees_agents.output import Output
from oees_agents.render import render
from test_render_claude import manifest, settings, under

REPO = Path(__file__).resolve().parents[1]
TARGETS = ("claude", "cursor", "codex")
JUNK = ("__pycache__", ".ruff_cache", ".mypy_cache", ".pytest_cache", ".pyc")


@dataclass(frozen=True)
class Kit:
    name: str
    globs: tuple[str, ...]
    templates: tuple[str, ...]


PYTHON_SERVICE_GLOBS = (
    "**/*.py",
    "**/pyproject.toml",
    "**/Makefile",
    "**/Dockerfile",
    "**/compose.yml",
    ".github/workflows/*.yml",
    ".do/app.yaml",
)
SERVICE_TEMPLATES = (
    "Makefile",
    "Dockerfile",
    "compose.yml",
    "pyproject.toml",
    ".dockerignore",
    ".env.example",
    ".github/workflows/ci.yml",
    ".github/workflows/deploy.yml",
    ".do/app.yaml",
)
KITS = (
    Kit(
        name="django-drf",
        globs=PYTHON_SERVICE_GLOBS,
        templates=(
            *SERVICE_TEMPLATES,
            "static/.gitkeep",
            "config/settings/production.py",
            "apps/core/views.py",
        ),
    ),
    Kit(
        name="fastapi",
        globs=PYTHON_SERVICE_GLOBS,
        templates=(
            *SERVICE_TEMPLATES,
            "alembic.ini",
            "migrations/versions/.gitkeep",
            "app/settings/production.py",
            "app/core/health.py",
        ),
    ),
    Kit(
        name="htmx-alpine",
        globs=("**/templates/**/*.html", "**/static/css/**/*.css", "**/static/js/**/*.js"),
        templates=(
            "templates/base.html",
            "apps/core/htmx.py",
            "config/settings/csp.py",
            "make/htmx-alpine.mk",
            "static/vendor/SHA256SUMS",
            "locale/.gitkeep",
        ),
    ),
)


@pytest.fixture(scope="module")
def content() -> Content:
    return load_content(REPO)


def rendered(content: Content, kit: Kit) -> Output:
    return render(manifest(targets=TARGETS, kits=(kit.name,)), content)


@pytest.mark.parametrize("kit", KITS, ids=lambda kit: kit.name)
def test_the_kit_skill_and_its_templates_land_under_claude_skills(
    content: Content, kit: Kit
) -> None:
    output = rendered(content, kit)
    root = f".claude/skills/{kit.name}"

    assert output.files[f"{root}/SKILL.md"] == content.kits[kit.name].document.raw
    for relative in kit.templates:
        assert f"{root}/templates/{relative}" in output.files, relative
    assert under(output, f"{root}/") == {f"{root}/{path}" for path in content.kits[kit.name].files}
    assert not [path for path in under(output, root) if any(junk in path for junk in JUNK)]


@pytest.mark.parametrize("kit", KITS, ids=lambda kit: kit.name)
def test_the_cursor_rule_for_the_kit_carries_its_globs(content: Content, kit: Kit) -> None:
    rule = rendered(content, kit).files[f".cursor/rules/{kit.name}.mdc"].decode()
    meta, body = parse_frontmatter(rule)

    assert meta["globs"] == kit.globs
    assert meta["alwaysApply"] == "false"
    assert body.lstrip("\n") == content.kits[kit.name].document.body.lstrip("\n")


@pytest.mark.parametrize("kit", KITS, ids=lambda kit: kit.name)
def test_claude_may_run_the_python_toolchain_the_kit_uses(content: Content, kit: Kit) -> None:
    allow = settings(rendered(content, kit))["permissions"]["allow"]

    assert {"Bash(uv*)", "Bash(pytest*)", "Bash(ruff*)", "Bash(mypy*)"} <= set(allow)


@pytest.mark.parametrize("kit", KITS, ids=lambda kit: kit.name)
def test_the_codex_context_names_the_kit(content: Content, kit: Kit) -> None:
    block = rendered(content, kit).blocks["AGENTS.md"].body

    assert f"Stack: {kit.name}." in block


@pytest.mark.parametrize("kit", KITS, ids=lambda kit: kit.name)
def test_the_kit_text_passes_the_content_lint(content: Content, kit: Kit) -> None:
    source = f"content/kits/{kit.name}/"

    assert [str(p) for p in lint_content(content) if p.source.startswith(source)] == []
