from pathlib import Path

import pytest

from oees_agents.output import RenderError
from oees_agents.scope import claude_dir, codex_dir, install_root


def test_a_project_install_writes_into_the_project(home: Path) -> None:
    assert install_root("project", Path("work/app")) == Path("work/app")
    assert claude_dir("project") == ".claude"
    assert codex_dir("project") == ".codex"


def test_a_machine_install_writes_into_the_home_directory(home: Path) -> None:
    assert install_root("machine", Path("work/app")) == home
    assert claude_dir("machine") == ".claude"
    assert codex_dir("machine") == ".codex"


def test_a_machine_install_follows_the_tools_own_home_variables(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(home / "config/claude"))
    monkeypatch.setenv("CODEX_HOME", str(home / "config/codex"))

    assert claude_dir("machine") == "config/claude"
    assert codex_dir("machine") == "config/codex"


def test_a_tool_home_outside_the_home_directory_is_refused(
    home: Path, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path_factory.mktemp("elsewhere")))

    with pytest.raises(RenderError, match="CODEX_HOME points outside your home directory"):
        codex_dir("machine")
