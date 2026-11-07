import json
from dataclasses import replace
from pathlib import Path

import pytest

from oees_agents.content import load_content
from oees_agents.context import context_block
from oees_agents.manifest import Extras, Manifest, Project
from oees_agents.output import RenderError
from oees_agents.profiles import KIT_GLOBS
from oees_agents.targets.cursor import render

from conftest import COMMAND_SKILLS, CONDUCT, DEFAULTS, write

RULES = ".cursor/rules"
CONTEXT_FILE = f"{RULES}/00-project-context.mdc"

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
        targets=("cursor",),
        project=PROJECT,
        defaults=DEFAULTS,
        kits=("django-drf",),
        extras=Extras(),
    )
    return replace(base, **overrides)  # type: ignore[arg-type]  # overrides are test inputs


def rendered(content_root: Path, **overrides: object) -> dict[str, str]:
    output = render(manifest(**overrides), load_content(content_root))
    return {path: data.decode("utf-8") for path, data in output.files.items()}


def split(mdc: str) -> tuple[dict[str, str], str]:
    assert mdc.startswith("---\n")
    header, separator, body = mdc[4:].partition("\n---\n\n")
    assert separator
    fields = dict(line.split(": ", 1) for line in header.split("\n"))
    return fields, body


def rule(files: dict[str, str], name: str) -> tuple[dict[str, str], str]:
    return split(files[f"{RULES}/{name}.mdc"])


def test_the_project_context_rule_always_applies_and_holds_the_block_once(
    content_root: Path,
) -> None:
    content = load_content(content_root)
    block = context_block(manifest(), content)
    assert block is not None

    fields, body = split(render(manifest(), content).files[CONTEXT_FILE].decode("utf-8"))

    assert fields["alwaysApply"] == "true"
    assert "globs" not in fields
    assert json.loads(fields["description"]) == (
        "Project context for octohub: who depends on it and how careful to be"
    )
    assert body == block
    assert body.count("BEGIN OEES PROJECT CONTEXT") == 1


def test_there_is_no_project_context_rule_without_a_project(content_root: Path) -> None:
    assert CONTEXT_FILE not in rendered(content_root, project=None)


@pytest.mark.parametrize(
    ("name", "tier"),
    [*((name, "conduct") for name in CONDUCT), *((name, "default") for name in DEFAULTS)],
)
def test_conduct_and_enabled_defaults_always_apply(
    content_root: Path, name: str, tier: str
) -> None:
    fields, body = rule(rendered(content_root), name)

    assert fields == {"description": f"{name} {tier}", "alwaysApply": "true"}
    assert body.startswith(f"# {name.title()}\n")


def test_an_opted_out_default_has_no_rule(content_root: Path) -> None:
    files = rendered(content_root, defaults=("git",))

    assert f"{RULES}/git.mdc" in files
    assert f"{RULES}/tdd.mdc" not in files


def test_a_document_without_a_description_falls_back_to_its_name(content_root: Path) -> None:
    write(content_root / "content/conduct/plain.md", "# Plain\n\nNo frontmatter.\n")

    fields, body = rule(rendered(content_root), "plain")

    assert fields["description"] == "plain rules"
    assert body == "# Plain\n\nNo frontmatter.\n"


def test_python_patterns_attach_to_python_files(content_root: Path) -> None:
    fields, _ = rule(rendered(content_root), "python-patterns")

    assert fields["globs"] == '["**/*.py"]'
    assert fields["alwaysApply"] == "false"


def test_typescript_patterns_attach_to_both_typescript_extensions(content_root: Path) -> None:
    fields, _ = rule(rendered(content_root), "typescript-patterns")

    assert json.loads(fields["globs"]) == ["**/*.ts", "**/*.tsx"]
    assert fields["alwaysApply"] == "false"


def test_an_enabled_kit_with_known_globs_is_glob_attached(content_root: Path) -> None:
    fields, body = rule(rendered(content_root), "django-drf")

    assert fields["globs"] == json.dumps(list(KIT_GLOBS["django-drf"]))
    assert fields["alwaysApply"] == "false"
    assert fields["description"] == "The django-drf stack kit."
    assert body == "# django-drf\n"


def test_a_disabled_kit_has_no_rule(content_root: Path) -> None:
    files = rendered(content_root)

    assert f"{RULES}/fastapi.mdc" not in files
    assert f"{RULES}/htmx-alpine.mdc" not in files


def test_an_enabled_kit_without_known_globs_is_agent_requested(content_root: Path) -> None:
    write(
        content_root / "content/kits/rails/SKILL.md",
        "---\nname: rails\ndescription: The rails stack kit.\n---\n\n# rails\n",
    )

    fields, _ = rule(rendered(content_root, kits=("rails",)), "rails")

    assert fields == {"description": "The rails stack kit.", "alwaysApply": "false"}


@pytest.mark.parametrize("name", COMMAND_SKILLS)
def test_command_skills_are_agent_requested(content_root: Path, name: str) -> None:
    fields, _ = rule(rendered(content_root), name)

    assert "globs" not in fields
    assert fields["alwaysApply"] == "false"
    assert json.loads(fields["description"]) == f"Use for {name}: the {name} skill."


def test_the_subagent_only_reviewing_skill_is_never_rendered(content_root: Path) -> None:
    files = rendered(content_root)

    assert not any("reviewing" in path for path in files)


def test_bodies_carry_no_frontmatter(content_root: Path) -> None:
    for path, text in rendered(content_root).items():
        _, body = split(text)
        assert "---" not in body, path
        assert "name:" not in body, path
        assert not body.startswith("\n"), path


def test_a_description_with_a_colon_is_quoted_and_round_trips(content_root: Path) -> None:
    fields, _ = rule(rendered(content_root), "commit")

    assert fields["description"].startswith('"')
    assert json.loads(fields["description"]) == "Use for commit: the commit skill."


@pytest.mark.parametrize(
    "description",
    [
        "Tags # are comments",
        "- looks like a list",
        "? looks like a key",
        "*anchor-like",
        "`backticked` start",
        "[bracketed]",
        "'single quoted'",
        "Ends with a colon:",
    ],
)
def test_yaml_unsafe_descriptions_are_quoted(content_root: Path, description: str) -> None:
    write(
        content_root / "content/conduct/odd.md",
        f"---\ndescription: {json.dumps(description)}\n---\n\n# Odd\n",
    )

    fields, _ = rule(rendered(content_root), "odd")

    assert json.loads(fields["description"]) == description


def test_descriptions_are_collapsed_to_one_line(content_root: Path) -> None:
    write(
        content_root / "content/conduct/wrapped.md",
        '---\ndescription: "Two\\n  lines"\n---\n\n# Wrapped\n',
    )

    fields, _ = rule(rendered(content_root), "wrapped")

    assert fields["description"] == "Two lines"


def test_two_rules_for_one_file_name_are_refused(content_root: Path) -> None:
    write(content_root / "content/defaults/test.md", "---\ndescription: t\n---\n\n# Test\n")

    with pytest.raises(RenderError, match=r"\.cursor/rules/test\.mdc"):
        render(manifest(defaults=("test",)), load_content(content_root))


def test_output_is_sorted_by_path(content_root: Path) -> None:
    content = load_content(content_root)
    paths = list(render(manifest(), content).files)

    assert paths == sorted(paths)
    assert all(path.startswith(f"{RULES}/") and path.endswith(".mdc") for path in paths)
    assert render(manifest(), content).blocks == {}
