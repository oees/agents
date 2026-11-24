"""Pack the canonical content into the wheel so `uvx --from git+...` has it."""

from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

BUNDLED = ("content", "skills", "commands")


class BundleContentHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        if self.target_name != "wheel" or version == "editable":
            return
        root = Path(self.root)
        for name in BUNDLED:
            if not (root / name).is_dir():
                raise FileNotFoundError(f"{name}/ is missing; the wheel would ship no {name}")
            build_data["force_include"][str(root / name)] = f"oees_agents/_bundled/{name}"
