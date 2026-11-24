from pathlib import Path

import pytest

from oees_agents.output import RenderError
from oees_agents.scope import layout, machine_layout, project_layout


def test_a_project_install_writes_into_the_project() -> None:
    project = project_layout(Path("work/app"))

    assert project.root == Path("work/app")
    assert (project.claude, project.codex) == (".claude", ".codex")
    assert project.update_command == "oees-agents update"


def test_a_machine_install_writes_into_the_home_directory(home: Path) -> None:
    machine = machine_layout()

    assert machine.root == home
    assert (machine.claude, machine.codex) == (".claude", ".codex")
    assert machine.update_command == "oees-agents update --machine"
    assert layout("machine", Path("work/app")) == machine


def test_a_machine_install_follows_the_tools_own_home_variables(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(home / "config/claude"))
    monkeypatch.setenv("CODEX_HOME", str(home / "config/codex"))

    machine = machine_layout()

    assert (machine.claude, machine.codex) == ("config/claude", "config/codex")


def test_a_tool_home_outside_the_home_directory_is_refused(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path_factory.mktemp("elsewhere")))

    with pytest.raises(RenderError, match="CODEX_HOME points outside your home directory"):
        machine_layout()
