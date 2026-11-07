"""What the installer knows about skills and kits beyond their SKILL.md.

A kit or pattern skill missing here still installs; it is just not attached to
file globs in Cursor and adds no tool permissions in Claude Code.
"""

from typing import Literal

Toolchain = Literal["python", "typescript"]

PATTERN_GLOBS: dict[str, tuple[str, ...]] = {
    "python-patterns": ("**/*.py",),
    "typescript-patterns": ("**/*.ts", "**/*.tsx"),
}

# A service kit also covers the container, CI and deploy files its templates ship.
PYTHON_SERVICE_GLOBS = (
    "**/*.py",
    "**/pyproject.toml",
    "**/Makefile",
    "**/Dockerfile",
    "**/compose.yml",
    ".github/workflows/*.yml",
    ".do/app.yaml",
)

KIT_GLOBS: dict[str, tuple[str, ...]] = {
    "django-drf": PYTHON_SERVICE_GLOBS,
    "fastapi": PYTHON_SERVICE_GLOBS,
    "htmx-alpine": ("**/templates/**/*.html", "**/static/css/**/*.css", "**/static/js/**/*.js"),
}

# htmx-alpine sits on Django and runs djLint and its tests through uv.
KIT_TOOLCHAINS: dict[str, tuple[Toolchain, ...]] = {
    "django-drf": ("python",),
    "fastapi": ("python",),
    "htmx-alpine": ("python",),
}

SUBAGENT_ONLY_SKILLS = frozenset({"reviewing"})
