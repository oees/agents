"""Regenerate `src/oees_agents/legacy_hashes.json` from this repository's git history.

Before the CLI, `scripts/init-repo.sh` copied files from this repository into
projects. This lists the sha256 of every version of every file it could have
copied, keyed by the path it was installed at, so `oees-agents init` can prove
a project's file came from here before deleting it. Only commits that still
ship `init-repo.sh` count, and only the history is read, never the working tree.

    uv run python scripts/generate_legacy_hashes.py            # rewrite the JSON
    uv run python scripts/generate_legacy_hashes.py --stdout   # print it instead
"""

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[1]
OUTPUT = REPO / "src/oees_agents/legacy_hashes.json"
INSTALLER = "scripts/init-repo.sh"
REVISIONS = ("HEAD", "main")
SOURCES = (
    "rules",
    "content/conduct",
    "content/defaults",
    "skills",
    "commands",
    "loops",
    ".cursor/rules",
    ".claude/settings.json",
)
COMMAND_REWRITE = b"sed 's|@skills/|@../skills/|g'"


def git(*args: str, stdin: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", "-C", str(REPO), *args], input=stdin, capture_output=True, check=True
    ).stdout


def installed_at(source: str) -> str | None:
    parts = PurePosixPath(source).parts
    match parts:
        case ("rules" | "commands" | "loops") as kind, name if name.endswith(".md"):
            return f".claude/{kind}/{name}"
        case "content", "conduct" | "defaults", name if name.endswith(".md"):
            return f".claude/rules/{name}"
        case "skills", skill, name if name.endswith(".md"):
            return f".claude/skills/{skill}/{name}"
        case ".cursor", "rules", name if name.endswith(".mdc"):
            return source
        case ".claude", "settings.json":
            return source
    return None


def revisions() -> list[str]:
    present = [rev for rev in REVISIONS if _resolves(rev)]
    return git("rev-list", *present).decode().split()


def _resolves(rev: str) -> bool:
    found = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    return found.returncode == 0


def installed_blobs(commit: str) -> Iterator[tuple[str, str, bool]]:
    """(installed path, blob id, rewritten by sed) for what init-repo.sh copied at `commit`."""
    tree = git("ls-tree", "-r", "-z", commit, "--", INSTALLER, *SOURCES).split(b"\0")
    entries = {}
    for entry in filter(None, tree):
        meta, path = entry.decode().split("\t", 1)
        mode, kind, blob = meta.split()
        if kind == "blob" and mode in ("100644", "100755"):
            entries[path] = blob
    if INSTALLER not in entries:
        return
    rewrites = COMMAND_REWRITE in read_blobs([entries[INSTALLER]])[entries[INSTALLER]]
    for path, blob in entries.items():
        target = installed_at(path)
        if target is not None:
            yield target, blob, rewrites and target.startswith(".claude/commands/")


def read_blobs(blobs: list[str]) -> dict[str, bytes]:
    output = git("cat-file", "--batch", stdin="".join(f"{blob}\n" for blob in blobs).encode())
    contents: dict[str, bytes] = {}
    offset = 0
    for blob in blobs:
        header_end = output.index(b"\n", offset)
        _, _, size = output[offset:header_end].decode().split()
        start = header_end + 1
        contents[blob] = output[start : start + int(size)]
        offset = start + int(size) + 1
    return contents


def generate() -> str:
    found = {entry for commit in revisions() for entry in installed_blobs(commit)}
    contents = read_blobs(sorted({blob for _, blob, _ in found}))
    table: dict[str, set[str]] = {}
    for target, blob, rewritten in found:
        data = contents[blob]
        if rewritten:
            data = data.replace(b"@skills/", b"@../skills/")
        table.setdefault(target, set()).add(hashlib.sha256(data).hexdigest())
    ordered = {path: sorted(hashes) for path, hashes in sorted(table.items())}
    return json.dumps(ordered, indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    parser.add_argument("--stdout", action="store_true", help="print instead of writing")
    arguments = parser.parse_args()
    table = generate()
    if arguments.stdout:
        sys.stdout.write(table)
    else:
        OUTPUT.write_text(table, encoding="utf-8")


if __name__ == "__main__":
    main()
