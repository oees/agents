import logging

import pytest

from oees_agents.sources import REPOSITORY_ENV, SourceError, resolve


def test_a_repository_password_never_reaches_the_log_or_the_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Port 1 on the loopback refuses at once, so the clone fails without the network.
    monkeypatch.setenv(REPOSITORY_ENV, "https://ci-bot:s3cret-token@127.0.0.1:1/agents.git")
    caplog.set_level(logging.DEBUG, logger="oees_agents")

    with pytest.raises(SourceError) as raised:
        resolve(ref="v1.0.0", content_dir=None)

    assert "s3cret-token" not in str(raised.value)
    assert "127.0.0.1:1/agents.git" in str(raised.value)
    logged = " ".join(str(vars(record)) for record in caplog.records)
    assert "repository" in logged
    assert "s3cret-token" not in logged
    assert "ci-bot" not in logged
