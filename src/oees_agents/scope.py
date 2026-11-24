"""Where a project install and a machine install keep their files.

A project install writes into the project root. A machine install writes into
the home directory, where each tool reads its user-level configuration:
`~/.claude/` for Claude Code and `~/.codex/` for Codex. Each tool's own
variable (`CLAUDE_CONFIG_DIR`, `CODEX_HOME`) moves that directory, and the
install follows it, but only to a place inside the home directory.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from oees_agents.manifest import Scope
from oees_agents.output import RenderError


@dataclass(frozen=True)
class Layout:
    """One install's root and each tool's directory in it, resolved once."""

    scope: Scope
    root: Path
    """Holds the manifest and the lock; every generated path is relative to it."""
    claude: str
    codex: str

    @property
    def update_command(self) -> str:
        """The command that regenerates this install, as generated text names it."""
        return "oees-agents update --machine" if self.scope == "machine" else "oees-agents update"


def project_layout(root: Path) -> Layout:
    return Layout("project", root, claude=".claude", codex=".codex")


def machine_layout() -> Layout:
    home = Path.home()
    return Layout(
        "machine",
        home,
        claude=_in_home(home, "CLAUDE_CONFIG_DIR", ".claude"),
        codex=_in_home(home, "CODEX_HOME", ".codex"),
    )


def layout(scope: Scope, project: Path) -> Layout:
    return machine_layout() if scope == "machine" else project_layout(project)


def _in_home(home: Path, variable: str, default: str) -> str:
    value = os.environ.get(variable)
    if not value:
        return default
    target = Path(value).expanduser().resolve()
    try:
        return target.relative_to(home.resolve()).as_posix()
    except ValueError as error:
        raise RenderError(
            f"{variable} points outside your home directory ({target}); "
            "a machine install writes only inside it"
        ) from error
