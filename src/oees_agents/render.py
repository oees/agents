"""Build the full file set a manifest asks for."""

from collections.abc import Callable, Mapping

from oees_agents.content import Content
from oees_agents.manifest import Manifest, Target
from oees_agents.output import Output, RenderError, merge_outputs
from oees_agents.targets import claude, codex, cursor

TargetRenderer = Callable[[Manifest, Content], Output]

RENDERERS: Mapping[Target, TargetRenderer] = {
    "claude": claude.render,
    "cursor": cursor.render,
    "codex": codex.render,
}


def render(manifest: Manifest, content: Content) -> Output:
    _check_names("default", manifest.defaults, content.defaults)
    _check_names("kit", manifest.kits, content.kits)
    _check_names("loop", manifest.extras.loops, content.loops)
    outputs = []
    for target in manifest.targets:
        outputs.append(RENDERERS[target](manifest, content))
    return merge_outputs(outputs)


def _check_names(kind: str, wanted: tuple[str, ...], available: Mapping[str, object]) -> None:
    for name in wanted:
        if name not in available:
            known = ", ".join(sorted(available)) or "none"
            raise RenderError(f"unknown {kind} {name!r}; available: {known}")
