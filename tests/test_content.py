import shutil
from pathlib import Path

import pytest

from oees_agents.content import ContentError, load_content, parse_frontmatter

from conftest import (
    CONDUCT,
    CORE_SUBAGENTS,
    DEFAULTS,
    EXTENDED_SUBAGENTS,
    KITS,
    LOOPS,
    SKILLS,
    write,
)

REPO = Path(__file__).resolve().parents[1]


def test_every_expected_tier_skill_kit_subagent_and_loop_is_found(content_root: Path) -> None:
    content = load_content(content_root)

    assert set(content.conduct) == set(CONDUCT)
    assert set(content.defaults) == set(DEFAULTS)
    assert set(content.skills) == set(SKILLS)
    assert set(content.kits) == set(KITS)
    assert set(content.subagents["core"]) == set(CORE_SUBAGENTS)
    assert set(content.subagents["extended"]) == set(EXTENDED_SUBAGENTS)
    assert set(content.loops) == set(LOOPS)
    assert set(content.commands) == {"commit", "code-review", "plan", "pr-tidy", "test", "shipped"}


def test_frontmatter_is_parsed_into_meta_and_body(content_root: Path) -> None:
    content = load_content(content_root)

    agent = content.subagents["core"]["implementer"]
    assert agent.meta["description"] == "Use for implementer: in a fresh context."
    assert agent.meta["tools"] == "Read, Grep, Glob"
    assert agent.meta["skills"] == ("reviewing",)
    assert agent.body == "\n# implementer\n"
    assert agent.source == "content/subagents/core/implementer.md"
    assert agent.raw == (content_root / agent.source).read_bytes()


def test_a_document_without_frontmatter_has_empty_meta(content_root: Path) -> None:
    loop = load_content(content_root).loops["tier-0-daily-health-scan"]

    assert loop.meta == {}
    assert loop.body.startswith("# tier-0-daily-health-scan")


def test_a_skill_carries_every_file_in_its_directory(content_root: Path) -> None:
    kit = load_content(content_root).kits["fastapi"]

    assert set(kit.files) == {"SKILL.md", "templates/Makefile"}
    assert kit.files["templates/Makefile"] == b"check:\n\ttrue\n"
    assert kit.description == "The fastapi stack kit."


def test_a_skill_directory_without_skill_md_raises(content_root: Path) -> None:
    (content_root / "skills/commit/SKILL.md").rename(content_root / "skills/commit/commit.md")

    with pytest.raises(ContentError, match=r"skills/commit.*SKILL\.md"):
        load_content(content_root)


def test_a_kit_directory_without_skill_md_raises(content_root: Path) -> None:
    (content_root / "content/kits/fastapi/SKILL.md").unlink()

    with pytest.raises(ContentError, match=r"content/kits/fastapi"):
        load_content(content_root)


@pytest.mark.parametrize("key", ["name", "description"])
def test_a_skill_without_name_or_description_raises(content_root: Path, key: str) -> None:
    path = content_root / "skills/plan/SKILL.md"
    path.write_text(
        "\n".join(line for line in path.read_text().splitlines() if not line.startswith(key)),
    )

    with pytest.raises(ContentError, match=key):
        load_content(content_root)


def test_a_skill_named_differently_from_its_directory_raises(content_root: Path) -> None:
    path = content_root / "skills/plan/SKILL.md"
    path.write_text(path.read_text().replace("name: plan", "name: planning"))

    with pytest.raises(ContentError, match="planning"):
        load_content(content_root)


def test_skills_may_also_live_under_content_skills(content_root: Path) -> None:
    shutil.move(content_root / "skills/shipped", content_root / "content/skills/shipped")

    content = load_content(content_root)

    assert content.skills["shipped"].source == "content/skills/shipped/SKILL.md"


def test_a_skill_defined_twice_raises(content_root: Path) -> None:
    shutil.copytree(content_root / "skills/shipped", content_root / "content/skills/shipped")

    with pytest.raises(ContentError, match=r"shipped.*more than once"):
        load_content(content_root)


def test_loops_and_commands_may_live_at_the_repository_root(content_root: Path) -> None:
    shutil.move(content_root / "content/loops", content_root / "loops")

    assert set(load_content(content_root).loops) == set(LOOPS)


def test_a_readme_in_a_document_directory_is_not_a_document(content_root: Path) -> None:
    write(content_root / "content/loops/README.md", "# Loops\n\nHow to run one.\n")

    assert set(load_content(content_root).loops) == set(LOOPS)


def test_a_missing_tier_directory_raises(content_root: Path) -> None:
    shutil.rmtree(content_root / "content/conduct")

    with pytest.raises(ContentError, match="content/conduct"):
        load_content(content_root)


def test_crlf_frontmatter_is_parsed() -> None:
    meta, body = parse_frontmatter("---\r\nname: x\r\ndescription: y\r\n---\r\n\r\n# X\r\n")

    assert meta == {"name": "x", "description": "y"}
    assert body == "\n# X\n"


def test_quoted_values_and_inline_lists_are_parsed() -> None:
    meta, _ = parse_frontmatter(
        '---\na: "say \\"hi\\": now"\nb: \'single\'\nc: ["**/*.py", \'**/*.pyi\']\n---\n'
    )

    assert meta == {"a": 'say "hi": now', "b": "single", "c": ("**/*.py", "**/*.pyi")}


def test_unterminated_frontmatter_raises() -> None:
    with pytest.raises(ContentError, match="unterminated"):
        parse_frontmatter("---\nname: x\n")


def test_unparseable_frontmatter_lines_raise_with_the_line() -> None:
    with pytest.raises(ContentError, match="not a key"):
        parse_frontmatter("---\nname x\n---\n")


def test_non_markdown_files_in_tier_directories_are_ignored(content_root: Path) -> None:
    write(content_root / "content/defaults/README.txt", "notes")

    assert "README" not in load_content(content_root).defaults


def test_hidden_files_in_a_skill_directory_are_not_carried(content_root: Path) -> None:
    write(content_root / "content/kits/fastapi/.DS_Store", "junk")

    assert ".DS_Store" not in load_content(content_root).kits["fastapi"].files


@pytest.mark.parametrize(
    "relative",
    [
        "templates/.github/workflows/ci.yml",
        "templates/.do/app.yaml",
        "templates/.dockerignore",
        "templates/.env.example",
        "templates/static/.gitkeep",
    ],
)
def test_dotfiles_under_templates_are_carried(content_root: Path, relative: str) -> None:
    write(content_root / "content/kits/fastapi" / relative, "kept\n")

    assert load_content(content_root).kits["fastapi"].files[relative] == b"kept\n"


@pytest.mark.parametrize(
    "relative",
    [
        "templates/.DS_Store",
        "templates/.git/HEAD",
        "templates/app/__pycache__/main.cpython-313.pyc",
        "templates/app/main.pyc",
        "templates/.ruff_cache/0.13/cache",
        "templates/.mypy_cache/3.13/app.json",
        "templates/.pytest_cache/v/cache/nodeids",
        "templates/.venv/bin/python",
    ],
)
def test_tool_and_os_junk_under_templates_is_not_carried(content_root: Path, relative: str) -> None:
    write(content_root / "content/kits/fastapi" / relative, "junk")

    assert relative not in load_content(content_root).kits["fastapi"].files


def test_pycache_outside_templates_is_not_carried(content_root: Path) -> None:
    write(content_root / "skills/commit/__pycache__/x.cpython-313.pyc", "junk")

    assert load_content(content_root).skills["commit"].files.keys() == {"SKILL.md"}


def test_a_tree_without_kits_has_no_kits(content_root: Path) -> None:
    shutil.rmtree(content_root / "content/kits")

    assert load_content(content_root).kits == {}


def test_this_repositorys_content_has_every_tier_skill_subagent_and_loop() -> None:
    content = load_content(REPO)

    assert set(content.conduct) == set(CONDUCT)
    assert set(content.defaults) == set(DEFAULTS)
    assert set(content.skills) == set(SKILLS)
    assert set(content.subagents["core"]) == set(CORE_SUBAGENTS)
    assert set(content.subagents["extended"]) == set(EXTENDED_SUBAGENTS)
    assert set(content.commands) == {"commit", "code-review", "plan", "pr-tidy", "test", "shipped"}
    assert content.loops
