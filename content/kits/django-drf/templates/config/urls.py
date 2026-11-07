"""URL root. `HealthCheckMiddleware` answers `/healthz` and `/readyz` before routing."""

from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)

# Every domain app registers its ViewSets here, e.g.
# router.register("invoices", InvoiceViewSet, basename="invoice")
router = DefaultRouter()

api_v1: list[URLPattern | URLResolver] = [
    path("", include(router.urls)),
    path("auth/token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/token/blacklist/", TokenBlacklistView.as_view(), name="token-blacklist"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
]

handler404 = "apps.core.views.not_found"
handler500 = "apps.core.views.server_error"
