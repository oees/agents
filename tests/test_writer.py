from pathlib import Path

import pytest

from oees_agents.blocks import BEGIN, END
from oees_agents.output import ManagedBlock, Output
from oees_agents.writer import (
    LOCK_NAME,
    Lock,
    WriterError,
    apply,
    digest,
    plan,
    read_lock,
    sync,
)

RULES = ManagedBlock(body="Shared rules v1.\n", placement="bottom")


def locked(root: Path) -> Lock:
    lock = read_lock(root)
    assert lock is not None
    return lock


def output(files: dict[str, bytes] | None = None, **blocks: ManagedBlock) -> Output:
    return Output(
        files=files if files is not None else {".claude/rules/tdd.md": b"tdd v1\n"},
        blocks={name.replace("_", "."): block for name, block in blocks.items()},
    )


def test_a_fresh_install_writes_every_owned_file_and_records_it(tmp_path: Path) -> None:
    files = {".claude/rules/tdd.md": b"tdd\n", ".claude/settings.json": b"{}\n"}

    sync(tmp_path, output(files))

    assert (tmp_path / ".claude/rules/tdd.md").read_bytes() == b"tdd\n"
    assert read_lock(tmp_path) == Lock(
        files={path: digest(data) for path, data in files.items()}, blocks={}
    )


def test_the_lock_records_path_and_sha256(tmp_path: Path) -> None:
    sync(tmp_path, output())

    text = (tmp_path / LOCK_NAME).read_text()
    assert '".claude/rules/tdd.md" = "sha256:' in text
    assert digest(b"tdd v1\n").startswith("sha256:")


def test_files_the_renderer_does_not_own_are_never_touched(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("mine\n")

    sync(tmp_path, output())

    assert (tmp_path / "README.md").read_text() == "mine\n"


def test_a_second_sync_changes_nothing(tmp_path: Path) -> None:
    sync(tmp_path, output(AGENTS_md=RULES))

    again = plan(tmp_path, output(AGENTS_md=RULES), read_lock(tmp_path))

    assert again.is_clean
    assert again.unchanged == (".claude/rules/tdd.md", "AGENTS.md")


def test_update_rewrites_files_it_wrote_that_are_unmodified(tmp_path: Path) -> None:
    sync(tmp_path, output())

    sync(tmp_path, output({".claude/rules/tdd.md": b"tdd v2\n"}))

    assert (tmp_path / ".claude/rules/tdd.md").read_bytes() == b"tdd v2\n"
    assert locked(tmp_path).files[".claude/rules/tdd.md"] == digest(b"tdd v2\n")


def test_update_removes_files_the_new_render_no_longer_produces(tmp_path: Path) -> None:
    kit = {
        ".claude/rules/tdd.md": b"tdd v1\n",
        ".claude/skills/fastapi/SKILL.md": b"kit\n",
        ".claude/skills/fastapi/templates/Makefile": b"check:\n",
    }
    sync(tmp_path, output(kit))

    result = sync(tmp_path, output())

    assert result.deletes == (
        ".claude/skills/fastapi/SKILL.md",
        ".claude/skills/fastapi/templates/Makefile",
    )
    assert not (tmp_path / ".claude/skills/fastapi").exists()
    assert (tmp_path / ".claude/skills").exists() is False
    assert (tmp_path / ".claude/rules/tdd.md").exists()
    assert set(locked(tmp_path).files) == {".claude/rules/tdd.md"}


def test_removal_keeps_directories_that_hold_project_files(tmp_path: Path) -> None:
    sync(tmp_path, output({".claude/skills/fastapi/SKILL.md": b"kit\n"}))
    (tmp_path / ".claude/skills/own").mkdir()
    (tmp_path / ".claude/skills/own/SKILL.md").write_text("mine\n")

    sync(tmp_path, output({}))

    assert (tmp_path / ".claude/skills/own/SKILL.md").read_text() == "mine\n"


def test_a_modified_file_is_not_overwritten_and_is_listed(tmp_path: Path) -> None:
    sync(tmp_path, output({".claude/rules/tdd.md": b"v1\n", ".claude/rules/git.md": b"v1\n"}))
    (tmp_path / ".claude/rules/tdd.md").write_bytes(b"edited locally\n")

    result = sync(
        tmp_path, output({".claude/rules/tdd.md": b"v2\n", ".claude/rules/git.md": b"v2\n"})
    )

    assert [conflict.path for conflict in result.conflicts] == [".claude/rules/tdd.md"]
    assert "modified since oees-agents wrote it" in result.conflicts[0].reason
    assert (tmp_path / ".claude/rules/tdd.md").read_bytes() == b"edited locally\n"
    assert (tmp_path / ".claude/rules/git.md").read_bytes() == b"v2\n"
    assert locked(tmp_path).files[".claude/rules/tdd.md"] == digest(b"v1\n")


def test_force_overwrites_a_modified_file(tmp_path: Path) -> None:
    sync(tmp_path, output())
    (tmp_path / ".claude/rules/tdd.md").write_bytes(b"edited locally\n")

    result = sync(tmp_path, output({".claude/rules/tdd.md": b"v2\n"}), force=True)

    assert result.conflicts == ()
    assert (tmp_path / ".claude/rules/tdd.md").read_bytes() == b"v2\n"


def test_a_modified_file_is_not_removed_without_force(tmp_path: Path) -> None:
    sync(tmp_path, output({".claude/loops/tier-0.md": b"loop\n"}))
    (tmp_path / ".claude/loops/tier-0.md").write_bytes(b"tuned locally\n")

    kept = sync(tmp_path, output({}))

    assert [conflict.path for conflict in kept.conflicts] == [".claude/loops/tier-0.md"]
    assert (tmp_path / ".claude/loops/tier-0.md").read_bytes() == b"tuned locally\n"

    removed = sync(tmp_path, output({}), force=True)

    assert removed.deletes == (".claude/loops/tier-0.md",)
    assert not (tmp_path / ".claude/loops/tier-0.md").exists()


def test_an_existing_file_it_did_not_write_is_left_alone_and_listed(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude/settings.json").write_text('{"mine": true}\n')

    result = sync(tmp_path, output({".claude/settings.json": b"{}\n"}))

    assert [conflict.path for conflict in result.conflicts] == [".claude/settings.json"]
    assert "not written by oees-agents" in result.conflicts[0].reason
    assert (tmp_path / ".claude/settings.json").read_text() == '{"mine": true}\n'
    assert ".claude/settings.json" not in locked(tmp_path).files


def test_an_identical_existing_file_is_adopted(tmp_path: Path) -> None:
    (tmp_path / ".claude/rules").mkdir(parents=True)
    (tmp_path / ".claude/rules/tdd.md").write_bytes(b"tdd v1\n")

    result = sync(tmp_path, output())

    assert result.conflicts == ()
    assert locked(tmp_path).files == {".claude/rules/tdd.md": digest(b"tdd v1\n")}


def test_a_deleted_file_is_written_again(tmp_path: Path) -> None:
    sync(tmp_path, output())
    (tmp_path / ".claude/rules/tdd.md").unlink()

    sync(tmp_path, output())

    assert (tmp_path / ".claude/rules/tdd.md").read_bytes() == b"tdd v1\n"


def test_a_block_keeps_project_text_and_records_only_the_block(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_bytes(b"Project rules.\n")

    sync(tmp_path, output(AGENTS_md=RULES))

    data = (tmp_path / "AGENTS.md").read_bytes()
    assert data.startswith(b"Project rules.\n\n" + BEGIN.encode())
    block = data[data.index(BEGIN.encode()) :]
    assert locked(tmp_path).blocks == {"AGENTS.md": digest(block)}


def test_project_edits_outside_the_block_do_not_count_as_modification(tmp_path: Path) -> None:
    sync(tmp_path, output(AGENTS_md=RULES))
    with (tmp_path / "AGENTS.md").open("ab") as handle:
        handle.write(b"\nLater project note.\n")

    result = sync(
        tmp_path, output(AGENTS_md=ManagedBlock(body="Shared rules v2.\n", placement="bottom"))
    )

    assert result.conflicts == ()
    data = (tmp_path / "AGENTS.md").read_text()
    assert "Shared rules v2." in data
    assert data.endswith("\nLater project note.\n")


def test_an_edited_block_is_not_overwritten_without_force(tmp_path: Path) -> None:
    sync(tmp_path, output(AGENTS_md=RULES))
    path = tmp_path / "AGENTS.md"
    path.write_text(path.read_text().replace("Shared rules v1.", "Hand-edited rules."))
    newer = output(AGENTS_md=ManagedBlock(body="Shared rules v2.\n", placement="bottom"))

    result = sync(tmp_path, newer)

    assert [conflict.path for conflict in result.conflicts] == ["AGENTS.md"]
    assert "Hand-edited rules." in path.read_text()

    sync(tmp_path, newer, force=True)

    assert "Shared rules v2." in path.read_text()


def test_a_pre_manifest_block_is_adopted(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text(f"Local.\n{BEGIN}\nOld shell output.\n{END}\n")

    result = sync(tmp_path, output(AGENTS_md=RULES))

    assert result.conflicts == ()
    assert "Old shell output." not in (tmp_path / "AGENTS.md").read_text()


def test_dropping_a_block_removes_it_and_keeps_project_text(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_bytes(b"Project rules.\n")
    sync(tmp_path, output(AGENTS_md=RULES))

    result = sync(tmp_path, output())

    assert tuple(result.unblocks) == ("AGENTS.md",)
    assert (tmp_path / "AGENTS.md").read_bytes() == b"Project rules.\n"
    assert locked(tmp_path).blocks == {}


def test_dropping_a_block_from_a_file_that_held_only_the_block_deletes_it(tmp_path: Path) -> None:
    sync(tmp_path, output(AGENTS_md=RULES))

    sync(tmp_path, output())

    assert not (tmp_path / "AGENTS.md").exists()


def test_malformed_markers_are_a_conflict_that_force_cannot_override(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text(f"{BEGIN}\nunclosed\n")

    result = sync(tmp_path, output(AGENTS_md=RULES), force=True)

    assert [conflict.path for conflict in result.conflicts] == ["AGENTS.md"]
    assert (tmp_path / "AGENTS.md").read_text() == f"{BEGIN}\nunclosed\n"


def test_a_symlink_is_refused_even_with_force(tmp_path: Path) -> None:
    target = tmp_path / "elsewhere.md"
    target.write_text("keep\n")
    (tmp_path / ".claude/rules").mkdir(parents=True)
    (tmp_path / ".claude/rules/tdd.md").symlink_to(target)

    result = sync(tmp_path, output(), force=True)

    assert [conflict.path for conflict in result.conflicts] == [".claude/rules/tdd.md"]
    assert (tmp_path / ".claude/rules/tdd.md").is_symlink()
    assert target.read_text() == "keep\n"


def test_a_symlinked_parent_directory_is_refused(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    (project / ".claude").symlink_to(outside, target_is_directory=True)

    result = sync(project, output(), force=True)

    assert [conflict.path for conflict in result.conflicts] == [".claude/rules/tdd.md"]
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("path", ["../escape.md", "/etc/passwd", "a/../../b.md"])
def test_paths_outside_the_project_are_rejected(tmp_path: Path, path: str) -> None:
    with pytest.raises(WriterError, match="outside the project"):
        plan(tmp_path, output({path: b"x"}), None)


def test_plan_does_not_write_until_applied(tmp_path: Path) -> None:
    pending = plan(tmp_path, output(AGENTS_md=RULES), None)

    assert not pending.is_clean
    assert list(tmp_path.iterdir()) == []

    apply(tmp_path, pending)

    assert (tmp_path / "AGENTS.md").exists()


def test_the_block_size_warning_is_reported(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_bytes(b"x" * 100 + b"\n")

    result = sync(
        tmp_path, output(AGENTS_md=ManagedBlock(body="r\n", placement="bottom", max_bytes=50))
    )

    size = (tmp_path / "AGENTS.md").stat().st_size
    assert result.warnings == (f"AGENTS.md is {size} bytes, over the 50-byte limit",)


def test_an_invalid_lock_is_an_error(tmp_path: Path) -> None:
    (tmp_path / LOCK_NAME).write_text("version = 9\n")

    with pytest.raises(WriterError, match=LOCK_NAME):
        read_lock(tmp_path)
