"""Installing for the whole machine: ~/.claude/ and ~/.codex/AGENTS.md."""

from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from oees_agents.cli import app
from oees_agents.manifest import MANIFEST_NAME, read_manifest
from oees_agents.writer import LOCK_NAME

runner = CliRunner()


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "home"
    path.mkdir()
    monkeypatch.setenv("HOME", str(path))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    return path


@pytest.fixture
def project(tmp_path: Path) -> Path:
    path = tmp_path / "portal"
    path.mkdir()
    return path


def invoke(*args: str | Path, input: str | None = None) -> Result:
    return runner.invoke(app, [str(arg) for arg in args], input=input)


def init_machine(content_root: Path, *extra: str) -> Result:
    return invoke("init", "--machine", "--yes", "--content-dir", content_root, *extra)


def test_init_for_the_machine_writes_into_the_home_directory(
    home: Path, project: Path, content_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(project)

    result = init_machine(content_root)

    assert result.exit_code == 0, result.output
    manifest = read_manifest(home / MANIFEST_NAME)
    assert manifest.scope == "machine"
    assert manifest.project is None
    assert manifest.targets == ("claude", "codex")
    assert (home / LOCK_NAME).is_file()
    assert (home / ".claude/rules/git.md").is_file()
    assert "Shared engineering rules" in (home / ".claude/CLAUDE.md").read_text()
    assert (home / ".claude/skills/commit/SKILL.md").is_file()
    assert "Shared engineering rules" in (home / ".codex/AGENTS.md").read_text()
    assert list(project.iterdir()) == []


def test_init_asks_for_the_scope_first(home: Path, project: Path, content_root: Path) -> None:
    answers = "\n".join(["machine", "claude", "-", "tdd, git", "none"])

    result = invoke("init", project, "--content-dir", content_root, input=answers + "\n")

    assert result.exit_code == 0, result.output
    manifest = read_manifest(home / MANIFEST_NAME)
    assert manifest.targets == ("claude",)
    assert manifest.defaults == ("tdd", "git")
    assert not (project / MANIFEST_NAME).exists()


def test_a_machine_install_keeps_the_users_own_files(home: Path, content_root: Path) -> None:
    (home / ".claude").mkdir()
    (home / ".claude/CLAUDE.md").write_text("# My own preferences\n")
    (home / ".claude/settings.json").write_text('{"model": "opus"}\n')

    result = init_machine(content_root, "--target", "claude")

    assert result.exit_code == 0, result.output
    claude_md = (home / ".claude/CLAUDE.md").read_text()
    assert claude_md.endswith("# My own preferences\n")
    assert (home / ".claude/settings.json").read_text() == '{"model": "opus"}\n'
    assert invoke("check", "--machine", "--content-dir", content_root).exit_code == 0


def test_project_questions_do_not_apply_to_a_machine_install(
    home: Path, content_root: Path
) -> None:
    result = init_machine(content_root, "--description", "A portal.")

    assert result.exit_code == 1
    assert "--description" in result.stderr
    assert not (home / MANIFEST_NAME).exists()


def test_update_and_check_work_on_the_machine_install(home: Path, content_root: Path) -> None:
    init_machine(content_root)
    (home / ".claude/rules/git.md").unlink()

    stale = invoke("check", "--machine", "--content-dir", content_root)
    updated = invoke("update", "--machine", "--content-dir", content_root)
    current = invoke("check", "--machine", "--content-dir", content_root)

    assert stale.exit_code == 1
    assert "stale or missing: .claude/rules/git.md" in stale.output
    assert updated.exit_code == 0, updated.output
    assert current.exit_code == 0, current.output


def test_machine_update_refuses_a_project_manifest_in_the_home_directory(
    home: Path, content_root: Path
) -> None:
    invoke(
        "init", home, "--yes", "--content-dir", content_root,
        "--description", "Dotfiles.", "--users", "me", "--target", "codex",
    )  # fmt: skip

    result = invoke("update", "--machine", "--content-dir", content_root)

    assert result.exit_code == 1
    assert "is a project install" in result.stderr


def test_a_project_without_a_manifest_points_at_the_machine_install(
    home: Path, project: Path, content_root: Path
) -> None:
    init_machine(content_root)

    result = invoke("update", project, "--content-dir", content_root)

    assert result.exit_code == 1
    assert "--machine" in result.stderr


def test_a_project_install_says_when_the_machine_install_also_loads(
    home: Path, project: Path, content_root: Path
) -> None:
    init_machine(content_root, "--target", "claude")

    result = invoke(
        "init", project, "--yes", "--content-dir", content_root,
        "--description", "A portal.", "--users", "partners", "--target", "claude",
    )  # fmt: skip

    assert result.exit_code == 0, result.output
    assert "machine install" in result.output
