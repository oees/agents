from pathlib import Path

import pytest
from django.contrib.auth.models import AbstractBaseUser
from django.core.management import call_command
from django.test import Client
from rest_framework.test import APIClient


def test_the_api_root_requires_authentication(api_client: APIClient) -> None:
    assert api_client.get("/api/v1/").status_code == 401


def test_authenticated_clients_reach_the_api(auth_client: APIClient) -> None:
    assert auth_client.get("/api/v1/").status_code == 200


def test_a_token_pair_authenticates_and_refresh_rotates_it(
    api_client: APIClient, user: AbstractBaseUser, user_password: str
) -> None:
    tokens = api_client.post(
        "/api/v1/auth/token/",
        {"username": user.get_username(), "password": user_password},
    ).json()

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert api_client.get("/api/v1/").status_code == 200

    refreshed = api_client.post(
        "/api/v1/auth/token/refresh/", {"refresh": tokens["refresh"]}
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh"] != tokens["refresh"]

    reused = api_client.post(
        "/api/v1/auth/token/refresh/", {"refresh": tokens["refresh"]}
    )
    assert reused.status_code == 401


@pytest.mark.django_db
def test_wrong_credentials_get_the_error_envelope(api_client: APIClient) -> None:
    response = api_client.post(
        "/api/v1/auth/token/", {"username": "ana", "password": "wrong"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "no_active_account"


def test_the_schema_is_only_served_to_staff(
    client: Client, admin_client: Client
) -> None:
    assert client.get("/api/v1/schema/").status_code == 403
    assert admin_client.get("/api/v1/schema/").status_code == 200


@pytest.mark.django_db
def test_the_openapi_schema_generates_without_warnings(tmp_path: Path) -> None:
    call_command(
        "spectacular", "--validate", "--fail-on-warn", "--file", str(tmp_path / "s.yml")
    )
