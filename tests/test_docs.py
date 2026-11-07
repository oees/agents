from pathlib import Path

import pytest

from oees_agents.content import load_content
from oees_agents.docs import (
    REGIONS,
    DocsError,
    fill,
    main,
    render_region,
    stale_docs,
    write_docs,
)

from conftest import CONDUCT, CORE_SUBAGENTS, EXTENDED_SUBAGENTS, KITS, write


def region(name: str, inner: str = "stale\n") -> str:
    return f"<!-- BEGIN GENERATED: {name} -->\n{inner}<!-- END GENERATED: {name} -->\n"


def test_every_region_renders_a_table_with_one_row_per_item(content_root: Path) -> None:
    content = load_content(content_root)

    for name in REGIONS:
        lines = render_region(name, content).splitlines()
        assert lines[0].startswith("| ")
        assert set(lines[1]) <= {"|", "-"}
        assert all(line.startswith("| ") and line.endswith(" |") for line in lines[2:])


def test_conduct_rows_name_each_rule_with_its_description(content_root: Path) -> None:
    table = render_region("conduct", load_content(content_root))

    rows = table.splitlines()[2:]
    assert rows == [f"| `{name}` | {name} conduct |" for name in sorted(CONDUCT)]


def test_subagents_are_listed_core_first_with_their_tier(content_root: Path) -> None:
    rows = render_region("subagents", load_content(content_root)).splitlines()[2:]

    tiers = [row.split(" | ")[1] for row in rows]
    assert tiers == ["core"] * len(CORE_SUBAGENTS) + ["extended"] * len(EXTENDED_SUBAGENTS)
    assert "| `implementer` | core | Use for implementer: in a fresh context. |" in rows


def test_kits_use_their_skill_description(content_root: Path) -> None:
    rows = render_region("kits", load_content(content_root)).splitlines()[2:]

    assert rows == [f"| `{name}` | The {name} stack kit. |" for name in sorted(KITS)]


def test_commands_are_shown_as_slash_commands(content_root: Path) -> None:
    rows = render_region("commands", load_content(content_root)).splitlines()[2:]

    assert "| `/commit` | Run commit. |" in rows


def test_a_loop_without_a_description_is_summarised_by_its_first_heading(
    content_root: Path,
) -> None:
    rows = render_region("loops", load_content(content_root)).splitlines()[2:]

    assert "| `tier-0-daily-health-scan` | tier-0-daily-health-scan |" in rows


def test_a_pipe_in_a_description_cannot_split_the_table_row(content_root: Path) -> None:
    write(
        content_root / "content/conduct/secrets.md",
        "---\ndescription: env vars | secret managers\n---\n\n# Secrets\n",
    )

    rows = render_region("conduct", load_content(content_root)).splitlines()[2:]

    assert "| `secrets` | env vars \\| secret managers |" in rows


def test_an_unknown_region_name_is_refused(content_root: Path) -> None:
    with pytest.raises(DocsError, match="unknown generated region 'nope'"):
        render_region("nope", load_content(content_root))


def test_fill_replaces_only_the_region_and_keeps_the_rest_byte_for_byte(
    content_root: Path,
) -> None:
    content = load_content(content_root)
    before = "# Title\n\nIntro, kept.\n\n"
    after = "\nOutro | with a pipe, kept.\n"

    filled = fill(before + region("kits") + after, content)

    assert filled == before + region("kits", render_region("kits", content) + "\n") + after


def test_fill_fills_every_region_and_is_idempotent(content_root: Path) -> None:
    content = load_content(content_root)
    text = region("conduct") + "\nbetween\n\n" + region("defaults")

    once = fill(text, content)

    assert "stale" not in once
    assert fill(once, content) == once


def test_text_without_regions_is_returned_unchanged(content_root: Path) -> None:
    assert fill("# Nothing generated here\n", load_content(content_root)) == (
        "# Nothing generated here\n"
    )


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("<!-- BEGIN GENERATED: kits -->\nno end\n", "kits is not closed"),
        ("no begin\n<!-- END GENERATED: kits -->\n", "END GENERATED: kits without a BEGIN"),
        (
            "<!-- BEGIN GENERATED: kits -->\n<!-- END GENERATED: loops -->\n",
            "END GENERATED: loops without a BEGIN",
        ),
        (region("kits") + region("kits"), "kits appears more than once"),
        (
            "<!-- BEGIN GENERATED: kits -->\n" + region("loops") + "<!-- END GENERATED: kits -->\n",
            "loops starts inside kits",
        ),
        (region("nope"), "unknown generated region 'nope'"),
    ],
)
def test_malformed_markers_are_refused(content_root: Path, text: str, message: str) -> None:
    with pytest.raises(DocsError, match=message):
        fill(text, load_content(content_root))


def test_write_docs_rewrites_stale_files_and_reports_them(
    content_root: Path, tmp_path: Path
) -> None:
    content = load_content(content_root)
    project = tmp_path / "project"
    write(project / "README.md", "# Readme\n\n" + region("skills"))
    write(project / "CONTRIBUTING.md", "# Contributing\n\nNo tables.\n")

    assert stale_docs(project, content) == ["README.md"]
    assert write_docs(project, content) == ["README.md"]
    assert stale_docs(project, content) == []
    assert write_docs(project, content) == []
    assert (project / "CONTRIBUTING.md").read_text(encoding="utf-8") == (
        "# Contributing\n\nNo tables.\n"
    )


def test_a_missing_doc_file_is_an_error(content_root: Path, tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Readme\n")

    with pytest.raises(DocsError, match=r"CONTRIBUTING\.md"):
        stale_docs(tmp_path, load_content(content_root))


def test_main_fills_the_docs_of_a_content_checkout(content_root: Path) -> None:
    write(content_root / "README.md", region("loops"))
    write(content_root / "CONTRIBUTING.md", region("kits"))

    assert main([str(content_root)]) == 0

    assert "stale" not in (content_root / "README.md").read_text(encoding="utf-8")
    assert "stale" not in (content_root / "CONTRIBUTING.md").read_text(encoding="utf-8")


def test_main_check_fails_without_writing_when_a_region_is_stale(content_root: Path) -> None:
    write(content_root / "README.md", region("loops"))
    write(content_root / "CONTRIBUTING.md", "# Contributing\n")

    assert main(["--check", str(content_root)]) == 1

    assert "stale" in (content_root / "README.md").read_text(encoding="utf-8")
