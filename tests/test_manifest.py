import os
from pathlib import Path

import pytest

from oees_agents.manifest import (
    MANIFEST_NAME,
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
name = "portal"
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
"""


def a_manifest(**overrides: object) -> Manifest:
    fields: dict[str, object] = {
        "source": "v1.0.0",
        "targets": ("claude", "codex"),
        "project": Project(
            name="portal",
            description="B2B platform.",
            users="partners",
            blast_radius="regulated",
            default_branch="main",
            check="make check",
            check_fast="make check-fast",
        ),
        "defaults": ("tdd", "git"),
        "kits": ("fastapi",),
        "extras": Extras(commands=False, subagents="extended"),
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


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ('targets = ["claude", "cursor", "codex"]', 'targets = ["claude", "claude"]', "targets"),
        ('defaults = ["tdd", "git"]', 'defaults = ["tdd", "tdd"]', r"rules\.defaults"),
        ('enabled = ["django-drf", "htmx-alpine"]', 'enabled = ["fastapi", "fastapi"]', "kits"),
    ],
)
def test_a_name_listed_twice_is_rejected(old: str, new: str, message: str) -> None:
    with pytest.raises(ManifestError, match=f"{message}.*listed more than once"):
        parse_manifest(FULL.replace(old, new))


def test_a_manifest_needs_at_least_one_target() -> None:
    with pytest.raises(ManifestError, match="targets: list at least one target"):
        parse_manifest(FULL.replace('targets = ["claude", "cursor", "codex"]', "targets = []"))


def test_an_empty_project_name_is_rejected() -> None:
    with pytest.raises(ManifestError, match=r"project\.name: must not be empty"):
        parse_manifest(FULL.replace('name = "portal"', 'name = "  "'))


MACHINE = """\
version = 1
source = "v1.0.0"
scope = "machine"
targets = ["claude", "codex"]

[rules]
defaults = ["tdd", "git"]
"""


def test_a_manifest_without_scope_is_a_project_install() -> None:
    assert parse_manifest(FULL).scope == "project"


def test_a_machine_manifest_has_no_project() -> None:
    manifest = parse_manifest(MACHINE)

    assert manifest.scope == "machine"
    assert manifest.project is None
    assert manifest.targets == ("claude", "codex")


def test_a_machine_manifest_round_trips_with_its_scope() -> None:
    manifest = parse_manifest(MACHINE)

    dumped = dump_manifest(manifest)

    assert 'scope = "machine"' in dumped
    assert parse_manifest(dumped) == manifest


def test_a_project_manifest_is_dumped_without_a_scope_line() -> None:
    assert "scope" not in dump_manifest(parse_manifest(FULL))


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (MACHINE.replace('"machine"', '"team"'), "scope: expected one of project, machine"),
        (
            MACHINE.replace('["claude", "codex"]', '["claude", "cursor"]'),
            "targets: Cursor has no machine-wide rules",
        ),
        (
            MACHINE + '\n[project]\nname = "x"\n',
            "project: a machine install has no project",
        ),
    ],
)
def test_invalid_machine_manifests_are_rejected(text: str, message: str) -> None:
    with pytest.raises(ManifestError, match=message):
        parse_manifest(text)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ('source = "v1.0.0"  # pinned by the team', 'source = "v1.2.0"  # pinned by the team'),
        ('source="v1.0.0"', 'source="v1.2.0"'),
        ("source = 'v1.0.0'", 'source = "v1.2.0"'),
    ],
)
def test_set_source_keeps_the_spacing_quotes_and_comment_of_any_valid_line(
    line: str, expected: str
) -> None:
    text = dump_manifest(a_manifest()).replace('source = "v1.0.0"', line)

    assert expected in set_source(text, "v1.2.0").splitlines()


def test_a_manifest_write_that_fails_leaves_the_old_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / MANIFEST_NAME
    write_manifest(path, a_manifest())
    before = path.read_bytes()

    def fail(source: str, destination: Path) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError, match="disk full"):
        write_manifest(path, a_manifest(source="v9.9.9"))

    assert path.read_bytes() == before


def test_set_source_refuses_a_multi_line_string() -> None:
    text = dump_manifest(a_manifest()).replace('source = "v1.0.0"', 'source = """v1.0.0"""')

    with pytest.raises(ManifestError, match="exactly one"):
        set_source(text, "v1.2.0")
