"""The content lint rules of the restructure, run through the loader.

The fixture tree is clean; each test plants one violation and expects exactly
that problem. The last test runs the rules against this repository once its
content is in the new layout.
"""

from pathlib import Path

import pytest

from oees_agents.content import load_content
from oees_agents.lint import lint_content

from conftest import write

REPO = Path(__file__).resolve().parents[1]


def problems(root: Path) -> list[str]:
    return [str(problem) for problem in lint_content(load_content(root))]


def test_the_fixture_tree_is_clean(content_root: Path) -> None:
    assert problems(content_root) == []


@pytest.mark.parametrize(
    ("path", "phrase"),
    [
        ("skills/plan/SKILL.md", "an internal tool for a handful of staff"),
        ("content/loops/tier-0-daily-health-scan.md", "AN INTERNAL TOOL FOR A SMALL TEAM"),
        ("content/subagents/core/implementer.md", "Assume an internal tool for a small team."),
    ],
)
def test_no_file_claims_the_project_is_a_throwaway(
    content_root: Path, path: str, phrase: str
) -> None:
    with (content_root / path).open("a") as handle:
        handle.write(f"\n{phrase}\n")

    assert problems(content_root) == [f"{path}: claims the project is a throwaway ({phrase!r})"]


def test_no_dangling_skill_import_in_a_command(content_root: Path) -> None:
    write(content_root / "commands/ship.md", "@../skills/ship/SKILL.md\n")

    assert problems(content_root) == [
        "commands/ship.md: imports @../skills/ship/SKILL.md, which is not a skill"
    ]


def test_no_dangling_skills_entry_in_a_subagent(content_root: Path) -> None:
    path = content_root / "content/subagents/extended/ui-reviewer.md"
    path.write_text(path.read_text().replace("  - reviewing", "  - reviewing\n  - designing"))

    assert problems(content_root) == [
        "content/subagents/extended/ui-reviewer.md: "
        "preloads skill 'designing', which does not exist"
    ]


def test_loops_have_no_duplicated_sections(content_root: Path) -> None:
    with (content_root / "content/loops/tier-1-increase-test-coverage.md").open("a") as handle:
        handle.write("\n## Steps\n\nAgain.\n")

    assert problems(content_root) == [
        "content/loops/tier-1-increase-test-coverage.md: repeats the heading '## Steps'"
    ]


@pytest.mark.parametrize("word", ["make check-fast", "Testcontainers", "HTMX", "tech lead"])
def test_subagents_contain_no_project_vocabulary(content_root: Path, word: str) -> None:
    with (content_root / "content/subagents/core/test-writer.md").open("a") as handle:
        handle.write(f"\nRun {word} first.\n")

    assert problems(content_root) == [
        f"content/subagents/core/test-writer.md: names project vocabulary {word!r}"
    ]


@pytest.mark.skipif(
    not (REPO / "content/conduct").is_dir(),
    reason="this repository's content is not in the restructured layout yet (Phase 1)",
)
def test_this_repositorys_content_is_clean() -> None:
    assert problems(REPO) == []
