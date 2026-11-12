import json
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from oees_agents.blocks import BEGIN, END
from oees_agents.content import Content, load_content
from oees_agents.legacy import (
    OLD_RULE_DEFAULTS,
    LegacyError,
    LegacyInstall,
    detect,
    legacy_manifest,
    migrate,
)
from oees_agents.manifest import MANIFEST_NAME, Project
from oees_agents.render import render
from oees_agents.writer import sync

from conftest import REPO

FIXTURE = REPO / "tests/fixtures/legacy/main"
HASHES = REPO / "src/oees_agents/legacy_hashes.json"
GENERATOR = REPO / "scripts/generate_legacy_hashes.py"
CLAUDE_MD = ".claude/CLAUDE.md"
MAIN_IMPORTS = tuple(
    f"@rules/{name}.md".encode()
    for name in (
        "code-quality",
        "git",
        "migrations",
        "no-inline-imports",
        "observability",
        "secrets",
        "standards",
        "tdd",
    )
)
PROJECT = Project(
    name="octohub",
    description="A partner platform.",
    users="partners",
    blast_radius="customer-facing",
    default_branch="main",
    check="make check",
    check_fast="make check-fast",
)


@pytest.fixture(scope="module")
def content() -> Content:
    return load_content(REPO)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(FIXTURE, root)
    return root


def files_under(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    }


def detected(root: Path, content: Content) -> LegacyInstall:
    install = detect(root, content)
    assert install is not None
    return install


def lines(*parts: bytes, newline: bytes = b"\n") -> bytes:
    return b"".join(part + newline for part in parts)


def test_the_main_install_migrates_to_every_default_and_no_project(
    project: Path, content: Content
) -> None:
    manifest = legacy_manifest(detected(project, content), source="v1.0.0")

    assert manifest.project is None
    assert manifest.defaults == tuple(content.defaults)
    assert len(manifest.defaults) == 7
    assert manifest.source == "v1.0.0"
    assert manifest.kits == ()
    assert manifest.extras.subagents == "none"
    assert manifest.extras.commands is True
    # The old installer shipped three loops; tier 3 arrived after it, so no legacy install has it.
    assert manifest.extras.loops == (
        "tier-0-daily-health-scan",
        "tier-1-increase-test-coverage",
        "tier-2-behavioural-improvements",
    )


def test_the_main_install_targets_claude_and_cursor(project: Path, content: Content) -> None:
    assert detected(project, content).targets == ("claude", "cursor")


def test_every_file_main_installed_is_proven_ours(project: Path, content: Content) -> None:
    install = detected(project, content)

    assert set(install.removable) == files_under(project) - {CLAUDE_MD}
    assert install.kept == ()


def test_shared_rule_markers_in_agents_md_add_codex_and_their_rules(
    tmp_path: Path, content: Content
) -> None:
    (tmp_path / "AGENTS.md").write_text(
        f"# Ours\n\n{BEGIN}\n\n## Shared engineering rules\n"
        "\n<!-- Source: rules/standards.md -->\n# Standards\n"
        "\n<!-- Source: content/defaults/tdd.md -->\n# TDD\n"
        f"\n{END}\n"
    )

    install = detected(tmp_path, content)

    assert install.targets == ("codex",)
    assert install.defaults == ("api", "standards", "tdd")
    assert install.removable == ()


@pytest.mark.parametrize(
    ("rules", "defaults"),
    [
        (("code-quality",), ("quality-gates",)),
        (("standards",), ("api", "standards")),
        (("secrets", "no-inline-imports"), ()),
        (("conduct", "api", "quality-gates"), ("api", "quality-gates")),
    ],
)
def test_old_rule_names_imply_the_new_defaults(
    tmp_path: Path, content: Content, rules: tuple[str, ...], defaults: tuple[str, ...]
) -> None:
    for name in rules:
        path = tmp_path / ".claude/rules" / f"{name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {name}, edited\n")

    install = detected(tmp_path, content)

    assert install.targets == ("claude",)
    assert install.defaults == defaults


def test_every_old_and_new_rule_name_has_a_mapping(content: Content) -> None:
    assert set(content.defaults) | set(content.conduct) <= set(OLD_RULE_DEFAULTS)
    for name in content.conduct:
        assert OLD_RULE_DEFAULTS[name] == ()


def test_local_lines_in_claude_md_survive_byte_for_byte(project: Path, content: Content) -> None:
    (project / CLAUDE_MD).write_bytes(
        lines(b"# Octohub", b"", b"Be kind.", *MAIN_IMPORTS[:4])
        + lines(b"Between the imports.", b"  ")
        + lines(*MAIN_IMPORTS[4:], b"@rules/team.md", b"After.")[:-1]
    )

    install = detected(project, content)
    migrate(project, install)

    expected = b"# Octohub\n\nBe kind.\nBetween the imports.\n  \n@rules/team.md\nAfter."
    assert install.claude_md == expected
    assert (project / CLAUDE_MD).read_bytes() == expected


def test_a_crlf_claude_md_keeps_its_crlf(project: Path, content: Content) -> None:
    (project / CLAUDE_MD).write_bytes(
        lines(b"# Octohub", *MAIN_IMPORTS, b"Keep me.", newline=b"\r\n")
    )

    install = detected(project, content)

    assert install.claude_md == b"# Octohub\r\nKeep me.\r\n"


def test_a_claude_md_left_with_only_whitespace_is_deleted(project: Path, content: Content) -> None:
    (project / CLAUDE_MD).write_bytes(lines(*MAIN_IMPORTS, b"", b"  "))

    migrate(project, detected(project, content))

    assert not (project / ".claude").exists()


def test_a_claude_md_without_legacy_imports_is_left_alone(project: Path, content: Content) -> None:
    (project / CLAUDE_MD).write_bytes(b"# Ours\n@rules/team.md\n")

    install = detected(project, content)
    migrate(project, install)

    assert install.claude_md is None
    assert (project / CLAUDE_MD).read_bytes() == b"# Ours\n@rules/team.md\n"


def test_migrate_removes_every_removable_file_and_nothing_else(
    project: Path, content: Content
) -> None:
    (project / CLAUDE_MD).write_bytes(lines(b"# Ours", *MAIN_IMPORTS))
    (project / ".claude/skills/plan/notes.md").write_text("our notes\n")
    before = files_under(project)

    install = detected(project, content)
    migrate(project, install)

    assert install.removable
    assert files_under(project) == before - set(install.removable)
    assert not (project / ".cursor").exists()
    assert not (project / ".claude/rules").exists()
    assert (project / ".claude/skills/plan/notes.md").exists()


def test_detect_never_writes(project: Path, content: Content) -> None:
    before = {path: (project / path).read_bytes() for path in files_under(project)}

    detected(project, content)

    assert {path: (project / path).read_bytes() for path in files_under(project)} == before


def test_a_legacy_file_the_project_edited_is_kept(project: Path, content: Content) -> None:
    edited = project / ".claude/rules/tdd.md"
    edited.write_text(edited.read_text() + "\nOur own addition.\n")

    install = detected(project, content)
    migrate(project, install)

    assert ".claude/rules/tdd.md" in install.kept
    assert ".claude/rules/tdd.md" not in install.removable
    assert edited.read_text().endswith("Our own addition.\n")
    assert "tdd" in install.defaults


def test_a_project_file_with_an_unknown_name_is_neither_removed_nor_kept(
    project: Path, content: Content
) -> None:
    (project / ".claude/rules/team.md").write_text("# Our team rule\n")

    install = detected(project, content)
    migrate(project, install)

    assert ".claude/rules/team.md" not in (*install.removable, *install.kept)
    assert (project / ".claude/rules/team.md").read_text() == "# Our team rule\n"


def test_a_project_that_dropped_tdd_gets_every_default_but_tdd(
    project: Path, content: Content
) -> None:
    (project / ".claude/rules/tdd.md").unlink()
    (project / CLAUDE_MD).write_bytes(lines(*MAIN_IMPORTS[:-1]))

    install = detected(project, content)

    assert install.defaults == tuple(name for name in content.defaults if name != "tdd")


def test_a_repo_with_a_manifest_is_not_legacy(project: Path, content: Content) -> None:
    (project / MANIFEST_NAME).write_text("version = 1\n")

    assert detect(project, content) is None


def test_a_repo_with_nothing_legacy_is_not_legacy(tmp_path: Path, content: Content) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / CLAUDE_MD).write_text("# Ours\n")
    (tmp_path / "AGENTS.md").write_text("# Ours\n")

    assert detect(tmp_path, content) is None


def test_a_projects_own_settings_json_is_not_a_legacy_install(
    tmp_path: Path, content: Content
) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude/settings.json").write_text('{"permissions": {}}\n')

    assert detect(tmp_path, content) is None


def test_a_projects_own_settings_json_is_not_listed_as_kept(
    project: Path, content: Content
) -> None:
    (project / ".claude/settings.json").write_text('{"permissions": {}}\n')

    install = detected(project, content)

    assert ".claude/settings.json" not in (*install.removable, *install.kept)


def test_a_symlinked_legacy_file_is_kept_and_never_deleted(
    tmp_path: Path, project: Path, content: Content
) -> None:
    original = project / ".claude/rules/git.md"
    outside = tmp_path / "shared-git.md"
    shutil.copy(original, outside)
    original.unlink()
    original.symlink_to(outside)

    install = detected(project, content)
    migrate(project, install)

    assert ".claude/rules/git.md" in install.kept
    assert ".claude/rules/git.md" not in install.removable
    assert original.is_symlink()
    assert outside.exists()


def test_files_behind_a_symlinked_directory_are_never_deleted(
    tmp_path: Path, project: Path, content: Content
) -> None:
    outside = tmp_path / "shared-cursor-rules"
    shutil.move(project / ".cursor/rules", outside)
    (project / ".cursor/rules").symlink_to(outside)

    install = detected(project, content)
    migrate(project, install)

    assert not any(path.startswith(".cursor/") for path in install.removable)
    assert files_under(outside) == files_under(FIXTURE / ".cursor/rules")


def test_migrate_refuses_a_symlink_before_changing_anything(
    tmp_path: Path, project: Path, content: Content
) -> None:
    install = detected(project, content)
    outside = tmp_path / "shared-git.md"
    shutil.copy(project / ".claude/rules/git.md", outside)
    (project / ".claude/rules/git.md").unlink()
    (project / ".claude/rules/git.md").symlink_to(outside)
    before = files_under(project)

    with pytest.raises(LegacyError, match=r"\.claude/rules/git\.md"):
        migrate(project, install)

    assert files_under(project) == before


def test_migrate_refuses_a_file_that_changed_since_detection(
    project: Path, content: Content
) -> None:
    install = detected(project, content)
    (project / ".claude/rules/tdd.md").write_text("changed\n")

    with pytest.raises(LegacyError, match=r"\.claude/rules/tdd\.md"):
        migrate(project, install)

    assert files_under(project) == files_under(FIXTURE)


def test_migrating_then_writing_conflicts_only_on_what_the_project_edited(
    project: Path, content: Content
) -> None:
    edited = project / ".claude/rules/tdd.md"
    edited.write_text(edited.read_text() + "\nOur own addition.\n")
    (project / CLAUDE_MD).write_bytes(lines(b"# Octohub notes", *MAIN_IMPORTS))
    install = detected(project, content)

    migrate(project, install)
    manifest = replace(legacy_manifest(install, source="local"), project=PROJECT)
    result = sync(project, render(manifest, content))

    assert [conflict.path for conflict in result.conflicts] == [".claude/rules/tdd.md"]
    assert edited.read_text().endswith("Our own addition.\n")
    assert set(install.removable) & set(result.writes)
    claude_md = (project / CLAUDE_MD).read_bytes()
    assert claude_md.startswith(BEGIN.encode())
    assert claude_md.endswith(b"# Octohub notes\n")


def _history_reason() -> str | None:
    if shutil.which("git") is None:
        return "git is not installed"
    probe = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "--is-shallow-repository"],
        capture_output=True,
        check=False,
        text=True,
    )
    if probe.returncode != 0:
        return "not running in a git checkout"
    if probe.stdout.strip() == "true":
        return "shallow clone: the history that produced the hashes is missing"
    return None


@pytest.mark.skipif(_history_reason() is not None, reason=_history_reason() or "")
def test_the_known_hashes_match_the_git_history() -> None:
    regenerated = subprocess.run(
        [sys.executable, str(GENERATOR), "--stdout"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert json.loads(regenerated) == json.loads(HASHES.read_text(encoding="utf-8"))
    assert regenerated == HASHES.read_text(encoding="utf-8")
