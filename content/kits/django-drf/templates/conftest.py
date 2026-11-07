"""Fixtures shared by every app's tests."""

from collections.abc import Iterator

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from rest_framework.test import APIClient
from structlog.contextvars import clear_contextvars

TEST_USER_PASSWORD = "placeholder-test-password"


@pytest.fixture(autouse=True)
def _isolated_log_context() -> Iterator[None]:
    """Bound log context (request_id, task_id) never leaks from one test to the next."""
    clear_contextvars()
    yield
    clear_contextvars()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user_password() -> str:
    return TEST_USER_PASSWORD


@pytest.fixture
def user(db: None, user_password: str) -> AbstractBaseUser:
    return get_user_model().objects.create_user(username="ana", password=user_password)


@pytest.fixture
def auth_client(api_client: APIClient, user: AbstractBaseUser) -> APIClient:
    api_client.force_authenticate(user=user)
    return api_client
