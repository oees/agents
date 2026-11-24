import os
import stat
from pathlib import Path

import pytest

from oees_agents.fs import remove_file, write_atomic


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_a_new_file_is_readable_by_everyone_and_writable_by_its_owner(tmp_path: Path) -> None:
    write_atomic(tmp_path / "a/b.md", b"new\n")

    assert (tmp_path / "a/b.md").read_bytes() == b"new\n"
    assert mode(tmp_path / "a/b.md") == 0o644


def test_a_replaced_file_keeps_its_mode_and_leaves_no_temporary_file(tmp_path: Path) -> None:
    script = tmp_path / "run.sh"
    script.write_bytes(b"old\n")
    script.chmod(0o755)

    write_atomic(script, b"new\n")

    assert script.read_bytes() == b"new\n"
    assert mode(script) == 0o755
    assert sorted(path.name for path in tmp_path.iterdir()) == ["run.sh"]


def test_a_failed_write_keeps_the_old_file_and_removes_the_temporary_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "manifest.toml"
    target.write_bytes(b"old\n")

    def fail(source: str, destination: Path) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError, match="disk full"):
        write_atomic(target, b"new\n")

    assert target.read_bytes() == b"old\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["manifest.toml"]


def test_removing_a_file_removes_the_directories_it_leaves_empty(tmp_path: Path) -> None:
    write_atomic(tmp_path / ".claude/skills/commit/SKILL.md", b"x\n")
    write_atomic(tmp_path / ".claude/settings.json", b"{}\n")

    remove_file(tmp_path, ".claude/skills/commit/SKILL.md")

    assert sorted(path.name for path in (tmp_path / ".claude").iterdir()) == ["settings.json"]
