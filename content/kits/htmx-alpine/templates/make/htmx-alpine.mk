# htmx-alpine kit targets. The project Makefile includes this file with
# `-include make/*.mk` as its last line (the django-drf Makefile does), which adds the prerequisites below to
# the existing check, check-fast and format targets (GNU make merges them).
# Needs: curl and sha256sum (vendor), gettext and diff (messages-check), and RUN
# (uv run --locked) from the project Makefile.

HTMX_VERSION := 2.0.11
ALPINE_CSP_VERSION := 3.17.5
VENDOR_DIR := static/vendor
TEMPLATE_DIRS := templates apps
# Source strings are in this language, so it needs no catalogue.
SOURCE_LANGUAGE := en

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
	$(RUN) djlint $(TEMPLATE_DIRS) --lint
	$(RUN) djlint $(TEMPLATE_DIRS) --check

# djLint exits 1 when it rewrote a file; the check after it decides the result.
format-templates:
	$(RUN) djlint $(TEMPLATE_DIRS) --reformat --quiet || $(RUN) djlint $(TEMPLATE_DIRS) --check --quiet

# Refresh the catalogues after adding or changing strings.
messages:
	$(RUN) python manage.py makemessages --all --no-location --no-obsolete

# Every language in settings.LANGUAGES except the source language has a catalogue.
# The catalogues match the code, have no fuzzy or untranslated entries, and compile.
# The staleness check compares the catalogues before and after makemessages, so it
# also covers a catalogue that git does not track yet.
messages-check: export DJANGO_SETTINGS_MODULE := config.settings.test
messages-check:
	locales="$$($(RUN) python -c 'import django; django.setup(); from django.conf import settings; from django.utils.translation import to_locale; print(*(to_locale(code) for code, _ in settings.LANGUAGES if code != "$(SOURCE_LANGUAGE)"))')"; \
	for locale in $$locales; do \
	  if [ ! -f "locale/$$locale/LC_MESSAGES/django.po" ]; then \
	    echo "no catalogue for $$locale: run '$(RUN) python manage.py makemessages -l $$locale --no-location', translate, commit"; \
	    exit 1; fi; \
	done
	before="$$(mktemp)"; trap 'rm -f "$$before"' EXIT; \
	snapshot() { for po in $$(find locale -name '*.po' | sort); do echo "== $$po"; grep -v '^"POT-Creation-Date: ' "$$po"; done; }; \
	snapshot > "$$before"; \
	$(RUN) python manage.py makemessages --all --no-location --no-obsolete; \
	snapshot | diff -u "$$before" - || \
	  { echo "locale/ is stale: run 'make messages', translate, commit"; exit 1; }
	for po in $$(find locale -name '*.po'); do \
	  if [ "$$(msgattrib --only-fuzzy "$$po" | grep -c '^msgid ')" -gt 0 ]; then \
	    echo "fuzzy entries in $$po"; exit 1; fi; \
	  if [ "$$(msgattrib --untranslated --no-obsolete "$$po" | grep -c '^msgid ')" -gt 0 ]; then \
	    echo "untranslated entries in $$po"; exit 1; fi; \
	done
	$(RUN) python manage.py compilemessages --ignore=.venv
