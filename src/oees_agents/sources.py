"""Where the content comes from: bundled with the CLI, a local checkout, or a git ref."""

import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from oees_agents import __version__
from oees_agents.content import Content, load_content

REPOSITORY = "https://github.com/oees/agents"
REPOSITORY_ENV = "OEES_AGENTS_REPOSITORY"
LOCAL = "local"

_PACKAGE = Path(__file__).resolve().parent

logger = logging.getLogger(__name__)


class SourceError(RuntimeError):
    """The requested content version cannot be fetched."""


@dataclass(frozen=True)
class Source:
    content: Content
    label: str
    """What the manifest records as `source`."""


def bundled_root() -> Path:
    """Content packed into the wheel, or the repository root in a source checkout."""
    packaged = _PACKAGE / "_bundled"
    return packaged if packaged.is_dir() else _PACKAGE.parents[1]


def resolve(ref: str | None, content_dir: Path | None) -> Source:
    if content_dir is not None:
        return Source(load_content(content_dir), LOCAL)
    if ref is not None:
        return Source(_fetch(ref), ref)
    return Source(load_content(bundled_root()), f"v{__version__}")


def _fetch(ref: str) -> Content:
    repository = os.environ.get(REPOSITORY_ENV, REPOSITORY)
    with tempfile.TemporaryDirectory(prefix="oees-agents-") as directory:
        command = [
            "git",
            "clone",
            "--quiet",
            "--depth",
            "1",
            "--branch",
            ref,
            repository,
            directory,
        ]
        logger.info("fetching content", extra={"ref": ref, "repository": repository})
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError as error:
            raise SourceError("git is needed to fetch content with --ref") from error
        except subprocess.CalledProcessError as error:
            logger.error(
                "fetching content failed",
                extra={"ref": ref, "repository": repository, "stderr": error.stderr.strip()},
            )
            raise SourceError(
                f"cannot fetch {ref!r} from {repository}: {error.stderr.strip()}"
            ) from error
        return load_content(Path(directory))
