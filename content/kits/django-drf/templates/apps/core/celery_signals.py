"""Celery signal handlers: JSON logging in the worker, task ids on every task log line.

Every log line inside a task carries `task_id` and `task_name`. The publishing side
copies the current `request_id` into the task headers, so a task started by an API
request logs with the same `request_id` as the request. Imported by `config.celery`,
which connects the handlers in both the web process and the worker.
"""

import contextvars
import logging.config
from collections.abc import Mapping
from typing import Any

from celery import Task
from celery.signals import before_task_publish, setup_logging, task_postrun, task_prerun
from django.conf import settings
from structlog.contextvars import (
    bind_contextvars,
    clear_contextvars,
    get_contextvars,
    reset_contextvars,
)

from apps.core.logging import configure_structlog

REQUEST_ID_HEADER = "request_id"

# Context tokens per running task, so an eager task (tests, local) restores its
# caller's context.
_task_tokens: dict[str, Mapping[str, contextvars.Token[Any]]] = {}


@setup_logging.connect
def use_django_logging(**_kwargs: Any) -> None:
    """Stop Celery installing its own handlers; the worker logs like the web process."""
    logging.config.dictConfig(settings.LOGGING)
    configure_structlog()


@before_task_publish.connect
def propagate_request_id(headers: dict[str, Any] | None = None, **_kwargs: Any) -> None:
    request_id = get_contextvars().get("request_id")
    if headers is not None and request_id is not None:
        headers.setdefault(REQUEST_ID_HEADER, request_id)


@task_prerun.connect
def bind_task_context(task_id: str, task: Task[..., Any], **_kwargs: Any) -> None:
    if not task.request.is_eager:
        clear_contextvars()
    context: dict[str, Any] = {"task_id": task_id, "task_name": task.name}
    request_id = _incoming_request_id(task)
    if request_id is not None:
        context["request_id"] = request_id
    _task_tokens[task_id] = bind_contextvars(**context)


@task_postrun.connect
def unbind_task_context(task_id: str, **_kwargs: Any) -> None:
    tokens = _task_tokens.pop(task_id, None)
    if tokens is not None:
        reset_contextvars(**tokens)


def _incoming_request_id(task: Task[..., Any]) -> str | None:
    headers = task.request.headers or {}
    value = headers.get(REQUEST_ID_HEADER) or getattr(
        task.request, REQUEST_ID_HEADER, None
    )
    return str(value) if value else None
