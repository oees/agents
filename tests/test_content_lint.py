"""Lint the canonical content: skills, loops and subagents.

These tests guard the shape other tooling relies on (Claude Code only loads
`SKILL.md`, subagents preload skills by name) and keep project-specific or
misleading text out of content that every OEES project installs.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONTENT_DIRS = ("content", "skills", "loops", "subagents", "commands")
SKILL_DIRS = ("skills", "content/skills")
LOOP_DIRS = ("loops", "content/loops")
SUBAGENT_DIRS = ("subagents", "content/subagents")

# Built from parts so this file does not itself contain the phrases.
THROWAWAY_PHRASES = (
    "internal tool for a " + "handful of staff",
    "internal tool for a " + "small team",
)

# Words that tie a subagent to one project's tools or vocabulary. Matched
# case-sensitively: "DECIDED" is a project's status label, "decided" is prose.
PROJECT_VOCABULARY = (
    "make check-fast",
    "Testcontainers",
    "Squawk",
    "zizmor",
    "OpenTofu",
    "HTMX",
    "DECIDED",
    "DERIVED",
    "tech lead",
    "doctl",
    "import contracts",
)

SKILL_IMPORT = re.compile(r"@(\S*skills/\S+\.md)")


def markdown_files(*dirs: str) -> list[Path]:
    files: list[Path] = []
    for name in dirs:
        base = ROOT / name
        if base.is_dir():
            files.extend(sorted(base.rglob("*.md")))
    return files


def frontmatter(path: Path) -> dict[str, str | list[str]]:
    """Parse the flat YAML frontmatter used in this repo: scalars and lists."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return {}
    fields: dict[str, str | list[str]] = {}
    key = None
    for line in lines[1:]:
        if line == "---":
            return fields
        item = re.match(r"^\s+-\s+(.+)$", line)
        if item and key is not None:
            values = fields[key] if isinstance(fields[key], list) else []
            fields[key] = [*values, item.group(1).strip()]
            continue
        pair = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if pair:
            key = pair.group(1)
            fields[key] = pair.group(2).strip()
    return {}


def skill_names() -> set[str]:
    return {
        skill.parent.name
        for base in SKILL_DIRS
        if (ROOT / base).is_dir()
        for skill in (ROOT / base).glob("*/SKILL.md")
    }


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def test_no_file_claims_the_project_is_a_throwaway() -> None:
    offenders = [
        f"{relative(path)}: {phrase!r}"
        for path in markdown_files(*CONTENT_DIRS)
        for phrase in THROWAWAY_PHRASES
        if phrase in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_every_skill_is_a_SKILL_md() -> None:
    problems: list[str] = []
    for base in SKILL_DIRS:
        if not (ROOT / base).is_dir():
            continue
        for skill_dir in sorted(p for p in (ROOT / base).iterdir() if p.is_dir()):
            markdown = sorted(p.name for p in skill_dir.glob("*.md"))
            if markdown != ["SKILL.md"]:
                problems.append(f"{relative(skill_dir)} holds {markdown}, expected ['SKILL.md']")
                continue
            fields = frontmatter(skill_dir / "SKILL.md")
            if fields.get("name") != skill_dir.name:
                problems.append(f"{relative(skill_dir)}/SKILL.md name is {fields.get('name')!r}")
            if not fields.get("description"):
                problems.append(f"{relative(skill_dir)}/SKILL.md has no description")

    assert problems == []


def test_no_dangling_skill_references() -> None:
    known_skills = skill_names()
    dangling: list[str] = []
    for path in markdown_files(*CONTENT_DIRS):
        for target in SKILL_IMPORT.findall(path.read_text(encoding="utf-8")):
            if not (path.parent / target).is_file():
                dangling.append(f"{relative(path)} imports @{target}")
    for path in markdown_files(*SUBAGENT_DIRS):
        preloaded = frontmatter(path).get("skills", [])
        for skill in preloaded if isinstance(preloaded, list) else [preloaded]:
            if skill not in known_skills:
                dangling.append(f"{relative(path)} preloads unknown skill {skill!r}")

    assert dangling == []


def test_loops_have_no_duplicated_sections() -> None:
    duplicated: list[str] = []
    for path in markdown_files(*LOOP_DIRS):
        headings = re.findall(r"^## .+$", path.read_text(encoding="utf-8"), re.MULTILINE)
        repeated = sorted({h for h in headings if headings.count(h) > 1})
        duplicated.extend(f"{relative(path)}: {heading}" for heading in repeated)

    assert duplicated == []


def test_subagents_contain_no_project_vocabulary() -> None:
    found = [
        f"{relative(path)}: {word!r}"
        for path in markdown_files(*SUBAGENT_DIRS)
        for word in PROJECT_VOCABULARY
        if word in path.read_text(encoding="utf-8")
    ]

    assert found == []
