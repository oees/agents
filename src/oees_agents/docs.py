"""Fill the generated tables in README.md and CONTRIBUTING.md from the content.

A region is everything between a pair of marker lines:

    <!-- BEGIN GENERATED: kits -->
    ...
    <!-- END GENERATED: kits -->

Only the lines between the markers are replaced; everything else in the file is
kept byte for byte. Unknown, unclosed, nested or repeated markers are refused.
Run it with `make docs`; `make check` fails when a region is stale.
"""

import argparse
import logging
import re
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from types import MappingProxyType

from oees_agents.content import Content, ContentError, Document, load_content
from oees_agents.log import configure

DOC_FILES = ("README.md", "CONTRIBUTING.md")

_MARKER = re.compile(r"^<!-- (BEGIN|END) GENERATED: ([a-z-]+) -->$")

logger = logging.getLogger(__name__)


class DocsError(ValueError):
    """A doc file's generated regions cannot be filled safely."""


Row = tuple[str, ...]


def _conduct(content: Content) -> tuple[Row, Iterable[Row]]:
    return ("Rule", "What it covers"), _named(content.conduct.items())


def _defaults(content: Content) -> tuple[Row, Iterable[Row]]:
    return ("Rule", "What it covers"), _named(content.defaults.items())


def _skills(content: Content) -> tuple[Row, Iterable[Row]]:
    return ("Skill", "What it does"), _named(
        (name, skill.document) for name, skill in content.skills.items()
    )


def _kits(content: Content) -> tuple[Row, Iterable[Row]]:
    return ("Kit", "What it is for"), _named(
        (name, kit.document) for name, kit in content.kits.items()
    )


def _subagents(content: Content) -> tuple[Row, Iterable[Row]]:
    rows = (
        (f"`{name}`", tier, document.summary)
        for tier, documents in content.subagents.items()
        for name, document in documents.items()
    )
    return ("Subagent", "Set", "What it does"), rows


def _commands(content: Content) -> tuple[Row, Iterable[Row]]:
    rows = ((f"`/{name}`", document.summary) for name, document in content.commands.items())
    return ("Command", "What it does"), rows


def _loops(content: Content) -> tuple[Row, Iterable[Row]]:
    return ("Loop", "What it does"), _named(content.loops.items())


def _named(documents: Iterable[tuple[str, Document]]) -> Iterable[Row]:
    return ((f"`{name}`", document.summary) for name, document in documents)


REGIONS: Mapping[str, Callable[[Content], tuple[Row, Iterable[Row]]]] = MappingProxyType(
    {
        "conduct": _conduct,
        "defaults": _defaults,
        "skills": _skills,
        "kits": _kits,
        "subagents": _subagents,
        "commands": _commands,
        "loops": _loops,
    }
)


def render_region(name: str, content: Content) -> str:
    """The markdown table for one region, without a trailing newline."""
    if name not in REGIONS:
        raise DocsError(f"unknown generated region '{name}'")
    header, rows = REGIONS[name](content)
    lines = [_row(header), "|" + "---|" * len(header)]
    lines.extend(_row(row) for row in rows)
    return "\n".join(lines)


def _row(cells: Row) -> str:
    return "| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |"


def fill(text: str, content: Content) -> str:
    """`text` with every generated region re-rendered from `content`."""
    output: list[str] = []
    open_region: str | None = None
    seen: set[str] = set()
    for line in text.splitlines(keepends=True):
        match = _MARKER.match(line.rstrip("\r\n"))
        if match is None:
            if open_region is None:
                output.append(line)
            continue
        kind, name = match.groups()
        if kind == "BEGIN":
            if open_region is not None:
                raise DocsError(f"generated region {name} starts inside {open_region}")
            if name in seen:
                raise DocsError(f"generated region {name} appears more than once")
            newline = line[len(line.rstrip("\r\n")) :] or "\n"
            output.append(line)
            output.append(render_region(name, content).replace("\n", newline) + newline)
            open_region = name
            seen.add(name)
        else:
            if open_region != name:
                raise DocsError(f"END GENERATED: {name} without a BEGIN")
            output.append(line)
            open_region = None
    if open_region is not None:
        raise DocsError(f"generated region {open_region} is not closed")
    return "".join(output)


def stale_docs(root: Path, content: Content) -> list[str]:
    """The doc files under `root` whose generated regions differ from `content`."""
    return [name for name, current, filled in _docs(root, content) if current != filled]


def write_docs(root: Path, content: Content) -> list[str]:
    """Rewrite the stale doc files under `root`; returns the ones it changed."""
    changed: list[str] = []
    for name, current, filled in _docs(root, content):
        if current != filled:
            (root / name).write_bytes(filled.encode("utf-8"))
            logger.info("regenerated doc tables", extra={"path": name})
            changed.append(name)
    return changed


def _docs(root: Path, content: Content) -> Iterable[tuple[str, str, str]]:
    for name in DOC_FILES:
        path = root / name
        if not path.is_file():
            raise DocsError(f"missing doc file: {name}")
        current = path.read_bytes().decode("utf-8")
        try:
            filled = fill(current, content)
        except DocsError as error:
            raise DocsError(f"{name}: {error}") from error
        yield name, current, filled


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m oees_agents.docs",
        description="Fill the generated tables in README.md and CONTRIBUTING.md.",
    )
    parser.add_argument("root", nargs="?", default=".", type=Path, help="agents checkout")
    parser.add_argument("--check", action="store_true", help="fail if a table is stale")
    args = parser.parse_args(argv)
    configure(verbose=False)
    try:
        content = load_content(args.root)
        if args.check:
            stale = stale_docs(args.root, content)
            for name in stale:
                print(f"stale generated tables: {name} (run `make docs`)", file=sys.stderr)
            return 1 if stale else 0
        for name in write_docs(args.root, content):
            print(f"regenerated {name}")
    except (ContentError, DocsError) as error:
        logger.error("docs generation failed", extra={"error": str(error)})
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
