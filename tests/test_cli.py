import json
import os
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from oees_agents import __version__, sources
from oees_agents.cli import app
from oees_agents.content import load_content
from oees_agents.manifest import MANIFEST_NAME, read_manifest, write_manifest
from oees_agents.writer import LOCK_NAME

from conftest import build_content_tree

runner = CliRunner()

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "PATH": os.environ["PATH"],
}


@pytest.fixture
def project(tmp_path: Path) -> Path:
    path = tmp_path / "octohub"
    path.mkdir()
    return path


def invoke(*args: str | Path, input: str | None = None) -> Result:
    return runner.invoke(app, [str(arg) for arg in args], input=input)


def init(project: Path, content_root: Path, *extra: str) -> Result:
    return invoke(
        "init",
        project,
        "--content-dir",
        content_root,
        "--yes",
        "--description",
        "B2B platform for energy partners.",
        "--users",
        "external partners",
        *extra,
    )


def test_init_with_flags_writes_the_manifest_files_and_lock(
    project: Path, content_root: Path
) -> None:
    result = init(
        project,
        content_root,
        "--target",
        "claude",
        "--target",
        "codex",
        "--kit",
        "fastapi",
        "--no-default",
        "tdd",
        "--blast-radius",
        "regulated",
        "--subagents",
        "extended",
        "--loop",
        "tier-0-daily-health-scan",
    )

    assert result.exit_code == 0, result.output
    manifest = read_manifest(project / MANIFEST_NAME)
    assert manifest.targets == ("claude", "codex")
    assert manifest.kits == ("fastapi",)
    assert "tdd" not in manifest.defaults
    assert manifest.project is not None
    assert manifest.project.name == "octohub"
    assert manifest.project.blast_radius == "regulated"
    assert manifest.extras.subagents == "extended"
    assert manifest.extras.loops == ("tier-0-daily-health-scan",)
    assert (project / LOCK_NAME).is_file()
    assert (project / ".claude/skills/fastapi/SKILL.md").is_file()
    assert not (project / ".claude/rules/tdd.md").exists()
    assert "@rules/tdd.md" not in (project / ".claude/CLAUDE.md").read_text()
    assert "**octohub**: B2B platform" in (project / "AGENTS.md").read_text()
    assert not (project / ".cursor").exists()


def test_init_answers_piped_questions_in_order(project: Path, content_root: Path) -> None:
    answers = "\n".join(
        [
            "claude",  # targets
            "",  # name: keep the directory name
            "A platform.",  # description
            "vendors",  # users
            "customer-facing",  # blast radius
            "trunk",  # default branch
            "",  # check
            "make lint",  # fast check
            "django-drf, htmx-alpine",  # kits
            "tdd, git",  # defaults to keep
            "none",  # subagents
            "-",  # loops
        ]
    )

    result = invoke("init", project, "--content-dir", content_root, input=answers + "\n")

    assert result.exit_code == 0, result.output
    manifest = read_manifest(project / MANIFEST_NAME)
    assert manifest.project is not None
    assert manifest.project.name == "octohub"
    assert manifest.project.default_branch == "trunk"
    assert manifest.project.check == "make check"
    assert manifest.project.check_fast == "make lint"
    assert manifest.kits == ("django-drf", "htmx-alpine")
    assert manifest.defaults == ("tdd", "git")
    assert manifest.extras.subagents == "none"
    assert not (project / ".claude/agents").exists()


def test_init_without_a_required_flag_fails_and_writes_nothing(
    project: Path, content_root: Path
) -> None:
    result = invoke("init", project, "--content-dir", content_root, "--yes", "--users", "u")

    assert result.exit_code == 2
    assert "--description" in result.output
    assert list(project.iterdir()) == []


def test_init_rejects_an_unknown_kit(project: Path, content_root: Path) -> None:
    result = init(project, content_root, "--kit", "rails")

    assert result.exit_code == 2
    assert "unknown kit 'rails'" in result.output
    assert list(project.iterdir()) == []


def test_init_refuses_an_already_initialised_project(project: Path, content_root: Path) -> None:
    assert init(project, content_root).exit_code == 0

    again = init(project, content_root)

    assert again.exit_code == 1
    assert "oees-agents update" in again.output


def test_init_records_the_bundled_version_as_source(
    project: Path, content_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sources, "bundled_root", lambda: content_root)

    result = invoke("init", project, "--yes", "--description", "d", "--users", "u")

    assert result.exit_code == 0, result.output
    assert read_manifest(project / MANIFEST_NAME).source == f"v{__version__}"


def test_init_from_a_content_dir_records_local_as_source(project: Path, content_root: Path) -> None:
    init(project, content_root)

    assert read_manifest(project / MANIFEST_NAME).source == "local"


def test_init_lists_files_it_would_not_overwrite(project: Path, content_root: Path) -> None:
    (project / ".claude").mkdir()
    (project / ".claude/settings.json").write_text('{"mine": true}\n')

    result = init(project, content_root, "--target", "claude")

    assert result.exit_code == 0, result.output
    assert ".claude/settings.json" in result.output
    assert "not written by oees-agents" in result.output
    assert (project / ".claude/settings.json").read_text() == '{"mine": true}\n'


def test_update_rerenders_from_the_manifest_and_removes_a_disabled_kit(
    project: Path, content_root: Path
) -> None:
    init(project, content_root, "--target", "claude", "--kit", "fastapi")
    manifest_path = project / MANIFEST_NAME
    write_manifest(manifest_path, replace(read_manifest(manifest_path), kits=()))

    result = invoke("update", project, "--content-dir", content_root)

    assert result.exit_code == 0, result.output
    assert not (project / ".claude/skills/fastapi").exists()


def test_update_never_re_adds_a_default_the_project_removed(
    project: Path, content_root: Path
) -> None:
    init(project, content_root, "--target", "claude", "--no-default", "tdd")

    invoke("update", project, "--content-dir", content_root)
    invoke("update", project, "--content-dir", content_root)

    assert not (project / ".claude/rules/tdd.md").exists()


def test_update_keeps_a_modified_file_unless_forced(project: Path, content_root: Path) -> None:
    init(project, content_root, "--target", "claude")
    rule = project / ".claude/rules/git.md"
    rule.write_text("our own git rule\n")
    (content_root / "content/defaults/git.md").write_text("---\ndescription: g\n---\nNew.\n")

    kept = invoke("update", project, "--content-dir", content_root)

    assert kept.exit_code == 0
    assert ".claude/rules/git.md" in kept.output
    assert rule.read_text() == "our own git rule\n"

    forced = invoke("update", project, "--content-dir", content_root, "--force")

    assert forced.exit_code == 0
    assert rule.read_text().endswith("New.\n")


def test_update_without_a_manifest_points_at_init(project: Path, content_root: Path) -> None:
    result = invoke("update", project, "--content-dir", content_root)

    assert result.exit_code == 1
    assert "oees-agents init" in result.output


def test_check_passes_right_after_init(project: Path, content_root: Path) -> None:
    init(project, content_root)

    result = invoke("check", project, "--content-dir", content_root)

    assert result.exit_code == 0, result.output
    assert "up to date" in result.output


def test_check_fails_on_an_edited_generated_file(project: Path, content_root: Path) -> None:
    init(project, content_root, "--target", "cursor")
    (project / ".cursor/rules/git.mdc").write_text("edited\n")

    result = invoke("check", project, "--content-dir", content_root)

    assert result.exit_code == 1
    assert ".cursor/rules/git.mdc" in result.output


def test_check_fails_when_the_manifest_changed_without_update(
    project: Path, content_root: Path
) -> None:
    init(project, content_root, "--target", "claude")
    manifest_path = project / MANIFEST_NAME
    manifest = read_manifest(manifest_path)
    write_manifest(
        manifest_path, replace(manifest, extras=replace(manifest.extras, subagents="none"))
    )

    result = invoke("check", project, "--content-dir", content_root)

    assert result.exit_code == 1
    assert ".claude/agents/implementer.md" in result.output


def test_check_never_writes(project: Path, content_root: Path) -> None:
    init(project, content_root, "--target", "claude")
    (project / ".claude/rules/git.md").unlink()

    invoke("check", project, "--content-dir", content_root)

    assert not (project / ".claude/rules/git.md").exists()


def test_list_prints_kits_defaults_and_extras(content_root: Path) -> None:
    result = invoke("list", "--content-dir", content_root)

    assert result.exit_code == 0, result.output
    assert "fastapi  The fastapi stack kit." in result.output
    assert "tdd  tdd default" in result.output
    assert "Conduct (always on)" in result.output
    assert "tier-0-daily-health-scan" in result.output
    assert "extended" in result.output


def test_a_malformed_manifest_is_reported_without_a_traceback(
    project: Path, content_root: Path
) -> None:
    (project / MANIFEST_NAME).write_text("version = 1\nsurprise = true\n")

    result = invoke("update", project, "--content-dir", content_root)

    assert result.exit_code == 1
    assert "unknown key 'surprise'" in result.output
    assert "Traceback" not in result.output


@pytest.fixture
def tagged_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repository = build_content_tree(tmp_path / "remote agents")
    (repository / "content/defaults/git.md").write_text("---\ndescription: g\n---\nTagged.\n")
    for command in (
        ["init", "-q", "-b", "main"],
        ["add", "."],
        ["commit", "-q", "-m", "content"],
        ["tag", "v9.9.9"],
    ):
        subprocess.run(["git", "-C", str(repository), *command], check=True, env=GIT_ENV)
    monkeypatch.setenv("OEES_AGENTS_REPOSITORY", str(repository))
    return repository


def test_init_with_ref_renders_that_tag_and_pins_it(project: Path, tagged_repository: Path) -> None:
    result = invoke(
        "init",
        project,
        "--ref",
        "v9.9.9",
        "--yes",
        "--description",
        "d",
        "--users",
        "u",
        "--target",
        "claude",
    )

    assert result.exit_code == 0, result.output
    assert read_manifest(project / MANIFEST_NAME).source == "v9.9.9"
    assert (project / ".claude/rules/git.md").read_text().endswith("Tagged.\n")


def test_update_with_ref_changes_only_the_source_line(
    project: Path, content_root: Path, tagged_repository: Path
) -> None:
    init(project, content_root, "--target", "claude")
    manifest_path = project / MANIFEST_NAME
    with_comment = manifest_path.read_text().replace("[rules]", "# tdd stays\n[rules]")
    manifest_path.write_text(with_comment)

    result = invoke("update", project, "--ref", "v9.9.9")

    assert result.exit_code == 0, result.output
    assert manifest_path.read_text() == with_comment.replace('"local"', '"v9.9.9"')


def test_an_unknown_ref_fails_cleanly(project: Path, tagged_repository: Path) -> None:
    result = invoke(
        "init", project, "--ref", "v0.0.404", "--yes", "--description", "d", "--users", "u"
    )

    assert result.exit_code == 1
    assert "v0.0.404" in result.output
    assert list(project.iterdir()) == []


def test_verbose_logs_each_file_operation_as_json_with_a_run_id(
    project: Path, content_root: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--verbose",
            "init",
            str(project),
            "--content-dir",
            str(content_root),
            "--yes",
            "--description",
            "d",
            "--users",
            "u",
            "--target",
            "codex",
        ],
    )

    records = [json.loads(line) for line in result.stderr.splitlines() if line.startswith("{")]
    assert result.exit_code == 0, result.output
    assert {"message": "wrote file", "path": "AGENTS.md"}.items() <= records[0].items()
    assert len({record["run_id"] for record in records}) == 1
    assert records[0]["run_id"]


LEGACY_FIXTURE = Path(__file__).resolve().parent / "fixtures/legacy/main"
REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def legacy_project(project: Path) -> Path:
    shutil.copytree(LEGACY_FIXTURE, project, dirs_exist_ok=True, symlinks=True)
    return project


def init_legacy(project: Path, *extra: str) -> Result:
    return invoke(
        "init",
        project,
        "--content-dir",
        REPO,
        "--yes",
        "--description",
        "d",
        "--users",
        "u",
        *extra,
    )


def test_init_migrates_a_pre_manifest_install(legacy_project: Path) -> None:
    claude_md = legacy_project / ".claude/CLAUDE.md"
    claude_md.write_text("Project rule.\n" + claude_md.read_text())

    result = init_legacy(legacy_project)

    assert result.exit_code == 0, result.output
    assert "pre-manifest install" in result.output
    manifest = read_manifest(legacy_project / MANIFEST_NAME)
    assert set(manifest.defaults) == set(load_content(REPO).defaults)
    assert manifest.extras.subagents == "none"
    assert not (legacy_project / ".claude/skills/commit/commit.md").exists()
    assert (legacy_project / ".claude/skills/commit/SKILL.md").is_file()
    text = claude_md.read_text()
    assert "Project rule.\n" in text
    assert text.count("@rules/tdd.md") == 1
    check = invoke("check", legacy_project, "--content-dir", REPO)
    assert check.exit_code == 0, check.output


def test_init_keeps_and_lists_legacy_files_the_project_edited(legacy_project: Path) -> None:
    edited = legacy_project / ".claude/loops/tier-0-daily-health-scan.md"
    edited.write_text("Our own tuned loop.\n")

    result = init_legacy(legacy_project)

    assert result.exit_code == 0, result.output
    assert ".claude/loops/tier-0-daily-health-scan.md" in result.output
    assert edited.read_text() == "Our own tuned loop.\n"


def test_flags_override_what_a_legacy_install_implies(legacy_project: Path) -> None:
    result = init_legacy(legacy_project, "--subagents", "core", "--target", "claude")

    assert result.exit_code == 0, result.output
    manifest = read_manifest(legacy_project / MANIFEST_NAME)
    assert manifest.extras.subagents == "core"
    assert manifest.targets == ("claude",)
