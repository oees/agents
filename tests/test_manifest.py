from pathlib import Path

import pytest

from oees_agents.manifest import (
    Extras,
    Manifest,
    ManifestError,
    Project,
    dump_manifest,
    parse_manifest,
    read_manifest,
    set_source,
    write_manifest,
)

FULL = """\
version = 1
source = "v1.0.0"
targets = ["claude", "cursor", "codex"]

[project]
name = "octohub"
description = "B2B multi-tenant platform."
users = "external partners, vendors, OEES operations"
blast_radius = "customer-facing"
default_branch = "main"
check = "make check"
check_fast = "make check-fast"

[rules]
defaults = ["tdd", "git"]

[kits]
enabled = ["django-drf", "htmx-alpine"]

[extras]
commands = true
subagents = "core"
loops = []
"""


def a_manifest(**overrides: object) -> Manifest:
    fields: dict[str, object] = {
        "source": "v1.0.0",
        "targets": ("claude", "codex"),
        "project": Project(
            name="octohub",
            description="B2B platform.",
            users="partners",
            blast_radius="regulated",
            default_branch="main",
            check="make check",
            check_fast="make check-fast",
        ),
        "defaults": ("tdd", "git"),
        "kits": ("fastapi",),
        "extras": Extras(commands=False, subagents="extended", loops=("tier-0",)),
    }
    fields.update(overrides)
    return Manifest(**fields)  # type: ignore[arg-type]  # test helper builds from a loose dict


def test_a_manifest_written_then_read_is_equal(tmp_path: Path) -> None:
    manifest = a_manifest()
    path = tmp_path / ".oees-agents.toml"

    write_manifest(path, manifest)

    assert read_manifest(path) == manifest


def test_the_plan_example_parses_and_round_trips() -> None:
    manifest = parse_manifest(FULL)

    assert manifest.project is not None
    assert manifest.project.blast_radius == "customer-facing"
    assert manifest.kits == ("django-drf", "htmx-alpine")
    assert parse_manifest(dump_manifest(manifest)) == manifest


def test_a_manifest_without_project_context_round_trips() -> None:
    manifest = a_manifest(project=None)

    assert parse_manifest(dump_manifest(manifest)) == manifest


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("colour = 'blue'\n" + FULL, "colour"),
        (FULL.replace("[rules]", "[rules]\nkits = []"), "rules.kits"),
        (FULL.replace("[project]", "[project]\nowner = 'me'"), "project.owner"),
        (FULL.replace("[extras]", "[extras]\nhooks = true"), "extras.hooks"),
        (FULL + "[surprise]\n", "surprise"),
    ],
)
def test_unknown_keys_fail_validation_with_the_key_named(text: str, key: str) -> None:
    with pytest.raises(ManifestError, match=f"unknown key '{key}'"):
        parse_manifest(text)


def test_rules_defaults_may_be_empty() -> None:
    manifest = parse_manifest(FULL.replace('defaults = ["tdd", "git"]', "defaults = []"))

    assert manifest.defaults == ()


@pytest.mark.parametrize("value", ["none", "core", "extended"])
def test_extras_subagents_accepts_the_three_tiers(value: str) -> None:
    manifest = parse_manifest(FULL.replace('subagents = "core"', f'subagents = "{value}"'))

    assert manifest.extras.subagents == value


def test_extras_subagents_rejects_anything_else() -> None:
    with pytest.raises(ManifestError, match=r"extras\.subagents"):
        parse_manifest(FULL.replace('subagents = "core"', 'subagents = "all"'))


@pytest.mark.parametrize("value", ["internal", "customer-facing", "regulated"])
def test_blast_radius_accepts_the_three_values(value: str) -> None:
    text = FULL.replace('blast_radius = "customer-facing"', f'blast_radius = "{value}"')

    manifest = parse_manifest(text)

    assert manifest.project is not None
    assert manifest.project.blast_radius == value


def test_blast_radius_rejects_anything_else() -> None:
    text = FULL.replace('blast_radius = "customer-facing"', 'blast_radius = "huge"')

    with pytest.raises(ManifestError, match=r"project\.blast_radius"):
        parse_manifest(text)


def test_unknown_targets_are_rejected() -> None:
    with pytest.raises(ManifestError, match="targets"):
        parse_manifest(FULL.replace('"codex"]', '"windsurf"]'))


def test_wrong_types_are_rejected_with_the_key_named() -> None:
    with pytest.raises(ManifestError, match=r"extras\.commands"):
        parse_manifest(FULL.replace("commands = true", 'commands = "yes"'))


def test_missing_project_fields_are_named() -> None:
    with pytest.raises(ManifestError, match=r"project\.users"):
        parse_manifest(FULL.replace('users = "external partners, vendors, OEES operations"\n', ""))


def test_unsupported_versions_are_rejected() -> None:
    with pytest.raises(ManifestError, match="version"):
        parse_manifest(FULL.replace("version = 1", "version = 2"))


def test_invalid_toml_is_a_manifest_error() -> None:
    with pytest.raises(ManifestError, match="not valid TOML"):
        parse_manifest("version = = 1")


def test_set_source_changes_only_the_source_line_and_keeps_comments() -> None:
    text = FULL.replace('defaults = ["tdd", "git"]', 'defaults = ["tdd", "git"]  # no api: no HTTP')

    updated = set_source(text, "v1.2.0")

    assert updated == text.replace('source = "v1.0.0"', 'source = "v1.2.0"')
    assert parse_manifest(updated).source == "v1.2.0"
