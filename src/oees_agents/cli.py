"""oees-agents: install and update OEES agent tooling from a committed manifest."""

import logging
import sys
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer

from oees_agents import legacy
from oees_agents.blocks import BlockError
from oees_agents.content import ContentError, Document
from oees_agents.log import configure
from oees_agents.manifest import (
    MANIFEST_NAME,
    Manifest,
    ManifestError,
    parse_manifest,
    read_manifest,
    set_source,
    write_manifest,
)
from oees_agents.output import RenderError
from oees_agents.questions import (
    Flags,
    QuestionError,
    ask,
    ask_scope,
    default_prompter,
    detect,
    detect_machine,
)
from oees_agents.render import render
from oees_agents.scope import claude_dir, install_root, update_command
from oees_agents.sources import LOCAL, SourceError, resolve
from oees_agents.targets import codex
from oees_agents.targets.claude import MACHINE_RULES_EXCLUDE
from oees_agents.writer import Plan, WriterError, apply, plan, read_lock

app = typer.Typer(
    help="Install the OEES conduct, defaults, skills and kits for Claude Code, Cursor and Codex.",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)

logger = logging.getLogger(__name__)

ProjectPath = Annotated[
    Path, typer.Argument(help="Project root.", file_okay=False, resolve_path=True)
]
Ref = Annotated[
    str | None,
    typer.Option(help="Content version: a tag or branch of the agents repository."),
]
ContentDir = Annotated[
    Path | None,
    typer.Option(
        help="Render from a local checkout of the agents repository.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
]
Force = Annotated[
    bool, typer.Option(help="Replace generated files and blocks that were edited by hand.")
]
Machine = Annotated[
    bool,
    typer.Option(
        "--machine", help="Work on the machine install in your home directory, not a project."
    ),
]
Many = Annotated[list[str] | None, typer.Option()]


@app.callback()
def main(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Log every file operation as JSON.")
    ] = False,
) -> None:
    configure(verbose)


@app.command()
def init(
    path: ProjectPath = Path(),
    *,
    machine: Annotated[
        bool | None,
        typer.Option(
            "--machine/--project",
            help="Install for the whole machine (~/.claude, ~/.codex) or for this project. "
            "Asked when not given.",
        ),
    ] = None,
    target: Annotated[
        list[str] | None, typer.Option(help="claude, cursor or codex; repeat for several.")
    ] = None,
    name: Annotated[str | None, typer.Option(help="Project name.")] = None,
    description: Annotated[str | None, typer.Option(help="One paragraph: what it is.")] = None,
    users: Annotated[str | None, typer.Option(help="Who uses it.")] = None,
    blast_radius: Annotated[
        str | None, typer.Option(help="internal, customer-facing or regulated.")
    ] = None,
    default_branch: Annotated[str | None, typer.Option()] = None,
    check: Annotated[str | None, typer.Option(help="Full check command.")] = None,
    check_fast: Annotated[str | None, typer.Option(help="Fast check command.")] = None,
    kit: Annotated[
        list[str] | None, typer.Option(help="Kit to enable; repeat for several.")
    ] = None,
    no_kits: Annotated[bool, typer.Option(help="Enable no kit.")] = False,
    no_default: Annotated[
        list[str] | None, typer.Option(help="Default rule to opt out of; repeat for several.")
    ] = None,
    subagents: Annotated[str | None, typer.Option(help="none, core or extended.")] = None,
    no_commands: Annotated[bool, typer.Option(help="Skip the slash commands.")] = False,
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Ask nothing; use flags and defaults.")
    ] = False,
    force: Force = False,
    ref: Ref = None,
    content_dir: ContentDir = None,
) -> None:
    """Ask a few questions, write .oees-agents.toml and generate the files."""
    with _handled():
        flags = Flags(
            scope=None if machine is None else ("machine" if machine else "project"),
            targets=_tuple(target),
            name=name,
            description=description,
            users=users,
            blast_radius=blast_radius,
            default_branch=default_branch,
            check=check,
            check_fast=check_fast,
            kits=() if no_kits else _tuple(kit),
            no_defaults=_tuple(no_default),
            subagents=subagents,
            commands=not no_commands,
        )
        prompter = None if yes else default_prompter()
        with _answering():
            scope = ask_scope(flags, prompter)
        root = install_root(scope, path)
        manifest_path = root / MANIFEST_NAME
        if manifest_path.exists():
            _fail(f"{manifest_path} exists already; run `{update_command(scope)}` instead")
        if scope == "machine":
            _refuse_project_flags(flags)
        source = resolve(ref, content_dir)
        content = source.content
        install = legacy.detect(root, content) if scope == "project" else None
        if install is not None:
            flags = _with_legacy_answers(flags, install, tuple(content.defaults))
        kits = tuple(content.kits)
        suggestions = detect(root, kits) if scope == "project" else detect_machine(root)
        with _answering():
            answers = ask(
                flags,
                suggestions,
                defaults=tuple(content.defaults),
                kits=kits,
                prompter=prompter,
                scope=scope,
            )
        manifest = Manifest(
            source=source.label,
            scope=scope,
            targets=answers.targets,
            project=answers.project,
            defaults=answers.defaults,
            kits=answers.kits,
            extras=answers.extras,
        )
        output = render(manifest, content)
        if install is not None:
            legacy.migrate(root, install)
            _report_legacy(install)
        pending = plan(root, output, read_lock(root), force)
        apply(root, pending)
        write_manifest(manifest_path, manifest)
        if scope == "machine":
            typer.echo(f"Wrote {manifest_path}. It and the lock next to it track this machine.")
        else:
            typer.echo(f"Wrote {MANIFEST_NAME}. Commit it with the generated files and the lock.")
        _report(pending)
        if scope == "project":
            _report_machine_overlap(root, manifest, pending)
        elif "codex" in manifest.targets:
            _report_codex_hook(manifest, output.files, pending)


@app.command()
def update(
    path: ProjectPath = Path(),
    machine: Machine = False,
    ref: Ref = None,
    force: Force = False,
    content_dir: ContentDir = None,
) -> None:
    """Re-render everything from .oees-agents.toml."""
    with _handled():
        root = install_root("machine", path) if machine else path
        text, manifest = _read_manifest(root, machine)
        source = resolve(ref, content_dir)
        manifest = replace(manifest, source=source.label)
        pending = plan(root, render(manifest, source.content), read_lock(root), force)
        # Pin first: if the source line cannot be rewritten, no file has changed yet.
        pinned = None
        if parse_manifest(text).source != source.label:
            pinned = set_source(text, source.label)
        apply(root, pending)
        if pinned is not None:
            (root / MANIFEST_NAME).write_text(pinned, encoding="utf-8")
            typer.echo(f"Pinned {MANIFEST_NAME} to {source.label}.")
        _report(pending)


@app.command("check")
def check_command(
    path: ProjectPath = Path(),
    machine: Machine = False,
    ref: Ref = None,
    content_dir: ContentDir = None,
) -> None:
    """Exit non-zero when generated files are missing, stale or edited by hand."""
    with _handled():
        root = install_root("machine", path) if machine else path
        _, manifest = _read_manifest(root, machine)
        source = resolve(ref, content_dir)
        if source.label not in (manifest.source, LOCAL):
            typer.echo(f"note: {MANIFEST_NAME} pins {manifest.source}; checking {source.label}")
        pending = plan(root, render(manifest, source.content), read_lock(root))
        if pending.is_clean:
            typer.echo("oees-agents files are up to date.")
            return
        for item in sorted(pending.writes):
            typer.echo(f"stale or missing: {item}")
        for item in (*pending.deletes, *pending.unblocks):
            typer.echo(f"no longer rendered: {item}")
        for conflict in pending.conflicts:
            typer.echo(f"edited by hand: {conflict.path} ({conflict.reason})")
        update = update_command(manifest.scope)
        if pending.writes or pending.deletes or pending.unblocks:
            typer.echo(f"Run `{update}` to bring the generated files in line.")
        if pending.conflicts:
            typer.echo(f"Run `{update} --force` to replace the files edited by hand.")
        raise typer.Exit(1)


@app.command("list")
def list_command(ref: Ref = None, content_dir: ContentDir = None) -> None:
    """Show the conduct, defaults, kits and subagents on offer."""
    with _handled():
        content = resolve(ref, content_dir).content
        _section("Conduct (always on)", content.conduct.items())
        _section("Defaults (on unless you pass --no-default <name>)", content.defaults.items())
        _section(
            "Kits (opt in with --kit <name>)",
            ((name, kit.document) for name, kit in content.kits.items()),
        )
        typer.echo("Subagents (--subagents)")
        core = ", ".join(content.subagents["core"])
        typer.echo("  none  no subagents")
        typer.echo(f"  core  {core}")
        typer.echo(f"  extended  core plus {', '.join(content.subagents['extended'])}")


def _section(title: str, documents: Iterable[tuple[str, Document]]) -> None:
    typer.echo(title)
    for name, document in documents:
        typer.echo(f"  {name}  {document.summary}".rstrip())


def _with_legacy_answers(
    flags: Flags, install: legacy.LegacyInstall, defaults: tuple[str, ...]
) -> Flags:
    """A pre-manifest install already answers everything but the project context."""
    return replace(
        flags,
        targets=flags.targets or install.targets,
        kits=flags.kits if flags.kits is not None else (),
        no_defaults=flags.no_defaults
        if flags.no_defaults is not None
        else tuple(name for name in defaults if name not in install.defaults),
        subagents=flags.subagents or "none",
        commands=flags.commands and install.commands,
    )


def _report_legacy(install: legacy.LegacyInstall) -> None:
    typer.echo(
        f"Migrated a pre-manifest install: removed {_files(len(install.removable))} "
        "copied unchanged from oees/agents."
    )
    if install.kept:
        typer.echo("Kept, because they were edited after install (delete them if unneeded):")
        for item in install.kept:
            typer.echo(f"  {item}")


def _report(pending: Plan) -> None:
    removed = len(pending.deletes) + len(pending.unblocks)
    typer.echo(
        f"Wrote {_files(len(pending.writes))}, removed {removed}, "
        f"{len(pending.unchanged)} already current."
    )
    if pending.conflicts:
        typer.echo("Left untouched:")
        for conflict in pending.conflicts:
            typer.echo(f"  {conflict.path}: {conflict.reason}")
    for path in pending.own:
        typer.echo(
            f"Kept your own {path}; oees-agents does not manage it. "
            "Delete it, or use --force, to take the generated one."
        )
    for warning in pending.warnings:
        typer.echo(f"warning: {warning}", err=True)


def _files(count: int) -> str:
    return f"{count} file" if count == 1 else f"{count} files"


def _read_manifest(root: Path, machine: bool = False) -> tuple[str, Manifest]:
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        hint = ""
        if not machine and _machine_manifest(root) is not None:
            hint = "; for the machine install, add --machine"
        _fail(f"no {MANIFEST_NAME} in {root}; run `oees-agents init` first{hint}")
    text = manifest_path.read_text(encoding="utf-8")
    manifest = parse_manifest(text)
    if machine and manifest.scope != "machine":
        _fail(f"{manifest_path} is a project install; run the command without --machine")
    return text, manifest


def _machine_manifest(root: Path) -> Manifest | None:
    """The manifest of a machine install other than `root` itself."""
    home = install_root("machine", root)
    if root.resolve() == home.resolve() or not (home / MANIFEST_NAME).is_file():
        return None
    try:
        manifest = read_manifest(home / MANIFEST_NAME)
    except ManifestError:
        return None
    return manifest if manifest.scope == "machine" else None


def _report_machine_overlap(root: Path, manifest: Manifest, pending: Plan) -> None:
    """Say where the machine rules still load next to this project's rules.

    The generated Claude Code settings skip the machine rules; a project's own
    settings file does not. The machine's Codex hook skips them by itself.
    """
    machine = _machine_manifest(root)
    if machine is None or "claude" not in set(manifest.targets) & set(machine.targets):
        return
    settings = f"{claude_dir('project')}/settings.json"
    if settings in pending.own:
        typer.echo(
            "Claude Code also loads the machine rules here. To use only this project's "
            f'rules, add "claudeMdExcludes": ["{MACHINE_RULES_EXCLUDE}"] to {settings}.'
        )


def _report_codex_hook(manifest: Manifest, files: Mapping[str, bytes], pending: Plan) -> None:
    """Codex loads the machine rules through a hook that the user must approve."""
    hooks = codex.hooks_path(manifest)
    if hooks in pending.own:
        typer.echo(f"Codex loads the machine rules through a session hook. Add it to your {hooks}:")
        typer.echo(files[hooks].decode(), nl=False)
    typer.echo("Codex runs the hook only after you approve it: start Codex and run /hooks.")


def _refuse_project_flags(flags: Flags) -> None:
    given = [
        option
        for option, value in (
            ("--name", flags.name),
            ("--description", flags.description),
            ("--users", flags.users),
            ("--blast-radius", flags.blast_radius),
            ("--default-branch", flags.default_branch),
            ("--check", flags.check),
            ("--check-fast", flags.check_fast),
        )
        if value is not None
    ]
    if given:
        _fail(f"{', '.join(given)} describe a project; a machine install has no project")


@contextmanager
def _answering() -> Iterator[None]:
    """Turn a bad answer or closed input into a plain error."""
    try:
        yield
    except QuestionError as error:
        typer.echo(f"error: {error}", err=True)
        raise typer.Exit(2) from error
    except typer.Abort:
        if sys.stdin.isatty():
            raise
        _fail(
            "init needs answers, but its input ended. Run it in a terminal, "
            "or pass --yes with --description and --users."
        )


def _tuple(values: list[str] | None) -> tuple[str, ...] | None:
    return tuple(values) if values else None


def _fail(message: str) -> None:
    typer.echo(f"error: {message}", err=True)
    raise typer.Exit(1)


@contextmanager
def _handled() -> Iterator[None]:
    try:
        yield
    except (
        BlockError,
        ContentError,
        legacy.LegacyError,
        ManifestError,
        RenderError,
        SourceError,
        WriterError,
    ) as error:
        logger.error("command failed", extra={"error": str(error)})
        _fail(str(error))
    except (typer.Exit, typer.Abort):
        raise
    except Exception:
        logger.exception("unexpected failure")
        raise
