import importlib
import sys
from types import ModuleType

import pytest
from django.core.exceptions import ImproperlyConfigured

PRODUCTION = "config.settings.production"
PRODUCTION_ENV = {
    "DJANGO_SECRET_KEY": "placeholder-for-tests",
    "DJANGO_ALLOWED_HOSTS": "api.example.com,app.example.com",
    "DJANGO_CSRF_TRUSTED_ORIGINS": "https://app.example.com",
    "REDIS_URL": "redis://redis.example.com:6379/0",
}


def _load_production(
    monkeypatch: pytest.MonkeyPatch, **overrides: str | None
) -> ModuleType:
    for key, value in {**PRODUCTION_ENV, **overrides}.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    monkeypatch.delitem(sys.modules, PRODUCTION, raising=False)
    return importlib.import_module(PRODUCTION)


def test_production_is_never_in_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    production = _load_production(monkeypatch, DJANGO_DEBUG="True")

    assert production.DEBUG is False


def test_production_trusts_the_platform_proxy_and_forces_https(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    production = _load_production(monkeypatch)

    assert production.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert production.SECURE_SSL_REDIRECT is True
    assert production.SECURE_HSTS_SECONDS >= 31_536_000
    assert production.SESSION_COOKIE_SECURE is True
    assert production.CSRF_COOKIE_SECURE is True


def test_production_reads_hosts_and_origins_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    production = _load_production(monkeypatch)

    assert production.ALLOWED_HOSTS == ["api.example.com", "app.example.com"]
    assert production.CSRF_TRUSTED_ORIGINS == ["https://app.example.com"]


@pytest.mark.parametrize("missing", sorted(PRODUCTION_ENV))
def test_production_refuses_to_start_without_required_settings(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    with pytest.raises(ImproperlyConfigured):
        _load_production(monkeypatch, **{missing: None})
