import pytest
from django.test import Client
from pytest_django import Settings

from apps.core.tests.htmx_urls import use_example_templates

pytestmark = [pytest.mark.django_db, pytest.mark.urls("apps.core.tests.htmx_urls")]


@pytest.fixture(autouse=True)
def _example_templates(settings: Settings) -> None:
    use_example_templates(settings)


@pytest.fixture
def policy(client: Client) -> list[str]:
    header = client.get("/example/")["Content-Security-Policy"]
    return [directive.strip() for directive in header.split(";")]


def test_policy_defaults_to_self(policy: list[str]) -> None:
    assert "default-src 'self'" in policy
    assert "script-src 'self'" in policy
    assert "style-src 'self'" in policy


def test_policy_allows_no_inline_code_or_eval(policy: list[str]) -> None:
    joined = "; ".join(policy)
    assert "'unsafe-inline'" not in joined
    assert "'unsafe-eval'" not in joined
    assert "'nonce-" not in joined


def test_policy_blocks_plugins_framing_and_base_rewrites(policy: list[str]) -> None:
    assert "object-src 'none'" in policy
    assert "frame-ancestors 'none'" in policy
    assert "base-uri 'none'" in policy
    assert "form-action 'self'" in policy
