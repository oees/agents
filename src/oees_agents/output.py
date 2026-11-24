"""What a target renders: files it owns outright and blocks it manages inside files."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, TypeVar

V = TypeVar("V")


class RenderError(ValueError):
    """The manifest asks for something the content cannot provide."""


@dataclass(frozen=True)
class ManagedBlock:
    """Text kept between the shared-rule markers inside a file the project also edits."""

    body: str
    placement: Literal["top", "bottom"]
    max_bytes: int | None = None


def _frozen(items: Mapping[str, V]) -> Mapping[str, V]:
    return MappingProxyType(dict(sorted(items.items())))


@dataclass(frozen=True)
class Output:
    """A render, with every mapping sorted by path and read-only."""

    files: Mapping[str, bytes] = field(default_factory=dict)
    blocks: Mapping[str, ManagedBlock] = field(default_factory=dict)
    optional: Mapping[str, str] = field(default_factory=dict)
    """Files written only where the user has no file of their own, each with the
    advice for a user who keeps theirs ("" when there is none)."""
    notes: Mapping[str, str] = field(default_factory=dict)
    """What to tell the user when a file is written, such as a step it needs."""

    def __post_init__(self) -> None:
        for name in ("files", "blocks", "optional", "notes"):
            object.__setattr__(self, name, _frozen(getattr(self, name)))

    @property
    def paths(self) -> set[str]:
        return {*self.files, *self.blocks}


def merge_outputs(outputs: Iterable[Output]) -> Output:
    files: dict[str, bytes] = {}
    blocks: dict[str, ManagedBlock] = {}
    optional: dict[str, str] = {}
    notes: dict[str, str] = {}
    for output in outputs:
        for path in output.paths:
            if path in files or path in blocks:
                raise RenderError(f"{path} is rendered by more than one target")
        files.update(output.files)
        blocks.update(output.blocks)
        optional.update(output.optional)
        notes.update(output.notes)
    return Output(files=files, blocks=blocks, optional=optional, notes=notes)
