from typing import Any

from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory


class NumberSerializer(serializers.Serializer[dict[str, int]]):
    n = serializers.IntegerField()


class NumberList(generics.ListAPIView[Any]):
    permission_classes = (AllowAny,)
    serializer_class = NumberSerializer
    total = 0

    def get_queryset(self) -> Any:
        return [{"n": n} for n in range(self.total)]


def _list(total: int, **params: Any) -> Response:
    request = APIRequestFactory().get("/api/v1/numbers/", params)
    response: Response = NumberList.as_view(total=total)(request)
    return response


def test_lists_are_paginated_with_count_links_and_results() -> None:
    response = _list(120)

    assert response.status_code == 200
    assert set(response.data) == {"count", "next", "previous", "results"}
    assert response.data["count"] == 120
    assert len(response.data["results"]) == 50
    assert response.data["previous"] is None
    assert "page=2" in response.data["next"]


def test_clients_choose_the_page_and_its_size() -> None:
    response = _list(120, page=3, page_size=10)

    assert [item["n"] for item in response.data["results"]] == list(range(20, 30))


def test_page_size_is_capped_at_200() -> None:
    response = _list(500, page_size=1000)

    assert len(response.data["results"]) == 200


def test_a_page_past_the_end_is_a_not_found_error() -> None:
    response = _list(10, page=2)

    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"
