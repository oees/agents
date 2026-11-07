# syntax=docker/dockerfile:1

# Stages: builder (dependencies, compiled translations, static files), dev (compose and
# `make check`), runtime (last, the default target: what CI builds and App Platform runs).

FROM ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 AS uv

FROM python:3.13.18-slim-bookworm@sha256:a5a7017efc5969e00ae2b91c8eb0631049a569652aa4ffc4501769049ae45c72 AS python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

FROM python AS builder
COPY --from=uv /uv /uvx /bin/
RUN apt-get update \
    && apt-get install --yes --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project
COPY . .
# Placeholders satisfy the production settings for these build steps; none reach the image.
# compilemessages runs only when the project has .po files of its own.
RUN export PATH="/app/.venv/bin:$PATH" \
        DJANGO_SETTINGS_MODULE=config.settings.production \
        DJANGO_SECRET_KEY=build-only DATABASE_URL=sqlite:///:memory: \
        DJANGO_ALLOWED_HOSTS=localhost DJANGO_CSRF_TRUSTED_ORIGINS=https://localhost \
        REDIS_URL=redis://localhost:6379/0 \
    && if find . -path ./.venv -prune -o -name '*.po' -print | grep -q .; then \
        python manage.py compilemessages --ignore .venv; \
    fi \
    && python manage.py collectstatic --noinput

FROM python AS dev
COPY --from=uv /uv /uvx /bin/
# git: make fragments compare generated files with the bind-mounted checkout.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends gettext git make \
    && rm -rf /var/lib/apt/lists/* \
    && git config --system --add safe.directory /app
# The source is bind-mounted over /app in compose, so the environment lives outside it.
ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM python AS runtime
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home app
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]
CMD ["gunicorn", "--config", "python:config.gunicorn", "config.wsgi:application"]
