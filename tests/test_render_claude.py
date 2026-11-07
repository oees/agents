import json
import posixpath
import re
from dataclasses import replace
from pathlib import Path

import pytest

from oees_agents import profiles
from oees_agents.blocks import BEGIN, END, splice
from oees_agents.content import Content, load_content
from oees_agents.manifest import Extras, Manifest, Project
from oees_agents.output import Output
from oees_agents.targets.claude import render

from conftest import (
    COMMAND_SKILLS,
    CONDUCT,
    CORE_SUBAGENTS,
    DEFAULTS,
    EXTENDED_SUBAGENTS,
    KITS,
    LOOPS,
    PATTERN_SKILLS,
)

PROJECT = Project(
    name="octohub",
    description="B2B multi-tenant platform where partners and vendors sell energy products.",
    users="external partners, vendors, OEES operations",
    blast_radius="customer-facing",
    default_branch="main",
    check="make check",
    check_fast="make check-fast",
)
CONTEXT_BEGIN = "<!-- BEGIN OEES PROJECT CONTEXT -->"
DENIED = (
    "Bash(git push*)",
    "Bash(git push --force*)",
    "Bash(git reset --hard*)",
    "Bash(git rebase -i*)",
    "Bash(git rebase --interactive*)",
    "Bash(git filter-branch*)",
)
PYTHON_ALLOWS = ("Bash(uv*)", "Bash(pytest*)", "Bash(ruff*)", "Bash(mypy*)")
IMPORT = re.compile(r"^@(\S+\.md)$", re.MULTILINE)


def manifest(**overrides: object) -> Manifest:
    base = Manifest(
        source="v1.0.0",
        targets=("claude",),
        project=PROJECT,
        defaults=DEFAULTS,
        kits=("django-drf", "htmx-alpine"),
        extras=Extras(),
    )
    return replace(base, **overrides)  # type: ignore[arg-type]  # overrides are test inputs


@pytest.fixture
def content(content_root: Path) -> Content:
    return load_content(content_root)


def claude_block(output: Output) -> str:
    block = output.blocks[".claude/CLAUDE.md"]
    assert block.placement == "top"
    return block.body


def under(output: Output, prefix: str) -> set[str]:
    return {path for path in output.paths if path.startswith(prefix)}


def settings(output: Output) -> dict[str, dict[str, list[str]]]:
    data: dict[str, dict[str, list[str]]] = json.loads(output.files[".claude/settings.json"])
    return data


def test_claude_md_block_starts_with_context_then_imports_conduct_and_defaults(
    content: Content,
) -> None:
    body = claude_block(render(manifest(defaults=("tdd", "git")), content))

    assert body.startswith(CONTEXT_BEGIN)
    assert IMPORT.findall(body) == [
        "rules/conduct.md",
        "rules/data-protection.md",
        "rules/secrets.md",
        "rules/tdd.md",
        "rules/git.md",
    ]
    assert "## Shared engineering rules\n" in body
    assert "run `oees-agents update`" in body


def test_rules_hold_the_raw_documents_for_conduct_and_enabled_defaults(content: Content) -> None:
    output = render(manifest(), content)

    assert under(output, ".claude/rules/") == {
        f".claude/rules/{name}.md" for name in (*CONDUCT, *DEFAULTS)
    }
    assert output.files[".claude/rules/tdd.md"] == content.defaults["tdd"].raw


def test_an_opted_out_default_has_no_rule_file_and_no_import(content: Content) -> None:
    output = render(manifest(defaults=tuple(d for d in DEFAULTS if d != "migrations")), content)

    assert ".claude/rules/migrations.md" not in output.paths
    assert "@rules/migrations.md" not in claude_block(output)


def test_the_context_block_appears_once_after_two_renders(content: Content) -> None:
    block = render(manifest(), content).blocks[".claude/CLAUDE.md"]

    twice = splice(splice(b"# Project\n", block), block).decode()

    assert twice.count(CONTEXT_BEGIN) == 1
    assert twice.count(BEGIN) == 1


def test_project_text_around_the_managed_block_survives_byte_for_byte(content: Content) -> None:
    block = render(manifest(), content).blocks[".claude/CLAUDE.md"]
    before = b"# Octohub\n\nLocal notes before.\n\n"
    after = b"\n## Local\n\nKeep  this   spacing.\n"
    existing = before + f"{BEGIN}\n\nold rules\n\n{END}\n".encode() + after

    result = splice(existing, block)

    assert result.startswith(before)
    assert result.endswith(after)
    assert b"old rules" not in result


def test_a_claude_md_without_markers_keeps_its_bytes_under_the_block(content: Content) -> None:
    block = render(manifest(), content).blocks[".claude/CLAUDE.md"]
    existing = b"# Octohub\n\nOur own instructions.\n"

    result = splice(existing, block)

    assert result.startswith(BEGIN.encode())
    assert result.endswith(existing)


def test_settings_deny_destructive_git_and_never_rm_or_hooks(content: Content) -> None:
    data = settings(render(manifest(), content))

    assert set(data) == {"permissions"}
    assert data["permissions"]["deny"] == list(DENIED)
    entries = [*data["permissions"]["allow"], *data["permissions"]["deny"]]
    assert not [entry for entry in entries if re.search(r"\brm\b", entry)]


def test_settings_are_formatted_json_with_a_trailing_newline(content: Content) -> None:
    raw = render(manifest(), content).files[".claude/settings.json"]

    assert raw == (json.dumps(json.loads(raw), indent=2) + "\n").encode()


def test_settings_allow_the_project_checks(content: Content) -> None:
    allow = settings(render(manifest(), content))["permissions"]["allow"]

    assert "Bash(make check*)" in allow
    assert "Bash(make check-fast*)" in allow
    assert "Bash(git status*)" in allow


def test_a_python_kit_allows_its_toolchain(content: Content) -> None:
    allow = settings(render(manifest(kits=("django-drf", "fastapi")), content))["permissions"][
        "allow"
    ]

    assert set(PYTHON_ALLOWS) <= set(allow)
    assert len(allow) == len(set(allow))


def test_a_kitless_manifest_allows_no_toolchain(content: Content) -> None:
    allow = settings(render(manifest(kits=()), content))["permissions"]["allow"]

    assert not set(PYTHON_ALLOWS) & set(allow)
    assert "Bash(tsc*)" not in allow


def test_a_typescript_kit_allows_npm_tsc_and_eslint(
    content: Content, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(profiles.KIT_TOOLCHAINS, "htmx-alpine", ("typescript",))

    allow = settings(render(manifest(kits=("htmx-alpine",)), content))["permissions"]["allow"]

    assert {"Bash(npm run lint*)", "Bash(tsc*)", "Bash(eslint*)"} <= set(allow)
    assert "Bash(pytest*)" not in allow


def test_no_subagents_means_no_agents_and_no_reviewing_skill(content: Content) -> None:
    output = render(manifest(extras=Extras(subagents="none")), content)

    assert not under(output, ".claude/agents/")
    assert not under(output, ".claude/skills/reviewing/")


def test_core_subagents_install_the_core_six_and_reviewing(content: Content) -> None:
    output = render(manifest(extras=Extras(subagents="core")), content)

    assert under(output, ".claude/agents/") == {
        f".claude/agents/{name}.md" for name in CORE_SUBAGENTS
    }
    assert ".claude/skills/reviewing/SKILL.md" in output.paths


def test_extended_subagents_install_all_twelve(content: Content) -> None:
    output = render(manifest(extras=Extras(subagents="extended")), content)

    assert under(output, ".claude/agents/") == {
        f".claude/agents/{name}.md" for name in (*CORE_SUBAGENTS, *EXTENDED_SUBAGENTS)
    }
    assert (
        output.files[".claude/agents/ui-reviewer.md"]
        == content.subagents["extended"]["ui-reviewer"].raw
    )


def test_commands_install_with_their_skills(content: Content) -> None:
    output = render(manifest(), content)

    assert under(output, ".claude/commands/") == {
        f".claude/commands/{name}.md" for name in COMMAND_SKILLS
    }
    for name in (*COMMAND_SKILLS, *PATTERN_SKILLS):
        assert f".claude/skills/{name}/SKILL.md" in output.paths


def test_commands_off_installs_no_commands(content: Content) -> None:
    output = render(manifest(extras=Extras(commands=False)), content)

    assert not under(output, ".claude/commands/")


def test_kit_templates_land_under_the_kit_skill(content: Content) -> None:
    output = render(manifest(kits=("fastapi",)), content)

    assert (
        output.files[".claude/skills/fastapi/templates/Makefile"]
        == (content.kits["fastapi"].files["templates/Makefile"])
    )
    assert ".claude/skills/fastapi/SKILL.md" in output.paths
    for disabled in KITS:
        if disabled != "fastapi":
            assert not [path for path in output.paths if f"/{disabled}/" in path]


def test_only_selected_loops_install(content: Content) -> None:
    output = render(manifest(extras=Extras(loops=(LOOPS[1],))), content)

    assert under(output, ".claude/loops/") == {f".claude/loops/{LOOPS[1]}.md"}


def test_every_import_resolves_to_a_rendered_path(content: Content) -> None:
    output = render(manifest(), content)
    importers = {path: data.decode() for path, data in output.files.items()}
    importers[".claude/CLAUDE.md"] = claude_block(output)
    rendered = output.paths

    imports = [
        (path, target)
        for path, text in importers.items()
        if path.startswith(".claude/commands/") or path == ".claude/CLAUDE.md"
        for target in IMPORT.findall(text)
    ]

    assert len(imports) == len(CONDUCT) + len(DEFAULTS) + len(COMMAND_SKILLS)
    for path, target in imports:
        assert posixpath.normpath(posixpath.join(posixpath.dirname(path), target)) in rendered


def test_without_a_project_there_is_no_context_block_and_no_check_allows(
    content: Content,
) -> None:
    output = render(manifest(project=None), content)

    body = claude_block(output)
    assert CONTEXT_BEGIN not in body
    assert body.startswith("## Shared engineering rules")
    assert not any("make check" in entry for entry in settings(output)["permissions"]["allow"])


def test_files_are_sorted_by_path(content: Content) -> None:
    output = render(manifest(), content)

    assert list(output.files) == sorted(output.files)


def test_a_blank_check_command_never_allows_every_command(content: Content) -> None:
    project = replace(PROJECT, check="make check", check_fast="  ")

    allow = settings(render(manifest(project=project), content))["permissions"]["allow"]

    assert "Bash(*)" not in allow
    assert not [entry for entry in allow if entry.startswith("Bash( ")]
    assert "Bash(make check*)" in allow
