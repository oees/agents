"""Test-only URLconf: one screen with a form, built the way real screens are built.

Strings stay untranslated here so test fixtures never reach the catalogues.
"""

from http import HTTPStatus

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.urls import path, reverse
from pytest_django import Settings

from apps.core.htmx import HtmxHttpRequest, htmx_redirect, htmx_screen

SCREEN = "example/screen.html"
FORM_PARTIAL = "example/partials/example-form.html"

TEMPLATES = {
    SCREEN: """{% extends "base.html" %}
{% block title %}Example{% endblock title %}
{% block content %}<h1>Example</h1>
{% include "example/partials/example-form.html" %}
{% endblock content %}""",
    FORM_PARTIAL: """<form id="example-form" method="post" action="/example/" novalidate
      hx-post="/example/" hx-target="#example-form" hx-swap="outerHTML"
      hx-disabled-elt="find button[type=submit]">
  {% csrf_token %}
  {{ form.name.as_field_group }}
  <button type="submit">Save</button>
</form>""",
}


def use_example_templates(settings: Settings) -> None:
    """Serve the example templates from memory, ahead of the project's own loaders."""
    engine = {**settings.TEMPLATES[0]}
    options = {**engine.get("OPTIONS", {})}
    options["loaders"] = [
        ("django.template.loaders.locmem.Loader", TEMPLATES),
        "django.template.loaders.filesystem.Loader",
        "django.template.loaders.app_directories.Loader",
    ]
    engine["OPTIONS"] = options
    engine["APP_DIRS"] = False
    settings.TEMPLATES = [engine, *settings.TEMPLATES[1:]]


class ExampleForm(forms.Form):
    name = forms.CharField(label="Name", max_length=50)


def example_screen(request: HtmxHttpRequest) -> HttpResponse:
    form = ExampleForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            messages.success(request, "Saved.")
            return htmx_redirect(request, reverse("example"))
        return htmx_screen(
            request,
            SCREEN,
            FORM_PARTIAL,
            {"form": form},
            status=HTTPStatus.UNPROCESSABLE_ENTITY,
        )
    return htmx_screen(request, SCREEN, FORM_PARTIAL, {"form": form})


urlpatterns = [path("example/", example_screen, name="example")]
