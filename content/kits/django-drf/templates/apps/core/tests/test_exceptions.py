import logging
from typing import Any

import pytest
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.test import Client, RequestFactory
from rest_framework import exceptions, serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.views import APIView
from structlog.contextvars import bind_contextvars

from apps.core.views import server_error


class GreetingSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(max_length=5)
    tags = serializers.ListField(child=serializers.CharField(), min_length=1)


class RaisingView(APIView):
    permission_classes = (AllowAny,)
    raises: Exception = RuntimeError("database password is hunter2")

    def get(self, request: Request) -> Response:
        raise self.raises

    def post(self, request: Request) -> Response:
        serializer = GreetingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


def _call(
    raises: Exception | None = None, method: str = "get", **data: Any
) -> Response:
    factory = APIRequestFactory()
    request = getattr(factory, method)("/api/v1/raising/", data, format="json")
    view = RaisingView.as_view(**({"raises": raises} if raises else {}))
    response: Response = view(request)
    return response


def test_validation_errors_list_messages_per_field() -> None:
    bind_contextvars(request_id="req-1")

    response = _call(method="post", name="too long", tags=[])

    assert response.status_code == 400
    error = response.data["error"]
    assert error["code"] == "validation_error"
    assert error["message"] == "The request is invalid."
    assert error["request_id"] == "req-1"
    assert set(error["details"]) == {"name", "tags"}
    assert all(isinstance(message, str) for message in error["details"]["name"])


def test_django_validation_errors_use_the_same_envelope() -> None:
    response = _call(DjangoValidationError({"email": ["Enter a valid email address."]}))

    assert response.status_code == 400
    assert response.data["error"]["details"] == {
        "email": ["Enter a valid email address."]
    }


def test_non_field_validation_errors_are_grouped() -> None:
    response = _call(exceptions.ValidationError("Dates overlap."))

    assert response.data["error"]["details"] == {"non_field_errors": ["Dates overlap."]}


@pytest.mark.parametrize(
    ("raised", "status_code", "code"),
    [
        (Http404(), 404, "not_found"),
        (DjangoPermissionDenied(), 403, "permission_denied"),
        (exceptions.MethodNotAllowed("PUT"), 405, "method_not_allowed"),
        (exceptions.ParseError(), 400, "parse_error"),
    ],
)
def test_api_errors_carry_a_code_and_a_message(
    raised: Exception, status_code: int, code: str
) -> None:
    response = _call(raised)

    assert response.status_code == status_code
    assert response.data["error"]["code"] == code
    assert response.data["error"]["message"]
    assert response.data["error"]["details"] is None


def test_throttled_responses_say_when_to_retry() -> None:
    response = _call(exceptions.Throttled(wait=30))

    assert response.status_code == 429
    assert response["Retry-After"] == "30"


def test_unexpected_exceptions_are_logged_and_never_leaked(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR)

    response = _call(RuntimeError("database password is hunter2"))

    assert response.status_code == 500
    assert response.data["error"]["code"] == "internal_error"
    assert "hunter2" not in str(response.data)
    [record] = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert isinstance(record.msg, dict)
    assert record.msg["event"] == "unhandled_exception"
    assert isinstance(record.msg["exc_info"], RuntimeError)


def test_unauthenticated_requests_get_401_with_the_request_id(
    api_client: APIClient,
) -> None:
    response = api_client.get("/api/v1/", HTTP_X_REQUEST_ID="abc123")

    assert response.status_code == 401
    assert response["WWW-Authenticate"].startswith("Bearer")
    assert response.json()["error"]["code"] == "not_authenticated"
    assert response.json()["error"]["request_id"] == "abc123"


def test_invalid_tokens_get_401_with_the_token_code(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/", HTTP_AUTHORIZATION="Bearer not-a-jwt")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_not_valid"


def test_unknown_api_urls_get_the_envelope(client: Client) -> None:
    response = client.get("/api/v1/no-such-thing/")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["error"]["request_id"] == response["X-Request-ID"]


def test_unknown_non_api_urls_keep_djangos_page(client: Client) -> None:
    response = client.get("/no-such-page/")

    assert response.status_code == 404
    assert response["Content-Type"].startswith("text/html")


def test_server_errors_outside_drf_views_get_the_envelope_on_api_paths(
    rf: RequestFactory,
) -> None:
    response = server_error(rf.get("/api/v1/things/"))

    assert response.status_code == 500
    assert b'"internal_error"' in response.content
