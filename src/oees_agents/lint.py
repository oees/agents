"""Content rules the restructure introduced, checked against loaded content."""

import re
from collections.abc import Iterator
from dataclasses import dataclass

from oees_agents.content import Content, Document

THROWAWAY_PHRASES = ("internal tool for a handful of staff", "internal tool for a small team")
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
_SKILL_IMPORT = re.compile(r"@\.\./skills/([^/\s]+)/SKILL\.md")
_ANY_SKILL_IMPORT = re.compile(r"@\.\./skills/\S+")


@dataclass(frozen=True)
class Problem:
    source: str
    message: str

    def __str__(self) -> str:
        return f"{self.source}: {self.message}"


def lint_content(content: Content) -> list[Problem]:
    return sorted(
        [
            *_throwaway_claims(content),
            *_dangling_skill_references(content),
            *_duplicated_loop_sections(content),
            *_subagent_vocabulary(content),
        ],
        key=lambda problem: (problem.source, problem.message),
    )


def _all_documents(content: Content) -> Iterator[Document]:
    yield from content.conduct.values()
    yield from content.defaults.values()
    for skill in (*content.skills.values(), *content.kits.values()):
        yield skill.document
    for tier in content.subagents.values():
        yield from tier.values()
    yield from content.loops.values()
    yield from content.commands.values()


def _throwaway_claims(content: Content) -> Iterator[Problem]:
    for document in _all_documents(content):
        lowered = document.body.lower()
        for phrase in THROWAWAY_PHRASES:
            index = lowered.find(phrase)
            if index != -1:
                start = lowered.rfind("\n", 0, index) + 1
                end = lowered.find("\n", index)
                line = document.body[start : end if end != -1 else None].strip()
                yield Problem(document.source, f"claims the project is a throwaway ({line!r})")


def _dangling_skill_references(content: Content) -> Iterator[Problem]:
    for command in content.commands.values():
        for match in _ANY_SKILL_IMPORT.finditer(command.body):
            named = _SKILL_IMPORT.fullmatch(match.group(0))
            if named is None or named.group(1) not in content.skills:
                yield Problem(command.source, f"imports {match.group(0)}, which is not a skill")
    for tier in content.subagents.values():
        for agent in tier.values():
            preloaded = agent.meta.get("skills", ())
            for name in (preloaded,) if isinstance(preloaded, str) else preloaded:
                if name not in content.skills:
                    yield Problem(agent.source, f"preloads skill {name!r}, which does not exist")


def _duplicated_loop_sections(content: Content) -> Iterator[Problem]:
    for loop in content.loops.values():
        seen: set[str] = set()
        for line in loop.body.splitlines():
            if line.startswith("## "):
                heading = line.rstrip()
                if heading in seen:
                    yield Problem(loop.source, f"repeats the heading {heading!r}")
                seen.add(heading)


def _subagent_vocabulary(content: Content) -> Iterator[Problem]:
    for tier in content.subagents.values():
        for agent in tier.values():
            text = agent.raw.decode("utf-8")
            for word in PROJECT_VOCABULARY:
                if word in text:
                    yield Problem(agent.source, f"names project vocabulary {word!r}")
