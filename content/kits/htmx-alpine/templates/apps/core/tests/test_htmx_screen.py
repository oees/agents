from http import HTTPStatus

import pytest
from django.test import Client
from pytest_django import Settings

from apps.core.tests.htmx_urls import use_example_templates

pytestmark = [pytest.mark.django_db, pytest.mark.urls("apps.core.tests.htmx_urls")]

HTMX = {"HX-Request": "true"}


@pytest.fixture(autouse=True)
def _example_templates(settings: Settings) -> None:
    use_example_templates(settings)


def test_plain_request_gets_the_full_page(client: Client) -> None:
    response = client.get("/example/")

    body = response.content.decode()
    assert response.status_code == HTTPStatus.OK
    assert "<html" in body
    assert '<a class="skip-link" href="#main">' in body
    assert 'id="live-region"' in body
    assert 'id="example-form"' in body
    assert "HX-Request" in response["Vary"]


def test_htmx_request_gets_only_the_named_partial(client: Client) -> None:
    response = client.get("/example/", headers=HTMX)

    body = response.content.decode()
    assert response.status_code == HTTPStatus.OK
    assert "<html" not in body
    assert body.lstrip().startswith('<form id="example-form"')
    assert "HX-Request" in response["Vary"]


def test_htmx_partial_carries_messages_out_of_band(client: Client) -> None:
    response = client.get("/example/", headers=HTMX)

    assert 'id="messages"' in response.content.decode()
    assert 'hx-swap-oob="innerHTML"' in response.content.decode()


@pytest.mark.parametrize(
    "headers",
    [
        {**HTMX, "HX-Boosted": "true"},
        {**HTMX, "HX-History-Restore-Request": "true"},
    ],
    ids=["boosted", "history-restore"],
)
def test_requests_that_replace_the_body_get_the_full_page(
    client: Client, headers: dict[str, str]
) -> None:
    response = client.get("/example/", headers=headers)

    assert "<html" in response.content.decode()


def test_invalid_post_rerenders_the_form_with_errors_and_422(client: Client) -> None:
    response = client.post("/example/", {"name": ""}, headers=HTMX)

    body = response.content.decode()
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert "<html" not in body
    assert 'aria-invalid="true"' in body
    assert 'aria-describedby="id_name_error"' in body
    assert 'id="id_name_error"' in body


def test_invalid_post_without_htmx_rerenders_the_full_page_with_422(
    client: Client,
) -> None:
    response = client.post("/example/", {"name": ""})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert "<html" in response.content.decode()
    assert 'aria-invalid="true"' in response.content.decode()


def test_valid_htmx_post_redirects_with_hx_redirect(client: Client) -> None:
    response = client.post("/example/", {"name": "Ada"}, headers=HTMX)

    assert response.status_code == HTTPStatus.OK
    assert response["HX-Redirect"] == "/example/"


def test_valid_plain_post_redirects_and_shows_the_message(client: Client) -> None:
    response = client.post("/example/", {"name": "Ada"}, follow=True)

    body = response.content.decode()
    assert response.redirect_chain == [("/example/", HTTPStatus.FOUND)]
    assert "message--success" in body
    assert "Saved." in body
