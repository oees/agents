"""What a target renders: files it owns outright and blocks it manages inside files."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal


class RenderError(ValueError):
    """The manifest asks for something the content cannot provide."""


@dataclass(frozen=True)
class ManagedBlock:
    """Text kept between the shared-rule markers inside a file the project also edits."""

    body: str
    placement: Literal["top", "bottom"]
    max_bytes: int | None = None


@dataclass(frozen=True)
class Output:
    files: Mapping[str, bytes] = field(default_factory=lambda: MappingProxyType({}))
    blocks: Mapping[str, ManagedBlock] = field(default_factory=lambda: MappingProxyType({}))

    @property
    def paths(self) -> set[str]:
        return {*self.files, *self.blocks}


def merge_outputs(outputs: Iterable[Output]) -> Output:
    files: dict[str, bytes] = {}
    blocks: dict[str, ManagedBlock] = {}
    for output in outputs:
        for path in output.paths:
            if path in files or path in blocks:
                raise RenderError(f"{path} is rendered by more than one target")
        files.update(output.files)
        blocks.update(output.blocks)
    return Output(
        files=MappingProxyType(dict(sorted(files.items()))),
        blocks=MappingProxyType(dict(sorted(blocks.items()))),
    )
