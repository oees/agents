"""oees-agents: install and update OEES agent tooling from a committed manifest."""

import logging
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer

from oees_agents.blocks import BlockError
from oees_agents.content import ContentError, Document
from oees_agents.log import configure
from oees_agents.manifest import (
    MANIFEST_NAME,
    Manifest,
    ManifestError,
    parse_manifest,
    set_source,
    write_manifest,
)
from oees_agents.output import RenderError
from oees_agents.questions import Flags, QuestionError, ask, default_prompter, detect
from oees_agents.render import render
from oees_agents.sources import LOCAL, SourceError, resolve
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
    loop: Annotated[list[str] | None, typer.Option(help="Loop to install; repeat.")] = None,
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
        manifest_path = path / MANIFEST_NAME
        if manifest_path.exists():
            _fail(f"{manifest_path} exists already; run `oees-agents update` instead")
        source = resolve(ref, content_dir)
        content = source.content
        flags = Flags(
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
            loops=_tuple(loop),
            commands=not no_commands,
        )
        try:
            answers = ask(
                flags,
                detect(path, tuple(content.kits)),
                defaults=tuple(content.defaults),
                kits=tuple(content.kits),
                loops=tuple(content.loops),
                prompter=None if yes else default_prompter(),
            )
        except QuestionError as error:
            typer.echo(f"error: {error}", err=True)
            raise typer.Exit(2) from error
        manifest = Manifest(
            source=source.label,
            targets=answers.targets,
            project=answers.project,
            defaults=answers.defaults,
            kits=answers.kits,
            extras=answers.extras,
        )
        pending = plan(path, render(manifest, content), read_lock(path), force)
        apply(path, pending)
        write_manifest(manifest_path, manifest)
        typer.echo(f"Wrote {MANIFEST_NAME}. Commit it with the generated files and the lock.")
        _report(pending)


@app.command()
def update(
    path: ProjectPath = Path(),
    ref: Ref = None,
    force: Force = False,
    content_dir: ContentDir = None,
) -> None:
    """Re-render everything from .oees-agents.toml."""
    with _handled():
        text, manifest = _read_manifest(path)
        source = resolve(ref, content_dir)
        manifest = replace(manifest, source=source.label)
        pending = plan(path, render(manifest, source.content), read_lock(path), force)
        apply(path, pending)
        if parse_manifest(text).source != source.label:
            (path / MANIFEST_NAME).write_text(set_source(text, source.label), encoding="utf-8")
            typer.echo(f"Pinned {MANIFEST_NAME} to {source.label}.")
        _report(pending)


@app.command("check")
def check_command(
    path: ProjectPath = Path(),
    ref: Ref = None,
    content_dir: ContentDir = None,
) -> None:
    """Exit non-zero when generated files are missing, stale or edited by hand."""
    with _handled():
        _, manifest = _read_manifest(path)
        source = resolve(ref, content_dir)
        if source.label not in (manifest.source, LOCAL):
            typer.echo(f"note: {MANIFEST_NAME} pins {manifest.source}; checking {source.label}")
        pending = plan(path, render(manifest, source.content), read_lock(path))
        if pending.is_clean:
            typer.echo("oees-agents files are up to date.")
            return
        for item in sorted(pending.writes):
            typer.echo(f"stale or missing: {item}")
        for item in (*pending.deletes, *pending.unblocks):
            typer.echo(f"no longer rendered: {item}")
        for conflict in pending.conflicts:
            typer.echo(f"edited by hand: {conflict.path} ({conflict.reason})")
        typer.echo("Run `oees-agents update` to bring them in line.")
        raise typer.Exit(1)


@app.command("list")
def list_command(ref: Ref = None, content_dir: ContentDir = None) -> None:
    """Show the conduct, defaults, kits, subagents and loops on offer."""
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
        _section("Loops (opt in with --loop <name>)", content.loops.items())


def _section(title: str, documents: Iterable[tuple[str, Document]]) -> None:
    typer.echo(title)
    for name, document in documents:
        typer.echo(f"  {name}  {_summary(document)}".rstrip())


def _summary(document: Document) -> str:
    if document.description:
        return " ".join(document.description.split())
    for line in document.body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


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
    for warning in pending.warnings:
        typer.echo(f"warning: {warning}", err=True)


def _files(count: int) -> str:
    return f"{count} file" if count == 1 else f"{count} files"


def _read_manifest(path: Path) -> tuple[str, Manifest]:
    manifest_path = path / MANIFEST_NAME
    if not manifest_path.is_file():
        _fail(f"no {MANIFEST_NAME} in {path}; run `oees-agents init` first")
    text = manifest_path.read_text(encoding="utf-8")
    return text, parse_manifest(text)


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
