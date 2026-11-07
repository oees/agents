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

KIT_GLOBS: dict[str, tuple[str, ...]] = {
    "django-drf": ("**/*.py",),
    "fastapi": ("**/*.py",),
    "htmx-alpine": ("**/templates/**/*.html",),
}

KIT_TOOLCHAINS: dict[str, tuple[Toolchain, ...]] = {
    "django-drf": ("python",),
    "fastapi": ("python",),
}

SUBAGENT_ONLY_SKILLS = frozenset({"reviewing"})
