import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is needed to build the wheel")
def test_the_wheel_bundles_the_content(tmp_path: Path) -> None:
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path), str(REPO)],
        check=True,
        capture_output=True,
    )
    [wheel] = tmp_path.glob("oees_agents-*.whl")

    names = set(zipfile.ZipFile(wheel).namelist())

    assert "oees_agents/_bundled/content/blocks/project-context.md" in names
    assert any(name.startswith("oees_agents/_bundled/skills/") for name in names)
    assert "oees_agents/cli.py" in names
