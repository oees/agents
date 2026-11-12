"""Load the canonical content: tiers, skills, kits, subagents, loops and commands.

The layout is the one the restructure plan targets:

    content/conduct/*.md              always on
    content/defaults/*.md             on unless a project opts out
    content/kits/<name>/SKILL.md      opt-in stack kits, with templates/
    content/subagents/{core,extended}/*.md
    skills/<name>/SKILL.md            (or content/skills/<name>/SKILL.md)
    loops/*.md, commands/*.md         (or under content/)
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType

SUBAGENT_TIERS = ("core", "extended")
CONTEXT_TEMPLATE = "content/blocks/project-context.md"
TEMPLATES_DIR = "templates"
# Tool caches and OS litter a skill directory can pick up; never carried.
JUNK_NAMES = frozenset(
    {".DS_Store", ".git", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv"}
)
JUNK_SUFFIXES = (".pyc",)
# A README in a content directory documents the directory; it is not content.
README_NAME = "README.md"

Meta = Mapping[str, str | tuple[str, ...]]


class ContentError(ValueError):
    """The content tree is missing something the installer depends on."""


@dataclass(frozen=True)
class Document:
    name: str
    source: str
    meta: Meta
    body: str
    raw: bytes

    @property
    def description(self) -> str:
        value = self.meta.get("description", "")
        return value if isinstance(value, str) else ""

    @property
    def summary(self) -> str:
        """One line: the description, else the first `# ` heading."""
        if self.description:
            return " ".join(self.description.split())
        for line in self.body.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return ""


@dataclass(frozen=True)
class Skill:
    name: str
    document: Document
    files: Mapping[str, bytes]

    @property
    def source(self) -> str:
        return self.document.source

    @property
    def description(self) -> str:
        return self.document.description


@dataclass(frozen=True)
class Content:
    root: Path
    conduct: Mapping[str, Document]
    defaults: Mapping[str, Document]
    skills: Mapping[str, Skill]
    kits: Mapping[str, Skill]
    subagents: Mapping[str, Mapping[str, Document]]
    loops: Mapping[str, Document]
    commands: Mapping[str, Document]
    context_template: str


def load_content(root: Path) -> Content:
    root = root.resolve()
    return Content(
        root=root,
        conduct=_documents(root, ("content/conduct",)),
        defaults=_documents(root, ("content/defaults",)),
        skills=_skills(root, ("content/skills", "skills")),
        kits=_skills(root, ("content/kits",), optional=True),
        subagents=MappingProxyType(
            {
                tier: _documents(
                    root, (f"content/subagents/{tier}",), required=("name", "description")
                )
                for tier in SUBAGENT_TIERS
            }
        ),
        loops=_documents(root, ("content/loops", "loops")),
        commands=_documents(root, ("content/commands", "commands")),
        context_template=_text(root, CONTEXT_TEMPLATE),
    )


def parse_frontmatter(text: str) -> tuple[Meta, str]:
    """Split simple YAML frontmatter (scalars, quoted strings, lists) from the body."""
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return {}, text
    lines = text.split("\n")
    try:
        close = lines.index("---", 1)
    except ValueError:
        raise ContentError("unterminated frontmatter: no closing '---'") from None
    meta: dict[str, str | tuple[str, ...]] = {}
    list_key: str | None = None
    for number, line in enumerate(lines[1:close], start=2):
        stripped = line.strip()
        if not stripped:
            continue
        if list_key is not None and stripped.startswith("- "):
            meta[list_key] = (*meta[list_key], _scalar(stripped[2:]))
            continue
        key, separator, value = line.partition(":")
        if not separator or not key or key != key.strip() or " " in key:
            raise ContentError(f"frontmatter line {number} is not a key: {line!r}")
        value = value.strip()
        list_key = None if value else key
        if not value:
            meta[key] = ()
        elif value.startswith("["):
            meta[key] = _list(value)
        else:
            meta[key] = _scalar(value)
    return meta, "\n".join(lines[close + 1 :])


def _scalar(value: str) -> str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as error:
            raise ContentError(f"invalid quoted value {value!r}") from error
        return str(decoded)
    if value.startswith("'") and value.endswith("'") and len(value) >= 2:
        return value[1:-1].replace("''", "'")
    return value


def _list(value: str) -> tuple[str, ...]:
    if not value.endswith("]"):
        raise ContentError(f"invalid inline list {value!r}")
    inner = value[1:-1].strip()
    return tuple(_scalar(item) for item in inner.split(",")) if inner else ()


def _load_document(root: Path, path: Path, required: tuple[str, ...] = ()) -> Document:
    source = path.relative_to(root).as_posix()
    raw = path.read_bytes()
    try:
        meta, body = parse_frontmatter(raw.decode("utf-8"))
    except (ContentError, UnicodeDecodeError) as error:
        raise ContentError(f"{source}: {error}") from error
    for key in required:
        if not isinstance(meta.get(key), str) or not meta[key]:
            raise ContentError(f"{source}: frontmatter needs a '{key}'")
    return Document(name=path.stem, source=source, meta=meta, body=body, raw=raw)


def _text(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file():
        raise ContentError(f"missing content file: {relative}")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _existing(root: Path, candidates: tuple[str, ...], optional: bool = False) -> list[Path]:
    found = [root / candidate for candidate in candidates if (root / candidate).is_dir()]
    if not found and not optional:
        raise ContentError(f"missing content directory: {' or '.join(candidates)}")
    return found


def _documents(
    root: Path, candidates: tuple[str, ...], required: tuple[str, ...] = ()
) -> Mapping[str, Document]:
    documents: dict[str, Document] = {}
    for directory in _existing(root, candidates):
        for path in sorted(directory.glob("*.md")):
            if path.name == README_NAME:
                continue
            if path.stem in documents:
                raise ContentError(f"{path.stem} is defined more than once")
            documents[path.stem] = _load_document(root, path, required)
    return MappingProxyType(documents)


def _skills(root: Path, candidates: tuple[str, ...], optional: bool = False) -> Mapping[str, Skill]:
    skills: dict[str, Skill] = {}
    for directory in _existing(root, candidates, optional):
        for skill_dir in sorted(path for path in directory.iterdir() if path.is_dir()):
            skill = _load_skill(root, skill_dir)
            if skill.name in skills:
                raise ContentError(f"{skill.name} is defined more than once")
            skills[skill.name] = skill
    return MappingProxyType(skills)


def _load_skill(root: Path, directory: Path) -> Skill:
    relative = directory.relative_to(root).as_posix()
    skill_md = directory / "SKILL.md"
    if not skill_md.is_file():
        raise ContentError(f"{relative} has no SKILL.md")
    document = _load_document(root, skill_md, required=("name", "description"))
    if document.meta["name"] != directory.name:
        raise ContentError(
            f"{document.source}: name {document.meta['name']!r} does not match its directory"
        )
    files = {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and _carried(path.relative_to(directory).parts)
    }
    return Skill(
        name=directory.name,
        document=replace(document, name=directory.name),
        files=MappingProxyType(files),
    )


def _carried(parts: tuple[str, ...]) -> bool:
    """Templates mirror a project root, so their dotfiles (.github/, .env.example) are kept."""
    if any(part in JUNK_NAMES for part in parts) or parts[-1].endswith(JUNK_SUFFIXES):
        return False
    return parts[0] == TEMPLATES_DIR or not any(part.startswith(".") for part in parts)
