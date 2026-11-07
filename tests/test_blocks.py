from pathlib import Path

import pytest

from oees_agents.blocks import (
    BEGIN,
    END,
    BlockError,
    extract,
    merge,
    read_target,
    remove,
    splice,
)
from oees_agents.output import ManagedBlock

BOTTOM = ManagedBlock(body="Shared rules.\n", placement="bottom")
TOP = ManagedBlock(body="Shared rules.\n", placement="top")
BLOCK = f"{BEGIN}\n\nShared rules.\n\n{END}\n".encode()


def lines(*items: str, newline: str = "\n") -> bytes:
    return "".join(item + newline for item in items).encode()


def test_a_missing_file_becomes_just_the_block() -> None:
    assert splice(None, BOTTOM) == BLOCK
    assert splice(b"", TOP) == BLOCK


def test_without_markers_the_block_is_appended_after_a_blank_line() -> None:
    assert splice(b"Local.\n", BOTTOM) == b"Local.\n\n" + BLOCK


def test_without_markers_and_without_a_final_newline_local_bytes_are_kept() -> None:
    assert splice(b"Local.", BOTTOM) == b"Local.\n\n" + BLOCK


def test_without_markers_a_top_block_is_prepended() -> None:
    assert splice(b"Local.\n", TOP) == BLOCK + b"\nLocal.\n"


def test_an_existing_block_is_replaced_and_local_text_kept_byte_for_byte() -> None:
    existing = lines("Before.", BEGIN, "Outdated.", END, "After.")

    assert splice(existing, BOTTOM) == b"Before.\n" + BLOCK + b"After.\n"


def test_splicing_is_idempotent() -> None:
    once = splice(b"Local.\n", TOP)

    assert splice(once, TOP) == once
    assert once.count(BEGIN.encode()) == 1


def test_crlf_files_keep_their_local_bytes_and_get_a_crlf_block() -> None:
    prefix = b"Local before.\r\n\r\n"
    suffix = b"\r\nLocal after.\r\n"
    existing = prefix + lines(BEGIN, "Outdated.", END, newline="\r\n") + suffix

    result = splice(existing, BOTTOM)

    assert result == prefix + BLOCK.replace(b"\n", b"\r\n") + suffix
    assert splice(result, BOTTOM) == result


@pytest.mark.parametrize(
    "existing",
    [
        lines("Local.", BEGIN, "Stale."),
        lines("Local.", END),
        lines(BEGIN, END, BEGIN, END),
        lines(END, "Local.", BEGIN),
    ],
    ids=["unclosed", "orphan", "duplicate", "reversed"],
)
def test_malformed_or_duplicate_markers_are_refused(existing: bytes) -> None:
    with pytest.raises(BlockError, match="markers"):
        splice(existing, BOTTOM)


def test_markers_must_be_whole_lines_to_count() -> None:
    existing = f"Mentions {BEGIN} inline.\n".encode()

    assert splice(existing, BOTTOM) == existing + b"\n" + BLOCK


def test_extract_returns_the_block_bytes_or_none() -> None:
    assert extract(b"Local.\n") is None
    assert extract(b"Before.\n" + BLOCK + b"After.\n") == BLOCK


def test_remove_takes_out_the_block_and_its_separator() -> None:
    assert remove(splice(b"Local.\n", BOTTOM)) == b"Local.\n"
    assert remove(splice(b"Local.\n", TOP)) == b"Local.\n"
    assert remove(BLOCK) == b""


def test_read_target_refuses_a_symlink_without_touching_it(tmp_path: Path) -> None:
    original = tmp_path / "linked.md"
    original.write_text("Keep me.\n")
    link = tmp_path / "AGENTS.md"
    link.symlink_to(original)

    with pytest.raises(BlockError, match="symlink"):
        read_target(link)
    assert link.is_symlink()
    assert original.read_text() == "Keep me.\n"


def test_read_target_refuses_a_directory(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").mkdir()

    with pytest.raises(BlockError, match="not a regular file"):
        read_target(tmp_path / "AGENTS.md")


def test_read_target_returns_none_for_a_missing_file(tmp_path: Path) -> None:
    assert read_target(tmp_path / "AGENTS.md") is None


def test_merge_warns_when_the_result_exceeds_the_block_limit(tmp_path: Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_bytes(b"x" * 40_000 + b"\n")
    block = ManagedBlock(body="Rules.\n", placement="bottom", max_bytes=32_768)

    data, warnings = merge(path, block)

    assert len(data) > 32_768
    assert warnings == [f"{path.name} is {len(data)} bytes, over the 32768-byte limit"]


def test_merge_does_not_write(tmp_path: Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_bytes(b"Local.\n")

    merge(path, BOTTOM)

    assert path.read_bytes() == b"Local.\n"
