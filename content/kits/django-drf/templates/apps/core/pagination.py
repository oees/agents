"""The one pagination class every list endpoint uses (`DEFAULT_PAGINATION_CLASS`).

Response shape:
    {"count": int, "next": url | null, "previous": url | null, "results": [...]}
"""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
