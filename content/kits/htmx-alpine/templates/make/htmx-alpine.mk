# htmx-alpine kit targets. The project Makefile includes this file with
# `-include make/*.mk` as its last line (the django-drf Makefile does), which adds the prerequisites below to
# the existing check, check-fast and format targets (GNU make merges them).
# Needs: curl and sha256sum (vendor), gettext and git (messages-check).

HTMX_VERSION := 2.0.11
ALPINE_CSP_VERSION := 3.17.5
VENDOR_DIR := static/vendor
TEMPLATE_DIRS := templates apps

.PHONY: vendor vendor-check lint-templates format-templates messages messages-check

check-fast: vendor-check lint-templates
check: vendor-check lint-templates messages-check
format: format-templates

# Download the pinned libraries, verify them against SHA256SUMS, then install.
# To upgrade: bump the version above, run this, check the new file against the
# npm `integrity` of the release, then replace its line in SHA256SUMS.
vendor:
	tmp="$$(mktemp -d)"; trap 'rm -rf "$$tmp"' EXIT; \
	curl -fsSL --proto '=https' -o "$$tmp/htmx.min.js" \
	  "https://unpkg.com/htmx.org@$(HTMX_VERSION)/dist/htmx.min.js"; \
	curl -fsSL --proto '=https' -o "$$tmp/alpine-csp.min.js" \
	  "https://unpkg.com/@alpinejs/csp@$(ALPINE_CSP_VERSION)/dist/cdn.min.js"; \
	cp "$(VENDOR_DIR)/SHA256SUMS" "$$tmp/"; \
	(cd "$$tmp" && sha256sum --check --strict SHA256SUMS); \
	cp "$$tmp/htmx.min.js" "$$tmp/alpine-csp.min.js" "$(VENDOR_DIR)/"

# The committed files are the ones we pinned.
vendor-check:
	cd "$(VENDOR_DIR)" && sha256sum --check --strict SHA256SUMS

lint-templates:
	uv run djlint $(TEMPLATE_DIRS) --lint
	uv run djlint $(TEMPLATE_DIRS) --check

# djLint exits 1 when it rewrote a file; the check after it decides the result.
format-templates:
	uv run djlint $(TEMPLATE_DIRS) --reformat --quiet || uv run djlint $(TEMPLATE_DIRS) --check --quiet

# Refresh the catalogues after adding or changing strings.
messages:
	uv run python manage.py makemessages --all --no-location --no-obsolete

# Catalogues match the code, have no fuzzy or untranslated entries, and compile.
messages-check:
	uv run python manage.py makemessages --all --no-location --no-obsolete
	git diff --exit-code -I '^"POT-Creation-Date: ' -- locale/ || \
	  { echo "locale/ is stale: run 'make messages', translate, commit"; exit 1; }
	for po in $$(find locale -name '*.po'); do \
	  if [ "$$(msgattrib --only-fuzzy "$$po" | grep -c '^msgid ')" -gt 0 ]; then \
	    echo "fuzzy entries in $$po"; exit 1; fi; \
	  if [ "$$(msgattrib --untranslated --no-obsolete "$$po" | grep -c '^msgid ')" -gt 0 ]; then \
	    echo "untranslated entries in $$po"; exit 1; fi; \
	done
	uv run python manage.py compilemessages --ignore=.venv
