"""The ten-line bootstrap: install uv if missing, then run the CLI at the latest tag."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

BOOTSTRAP = Path(__file__).resolve().parents[1] / "scripts/bootstrap.sh"
TAGS = "aaa\trefs/tags/v1.2.0\nbbb\trefs/tags/v1.10.0\nccc\trefs/tags/v1.9.3\n"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


def fake(directory: Path, name: str, body: str) -> None:
    path = directory / name
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(0o755)


@pytest.fixture
def bin_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "bin"
    directory.mkdir()
    for tool in ("sh", "cat", "sort", "sed", "head", "tail", "mkdir", "chmod"):
        found = shutil.which(tool)
        if found:
            (directory / tool).symlink_to(found)
    fake(directory, "git", f"printf '{TAGS}'")
    return directory


def run(bin_dir: Path, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    bash = shutil.which("bash")
    assert bash is not None
    return subprocess.run(
        [bash, str(BOOTSTRAP), *args],
        capture_output=True,
        text=True,
        env={"PATH": str(bin_dir), "HOME": str(bin_dir.parent), **env},
        check=False,
    )


def test_it_runs_the_cli_from_the_latest_tag_with_the_arguments(bin_dir: Path) -> None:
    fake(bin_dir, "uv", "true")
    fake(bin_dir, "uvx", 'printf "%s\\n" "$@"')

    result = run(bin_dir, "--yes", "--kit", "fastapi", "two words")

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "--from",
        "git+https://github.com/oees/agents@v1.10.0",
        "oees-agents",
        "init",
        "--yes",
        "--kit",
        "fastapi",
        "two words",
    ]


def test_a_ref_override_skips_the_tag_lookup(bin_dir: Path) -> None:
    fake(bin_dir, "uv", "true")
    fake(bin_dir, "uvx", 'printf "%s\\n" "$@"')
    fake(bin_dir, "git", "exit 9")

    result = run(bin_dir, OEES_AGENTS_REF="main")

    assert result.returncode == 0, result.stderr
    assert "git+https://github.com/oees/agents@main" in result.stdout


def test_it_installs_uv_when_missing(bin_dir: Path) -> None:
    home_bin = bin_dir.parent / ".local/bin"
    installer = (
        f"mkdir -p {home_bin}; printf '#!/bin/sh\\ntrue\\n' > {home_bin}/uv; "
        f"printf '#!/bin/sh\\necho ran uvx\\n' > {home_bin}/uvx; "
        f"chmod +x {home_bin}/uv {home_bin}/uvx"
    )
    fake(bin_dir, "curl", f"printf '%s\\n' \"{installer}\"")

    result = run(bin_dir)

    assert result.returncode == 0, result.stderr
    assert "ran uvx" in result.stdout


def test_it_stops_when_there_is_no_release_tag(bin_dir: Path) -> None:
    fake(bin_dir, "uv", "true")
    fake(bin_dir, "uvx", "echo should not run")
    fake(bin_dir, "git", "true")

    result = run(bin_dir)

    assert result.returncode == 1
    assert "OEES_AGENTS_REF" in result.stderr
    assert "should not run" not in result.stdout


def test_the_script_stays_small() -> None:
    lines = [line for line in BOOTSTRAP.read_text().splitlines() if line.strip()]

    assert len(lines) <= 15
    assert os.access(BOOTSTRAP, os.X_OK)
