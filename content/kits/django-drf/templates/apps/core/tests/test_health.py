from unittest.mock import patch

import pytest
from django.db import OperationalError
from django.test import Client


def test_healthz_returns_ok_without_authentication_or_database(client: Client) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_answers_probes_whose_host_is_not_an_allowed_host(
    client: Client,
) -> None:
    response = client.get("/healthz", HTTP_HOST="10.244.0.17:8000")

    assert response.status_code == 200


@pytest.mark.django_db
def test_readyz_returns_ok_when_the_database_answers(client: Client) -> None:
    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok"}}


def test_readyz_returns_503_when_the_database_is_unreachable(client: Client) -> None:
    with patch("apps.core.views.connection") as connection:
        connection.cursor.side_effect = OperationalError("connection refused")
        response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "checks": {"database": "unavailable"},
    }


def test_health_paths_only_answer_get_and_head(client: Client) -> None:
    response = client.post("/healthz")

    assert response.status_code == 404
