"""The managed project-context block every target starts with."""

from string import Template

from oees_agents.content import Content
from oees_agents.manifest import Manifest
from oees_agents.output import RenderError


def context_block(manifest: Manifest, content: Content) -> str | None:
    project = manifest.project
    if project is None:
        return None
    values = {
        "name": project.name,
        "description": project.description,
        "users": project.users,
        "blast_radius": project.blast_radius,
        "default_branch": project.default_branch,
        "check": project.check,
        "check_fast": project.check_fast,
    }
    for key, value in values.items():
        if "<!--" in value or "-->" in value:
            raise RenderError(f"project.{key} cannot contain HTML comment markers")
    values = {key: " ".join(value.split()) for key, value in values.items()}
    values["stack"] = ", ".join(manifest.kits) or "no kit selected"
    try:
        return Template(content.context_template).substitute(values)
    except (KeyError, ValueError) as error:
        raise RenderError(f"the project-context template is invalid: {error}") from error
