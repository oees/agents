"""Where a project install and a machine install put each tool's files.

A project install writes into the project root. A machine install writes into
the home directory, where each tool reads its user-level configuration:
`~/.claude/` for Claude Code and `~/.codex/` for Codex. Each tool's
own variable (`CLAUDE_CONFIG_DIR`, `CODEX_HOME`) moves that directory, and the
install follows it, but only to a place inside the home directory.
"""

import os
from pathlib import Path

from oees_agents.manifest import Scope
from oees_agents.output import RenderError


def install_root(scope: Scope, path: Path) -> Path:
    """The directory that holds the manifest, the lock and every generated path."""
    return Path.home() if scope == "machine" else path


def claude_dir(scope: Scope) -> str:
    return ".claude" if scope == "project" else _in_home("CLAUDE_CONFIG_DIR", ".claude")


def codex_dir(scope: Scope) -> str:
    return ".codex" if scope == "project" else _in_home("CODEX_HOME", ".codex")


def update_command(scope: Scope) -> str:
    """The command that regenerates an install, as its generated text names it."""
    return "oees-agents update --machine" if scope == "machine" else "oees-agents update"


def _in_home(variable: str, default: str) -> str:
    value = os.environ.get(variable)
    if not value:
        return default
    home = Path.home().resolve()
    target = Path(value).expanduser().resolve()
    try:
        return target.relative_to(home).as_posix()
    except ValueError as error:
        raise RenderError(
            f"{variable} points outside your home directory ({target}); "
            "a machine install writes only inside it"
        ) from error
