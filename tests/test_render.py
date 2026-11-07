import posixpath
import re
from dataclasses import replace
from pathlib import Path

import pytest

from oees_agents.blocks import splice
from oees_agents.content import load_content
from oees_agents.context import context_block
from oees_agents.manifest import Extras, Manifest, Project
from oees_agents.output import ManagedBlock, Output, RenderError, merge_outputs
from oees_agents.render import render

PROJECT = Project(
    name="octohub",
    description="B2B multi-tenant platform where partners and vendors sell energy products.",
    users="external partners, vendors, OEES operations",
    blast_radius="customer-facing",
    default_branch="main",
    check="make check",
    check_fast="make check-fast",
)


def manifest(**overrides: object) -> Manifest:
    base = Manifest(
        source="v1.0.0",
        targets=("claude",),
        project=PROJECT,
        defaults=("tdd", "git"),
        kits=("django-drf", "htmx-alpine"),
        extras=Extras(),
    )
    return replace(base, **overrides)  # type: ignore[arg-type]  # overrides are test inputs


def test_the_context_block_states_the_project(content_root: Path) -> None:
    block = context_block(manifest(), load_content(content_root))

    assert block == (
        "<!-- BEGIN OEES PROJECT CONTEXT -->\n"
        "## Project context\n"
        "**octohub**: B2B multi-tenant platform where partners and vendors sell energy products.\n"
        "Used by: external partners, vendors, OEES operations. Blast radius: customer-facing.\n"
        "Stack: django-drf, htmx-alpine. Default branch: main.\n"
        "Checks: `make check-fast` while working, `make check` before handing over.\n"
        "Calibrate every judgement call to this context. Never assume the code is a throwaway.\n"
        "<!-- END OEES PROJECT CONTEXT -->\n"
    )


def test_the_context_block_without_kits_says_no_kit(content_root: Path) -> None:
    block = context_block(manifest(kits=()), load_content(content_root))

    assert block is not None
    assert "Stack: no kit selected." in block


def test_there_is_no_context_block_without_a_project(content_root: Path) -> None:
    assert context_block(manifest(project=None), load_content(content_root)) is None


def test_context_values_are_collapsed_to_one_line(content_root: Path) -> None:
    project = replace(PROJECT, description="Line one.\n\n  Line two.")

    block = context_block(manifest(project=project), load_content(content_root))

    assert block is not None
    assert "**octohub**: Line one. Line two.\n" in block


@pytest.mark.parametrize("value", ["<!-- sneaky", "ends here -->"])
def test_context_values_cannot_contain_comment_markers(content_root: Path, value: str) -> None:
    project = replace(PROJECT, users=value)

    with pytest.raises(RenderError, match=r"project\.users"):
        context_block(manifest(project=project), load_content(content_root))


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"defaults": ("tdd", "yolo")}, "unknown default 'yolo'"),
        ({"kits": ("rails",)}, "unknown kit 'rails'"),
        ({"extras": Extras(loops=("tier-9",))}, "unknown loop 'tier-9'"),
    ],
)
def test_render_refuses_names_the_content_does_not_have(
    content_root: Path, overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(RenderError, match=message):
        render(manifest(**overrides), load_content(content_root))


def test_render_is_deterministic(content_root: Path) -> None:
    content = load_content(content_root)

    assert render(manifest(), content) == render(manifest(), content)


def test_merging_outputs_refuses_two_owners_for_one_path() -> None:
    one = Output(files={"a.md": b"1"})
    two = Output(blocks={"a.md": ManagedBlock(body="x", placement="top")})

    with pytest.raises(RenderError, match=r"a\.md"):
        merge_outputs([one, two])


def test_all_three_targets_render_together(content_root: Path) -> None:
    rendered = render(manifest(targets=("claude", "cursor", "codex")), load_content(content_root))

    assert {".claude/CLAUDE.md", "AGENTS.md"} <= set(rendered.blocks)
    assert ".cursor/rules/00-project-context.mdc" in rendered.files
    assert ".claude/settings.json" in rendered.files


def test_this_repositorys_content_renders_every_target_with_resolvable_imports() -> None:
    content = load_content(Path(__file__).resolve().parents[1])
    everything = manifest(
        targets=("claude", "cursor", "codex"),
        defaults=tuple(content.defaults),
        kits=tuple(content.kits),
        extras=Extras(subagents="extended", loops=tuple(content.loops)),
    )

    rendered = render(everything, content)

    paths = set(rendered.files)
    sources = {
        **{path: data.decode() for path, data in rendered.files.items() if path.endswith(".md")},
        ".claude/CLAUDE.md": rendered.blocks[".claude/CLAUDE.md"].body,
    }
    for path, text in sources.items():
        for target in re.findall(r"^@(\S+\.md)$", text, re.MULTILINE):
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
            assert resolved in paths, f"{path} imports {target}"
    agents_md = splice(None, rendered.blocks["AGENTS.md"])
    assert len(agents_md) < 32 * 1024
    assert all(
        data.startswith(b"---\ndescription: ")
        for path, data in rendered.files.items()
        if path.startswith(".cursor/")
    )
