"""Cursor target: one `.cursor/rules/*.mdc` file per rule, skill and enabled kit.

Conduct, enabled defaults and the project context always apply. Pattern skills and
kits with known globs attach to matching files; every other skill is agent-requested,
picked by its description the way Claude Code picks a skill.
"""

import json
from types import MappingProxyType

from oees_agents.content import Content, Document
from oees_agents.context import context_block
from oees_agents.manifest import Manifest
from oees_agents.output import Output, RenderError
from oees_agents.profiles import KIT_GLOBS, PATTERN_GLOBS, SUBAGENT_ONLY_SKILLS
from oees_agents.scope import Layout
from oees_agents.sources import LOCAL, REPOSITORY

RULES_DIR = ".cursor/rules"
CONTEXT_RULE = "00-project-context"


def render(manifest: Manifest, content: Content, layout: Layout) -> Output:
    """Cursor reads rules only from a project, so `layout` changes nothing here."""
    files: dict[str, bytes] = {}

    def add(
        name: str, description: str, body: str, globs: tuple[str, ...] = (), *, always: bool
    ) -> None:
        path = f"{RULES_DIR}/{name}.mdc"
        if path in files:
            raise RenderError(f"{path} is rendered from more than one source")
        files[path] = _mdc(description, body, globs, always_apply=always).encode("utf-8")

    project = manifest.project
    if project is not None:
        description = f"Project context for {project.name}: who depends on it and how careful to be"
        block = context_block(project, manifest.kits, content.context_template)
        add(CONTEXT_RULE, description, block, always=True)
    for document in content.rules(manifest.defaults):
        description = document.description or f"{document.name} rules"
        add(document.name, description, _body(document), always=True)
    for name, skill in content.skills.items():
        if name not in SUBAGENT_ONLY_SKILLS:
            globs = PATTERN_GLOBS.get(name, ())
            add(name, skill.description, _body(skill.document), globs, always=False)
    for name in manifest.kits:
        kit = content.kits[name]
        body = f"{_body(kit.document)}\n{_templates_note(manifest, name)}\n"
        add(name, kit.description, body, KIT_GLOBS.get(name, ()), always=False)
    return Output(files=MappingProxyType(dict(sorted(files.items()))))


def _templates_note(manifest: Manifest, kit: str) -> str:
    """Cursor installs no templates, so say where this kit's templates are."""
    if "claude" in manifest.targets:
        where = f"`.claude/skills/{kit}/templates/`"
    else:
        ref = "main" if manifest.source == LOCAL else manifest.source
        where = f"{REPOSITORY}/tree/{ref}/content/kits/{kit}/templates"
    return f"The files that this kit names are in its templates: {where}."


def _body(document: Document) -> str:
    return document.body.lstrip("\n")


def _mdc(description: str, body: str, globs: tuple[str, ...], *, always_apply: bool) -> str:
    lines = ["---", f"description: {_yaml_line(description)}"]
    if globs:
        lines.append(f"globs: {json.dumps(list(globs))}")
    lines += [f"alwaysApply: {'true' if always_apply else 'false'}", "---", "", body]
    return "\n".join(lines)


def _yaml_line(value: str) -> str:
    """One line, double-quoted: a JSON string is a valid YAML scalar, whatever it holds."""
    return json.dumps(" ".join(value.split()))
