---
name: htmx-alpine
description: Use when building or reviewing server-rendered Django screens with htmx and Alpine, covering templates, partials, forms, static assets, CSP, translations and accessibility.
---

# htmx-alpine

This is how we build server-rendered screens. The kit layers on the django-drf kit (package `config`, apps under `apps/<domain>/`, the same `make check` and `make check-fast`). The server owns the data, the rules and the HTML. htmx swaps fragments the server renders, and Alpine holds UI state that never leaves the browser.

## Layout

```
templates/base.html                                    page shell every screen extends
apps/<app>/templates/<app>/<screen>.html               one full page per screen
apps/<app>/templates/<app>/partials/<element-id>.html  fragments htmx swaps in
apps/<app>/templates/<app>/components/<name>.html      repeated markup, included
apps/core/htmx.py                                      htmx_screen(), htmx_redirect()
apps/core/templates/core/partials/messages.html        the #messages region
static/css/tokens.css, static/css/app.css              design tokens, shared components
static/js/app.js                                       htmx config, CSRF, focus, Alpine components
static/vendor/                                         htmx, Alpine CSP build, SHA256SUMS (committed)
config/settings/csp.py                                 the Content Security Policy
locale/<lang>/LC_MESSAGES/django.po                    translations (committed; .mo built)
make/htmx-alpine.mk                                    vendor, lint-templates, messages-check
```

The project Makefile ends with `-include make/*.mk`, as the django-drf Makefile does. The fragment adds its targets as prerequisites of `check`, `check-fast` and `format`, because GNU make merges prerequisites declared for the same target. `pyproject.htmx-alpine.toml` is merged into `pyproject.toml` once and then deleted.

`config/settings/base.py` sets `TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]` with `APP_DIRS = True`, sets `STATICFILES_DIRS = [BASE_DIR / "static"]`, and adds `"csp"` and `"django_htmx"` to `INSTALLED_APPS`. In `MIDDLEWARE`, `csp.middleware.CSPMiddleware` goes right after `SecurityMiddleware`, `django.middleware.locale.LocaleMiddleware` after `SessionMiddleware`, and `django_htmx.middleware.HtmxMiddleware` last. Sessions and messages middleware and the `messages` and `request` context processors stay enabled.

## Screens and URLs

Each screen has one URL. The view prepares the context and calls `htmx_screen()`. A plain request gets the full page. An htmx request (`request.htmx` from django-htmx) gets only the named partial, plus `#messages` out of band. Boosted and history-restore requests get the full page. The response carries `Vary: HX-Request` so a cache never serves a fragment as a page. There are no separate fragment URLs, so links, bookmarks and reloads always land on a real page.

```python
def account_details(request: HtmxHttpRequest, pk: int) -> HttpResponse:
    account = get_account_for(request.user, pk)  # the service enforces access
    form = AccountDetailsForm(request.POST or None, instance=account)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, _("Details saved."))
            return htmx_redirect(request, reverse("accounts:detail", args=[pk]))
        status = HTTPStatus.UNPROCESSABLE_ENTITY
    else:
        status = HTTPStatus.OK
    return htmx_screen(
        request,
        "accounts/details.html",
        "accounts/partials/details-form.html",
        {"form": form, "account": account},
        status=status,
    )
```

## Partials

- A partial is named after the element id it replaces: `<app>/partials/<element-id>.html` replaces `#<element-id>`, and its root element carries that id.
- The trigger's `hx-target="#<element-id>"` and `hx-swap="outerHTML"` match the partial's root. The full page `{% include %}`s the same file, so page and fragment never drift.
- Navigations that change the screen use `hx-push-url="true"`. The swapped partial's `h1` carries `data-focus-after-swap`.
- Templates present data. Queries, permissions and business rules stay in the view and the services behind it.

## Requests in flight

- Every triggering control is disabled while its request runs: `hx-disabled-elt="find button[type=submit]"` on forms, and `hx-disabled-elt="this"` on buttons and links.
- `app.js` sets `aria-busy="true"` on the target for the duration of the request. Progress shows as `<span class="htmx-indicator" aria-hidden="true">` inside the control. Its styles live in `app.css`, because htmx's injected styles are switched off for the CSP.
- Failed requests (5xx, network) are announced through `#live-region` using its `data-error-message`, and logged to the console with the response's `X-Request-ID`.

## Forms and validation

- Forms POST to the screen URL. When the form is invalid, the view re-renders the form partial with its errors and status 422. `app.js` tells htmx to swap 422 responses; by default, htmx 2 drops them.
- When the form is valid, `htmx_redirect()` answers `HX-Redirect` for htmx requests, or a 302 for plain ones, and the next screen shows the message. Swap without redirecting only when the user stays on the same screen (an inline row edit), by returning `htmx_screen()` with the updated partial.
- Render fields with `{{ form.<field>.as_field_group }}`. Django 5.2 renders errors as `#<id>_error`, links them with `aria-describedby` and sets `aria-invalid="true"`. After the swap, `app.js` focuses the first invalid field. Non-field errors go at the top of the form partial.
- Validation lives in forms and services. The browser never decides whether data is valid.
- Outcomes that are not field errors go through `django.contrib.messages`. They render in `core/partials/messages.html`, both in the page and out of band on every htmx response.

## Client code

- Alpine holds UI state only, such as open or closed, the selected tab, or a character count. Business logic, data rules, prices, permissions and validation never run in the browser.
- Components are registered with `Alpine.data("name", ...)` inside the `alpine:init` listener in `static/js/app.js`, and templates reference them by name: `x-data="disclosure"`. The CSP build cannot evaluate inline objects or statements, so `x-data="{ open: false }"` and `@click="open = !open"` are out. Use property and method names such as `@click="toggle"` and `:aria-expanded="open"`.
- Once `app.js` holds more than a few components, each one moves to `static/js/components/<name>.js` and is loaded with `defer` before Alpine in `base.html`.
- Pass server data to scripts with `{{ value|json_script:"element-id" }}`. Never interpolate it into JavaScript.
- A new library or a bundler needs authorisation. htmx and Alpine cover screens.

## CSP

- The policy lives in `config/settings/csp.py` and is enforced by django-csp 4.x on Django 5.2. It sets `default-src 'self'`. `script-src`, `style-src`, `img-src`, `font-src`, `connect-src` and `form-action` are `'self'`. `object-src`, `base-uri` and `frame-ancestors` are `'none'`. It has no `'unsafe-inline'`, no `'unsafe-eval'`, no nonces and no hashes.
- So templates contain no inline `<script>` or `<style>`, no `style=""`, no `on*=` handlers, no `hx-on`, and no `js:` or `javascript:` values. `apps/core/tests/test_template_rules.py` fails on each of these.
- htmx is configured in `app.js` with `allowEval=false`, `allowScriptTags=false`, `includeIndicatorStyles=false`, an empty `inlineScriptNonce` and `selfRequestsOnly=true`. It also sets `historyCacheSize=0` with `refreshOnHistoryMiss=true`, so no screen with customer data is copied into `sessionStorage`.
- The CSRF token comes from `<meta name="csrf-token">`, which `app.js` reads and sends as `X-CSRFToken` on every non-GET request.
- A new origin (fonts, maps, analytics) is a policy change. It is added in `csp.py` with a comment giving the reason, and reviewed like code.

Deviate on Django 6.0+: use the built-in `SECURE_CSP` setting and `django.middleware.csp.ContentSecurityPolicyMiddleware` with the same directives instead of django-csp.

## Vendored libraries

- htmx 2.0.11 (`htmx.org`, `dist/htmx.min.js`) and the Alpine 3.17.5 CSP build (`@alpinejs/csp`, `dist/cdn.min.js`) are committed as `static/vendor/htmx.min.js` and `static/vendor/alpine-csp.min.js`. The versions are set in `make/htmx-alpine.mk` and the sha256 sums in `static/vendor/SHA256SUMS`.
- `make vendor` downloads the pinned files and installs them only if they match `SHA256SUMS`. `make vendor-check` verifies the committed files offline, and runs in both `check` and `check-fast`.
- Pages never load anything from a CDN. Django's static pipeline serves our own copies.
- To upgrade, bump the version, run `make vendor` (it fails on the new hash), check the file against the npm `integrity` of the release, replace its line in `SHA256SUMS`, read the changelog and commit everything together. We stay on htmx 2.x. htmx 4 is a separate migration.

## Design tokens

- Every raw value (colour, type, space, radius, focus ring, motion) is a custom property in `static/css/tokens.css`. Components in `app.css` and app stylesheets use `var(--token)` only, with no arbitrary values and no inline `style`. The template-rules test fails on raw colours outside `tokens.css`.
- Text tokens meet WCAG 2.2 AA at 4.5:1 on the surfaces, and borders and focus at 3:1. A new colour token states its contrast pair in a comment.
- Existing components are reused. Markup that repeats becomes an include under `<app>/components/`.

## Translations

- Every user-facing string is translated: `{% translate %}` and `{% blocktranslate %}` in templates, `gettext` and `gettext_lazy` in Python. This covers labels, messages, `aria-label`s and the live-region text. Source strings are English and use the project's glossary terms.
- The settings are `USE_I18N = True`, `LOCALE_PATHS = [BASE_DIR / "locale"]` and `LANGUAGES` listing the product's languages, with `LocaleMiddleware` enabled.
- `make messages` refreshes the catalogues (`makemessages --all --no-location --no-obsolete`). To add a language, run `uv run python manage.py makemessages -l <lang> --no-location`, translate, and remove the header's `#, fuzzy` flag.
- `make messages-check` runs in `make check`. It fails when the catalogues are stale against the code or have fuzzy or untranslated entries, and it compiles them. `.po` files are committed. `.mo` files are gitignored and compiled in the image build.

## Accessibility checklist

- [ ] Semantic HTML: one `h1` per screen, landmarks, buttons for actions, links for navigation, real lists and tables.
- [ ] Every control has a visible `<label>`. Errors are linked by `aria-describedby` and `aria-invalid` is set.
- [ ] Everything works from the keyboard, with a visible focus ring, no traps and a working skip link.
- [ ] After a swap, focus moves (to the first invalid field or the `data-focus-after-swap` heading) or the change is announced (`data-announce` goes to `#live-region`, and outcomes appear in `#messages`).
- [ ] No meaning is carried by colour alone. Messages and errors carry text.
- [ ] Contrast comes from tokens only, and motion respects `prefers-reduced-motion`.
- [ ] `<html lang>` is set, each screen has a `<title>`, and images have `alt`.

## Template linting

djLint runs with the Django profile (`[tool.djlint]` in `pyproject.toml`). `make lint-templates` runs `djlint templates apps --lint` and `--check` in both `make check-fast` and `make check`, and `make format` reformats templates. A lint failure is fixed in the template, never by adding a rule to `ignore`.

## Tests

pytest-django tests live in `apps/<app>/tests/`. For each screen:

- A plain GET returns the full page. An htmx GET (`client.get(url, headers={"HX-Request": "true"})`) returns only the partial, whose root has the target id.
- An invalid POST returns 422 with the partial, `aria-invalid="true"` and the linked `#<id>_error`.
- A valid POST answers `HX-Redirect` to htmx and a 302 without it.

The kit's `apps/core/tests/` cover `htmx_screen()`, the CSP header, and the template and stylesheet rules across every template in the project. Keep them green.

Browser tests use Playwright through `pytest-playwright` against `live_server`, marked `slow` so `check-fast` skips them. Each screen gets one smoke test covering the swap, focus after the swap, and a console free of CSP violations.

## Templates

| Concern | Template to copy | Edit after copying |
|---|---|---|
| Page shell, skip link, live region, script order | `templates/base.html` | nothing |
| Messages region (page and out of band) | `apps/core/templates/core/partials/messages.html` | nothing |
| Full page or partial helper, redirects | `apps/core/htmx.py` | nothing |
| Helper, CSP and template-rule tests | `apps/core/tests/htmx_urls.py`, `test_htmx_screen.py`, `test_csp_header.py`, `test_template_rules.py` | nothing |
| Design tokens | `static/css/tokens.css` | brand values; keep the names |
| Base styles and shared components | `static/css/app.css` | nothing |
| htmx config, CSRF, focus, Alpine components | `static/js/app.js` | add components |
| Pinned library checksums | `static/vendor/SHA256SUMS` | nothing; then run `make vendor` and commit the two files |
| Content Security Policy | `config/settings/csp.py` | nothing; import from `config/settings/base.py` |
| Dependencies and djLint config | `pyproject.htmx-alpine.toml` | merge into `pyproject.toml`, then delete |
| Make targets | `make/htmx-alpine.mk` | nothing; the django-drf Makefile already ends with `-include make/*.mk` |
| Catalogue directory | `locale/.gitkeep` | nothing |
