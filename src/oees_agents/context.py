"""The managed project-context block every target starts with."""

from collections.abc import Sequence
from dataclasses import asdict
from string import Template

from oees_agents.manifest import Project
from oees_agents.output import RenderError


def context_block(project: Project, kits: Sequence[str], template: str) -> str:
    values = asdict(project)
    for key, value in values.items():
        if "<!--" in value or "-->" in value:
            raise RenderError(f"project.{key} cannot contain HTML comment markers")
    values = {key: " ".join(value.split()) for key, value in values.items()}
    values["stack"] = ", ".join(kits) or "no kit selected"
    try:
        return Template(template).substitute(values)
    except (KeyError, ValueError) as error:
        raise RenderError(f"the project-context template is invalid: {error}") from error
