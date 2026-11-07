"""Rules the CSP and the design tokens depend on, checked on templates and CSS."""

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from django.conf import settings

BASE_DIR = Path(settings.BASE_DIR)
IDENTIFIER = re.compile(r"[A-Za-z_$][\w$]*")
RAW_COLOUR = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\("
)
EXTERNAL = ("http://", "https://", "//")


class TemplateRules(HTMLParser):
    """Collects CSP and Alpine CSP-build violations in one template's markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.violations: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        names = dict(attrs)
        if tag == "script" and "src" not in names:
            self.violations.append("inline <script>")
        if tag == "style":
            self.violations.append("inline <style>")
        if tag in ("script", "link") and (
            names.get("src") or names.get("href") or ""
        ).startswith(EXTERNAL):
            self.violations.append(f"external <{tag}> (vendor it under static/vendor/)")
        for name, value in attrs:
            text = (value or "").strip()
            if name == "style":
                self.violations.append("style attribute")
            elif name.startswith("on"):
                self.violations.append(f"inline event handler {name}")
            elif name.startswith(("hx-on", "data-hx-on")):
                self.violations.append(f"{name} needs eval")
            elif text.startswith("js:") or text.startswith("javascript:"):
                self.violations.append(f"{name} evaluates script")
            elif name == "x-data" and text and not IDENTIFIER.fullmatch(text):
                self.violations.append(
                    "x-data must name a component registered with Alpine.data()"
                )


def violations_in(markup: str) -> list[str]:
    parser = TemplateRules()
    parser.feed(markup)
    parser.close()
    return parser.violations


def project_templates() -> list[Path]:
    roots = [BASE_DIR / "templates", *sorted((BASE_DIR / "apps").glob("*/templates"))]
    return sorted(path for root in roots for path in root.rglob("*.html"))


def project_stylesheets() -> list[Path]:
    return sorted(
        path
        for path in (BASE_DIR / "static" / "css").rglob("*.css")
        if path.name != "tokens.css"
    )


@pytest.mark.parametrize(
    ("markup", "expected"),
    [
        ("<script>alert(1)</script>", "inline <script>"),
        ("<style>p {}</style>", "inline <style>"),
        ('<p style="color: red">x</p>', "style attribute"),
        ('<button onclick="go()">x</button>', "inline event handler onclick"),
        ('<form hx-on::after-request="x()"></form>', "hx-on::after-request needs eval"),
        ("<div hx-vals='js:{a: 1}'></div>", "hx-vals evaluates script"),
        (
            '<div x-data="{ open: false }"></div>',
            "x-data must name a component registered with Alpine.data()",
        ),
        (
            '<script src="https://unpkg.com/htmx.org"></script>',
            "external <script> (vendor it under static/vendor/)",
        ),
    ],
)
def test_rules_catch_each_violation(markup: str, expected: str) -> None:
    assert expected in violations_in(markup)


def test_rules_accept_csp_safe_markup() -> None:
    markup = (
        '<script src="/static/js/app.js" defer></script>'
        '<div x-data="disclosure">'
        '<button type="button" @click="toggle" :aria-expanded="open">x</button>'
        "</div>"
        '<form hx-post="/a/" hx-target="#a" hx-disabled-elt="find button"></form>'
    )
    assert violations_in(markup) == []


def test_project_has_templates_to_check() -> None:
    assert (BASE_DIR / "templates" / "base.html") in project_templates()


@pytest.mark.parametrize(
    "path", project_templates(), ids=lambda path: str(path.relative_to(BASE_DIR))
)
def test_template_is_csp_safe(path: Path) -> None:
    assert violations_in(path.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    "path", project_stylesheets(), ids=lambda path: str(path.relative_to(BASE_DIR))
)
def test_stylesheet_uses_tokens_for_colour(path: Path) -> None:
    assert RAW_COLOUR.findall(path.read_text(encoding="utf-8")) == []
