from typing import Any
from unittest.mock import patch

from celery import shared_task
from django.conf import settings
from structlog.contextvars import bind_contextvars, get_contextvars

from apps.core.celery_signals import (
    bind_task_context,
    propagate_request_id,
    unbind_task_context,
    use_django_logging,
)


@shared_task
def capture_context() -> dict[str, Any]:
    return dict(get_contextvars())


def test_tasks_log_with_their_id_and_name() -> None:
    result = capture_context.apply(task_id="task-1")

    assert result.get() == {
        "task_id": "task-1",
        "task_name": "apps.core.tests.test_celery_signals.capture_context",
    }


def test_tasks_carry_the_request_id_of_the_request_that_queued_them() -> None:
    result = capture_context.apply(task_id="task-2", headers={"request_id": "req-5"})

    assert result.get()["request_id"] == "req-5"


def test_an_inline_task_restores_its_callers_context() -> None:
    bind_contextvars(request_id="req-6")

    capture_context.apply(task_id="task-3")

    assert get_contextvars() == {"request_id": "req-6"}


def test_a_worker_task_starts_from_a_clean_context() -> None:
    bind_contextvars(stale="from-a-previous-task")
    # celery-types types push_request with the task's own parameters; Celery takes
    # request fields.
    capture_context.push_request(is_eager=False, headers=None)  # type: ignore[call-arg]
    try:
        bind_task_context(task_id="task-4", task=capture_context)
        bound = dict(get_contextvars())
        unbind_task_context(task_id="task-4")
    finally:
        capture_context.pop_request()

    assert "stale" not in bound
    assert bound["task_id"] == "task-4"


def test_publishing_copies_the_current_request_id_into_the_headers() -> None:
    bind_contextvars(request_id="req-7")
    headers: dict[str, Any] = {}

    propagate_request_id(headers=headers)

    assert headers == {"request_id": "req-7"}


def test_publishing_outside_a_request_adds_nothing() -> None:
    headers: dict[str, Any] = {}

    propagate_request_id(headers=headers)

    assert headers == {}


def test_the_worker_logs_with_the_django_logging_config() -> None:
    with patch("apps.core.celery_signals.logging.config.dictConfig") as dict_config:
        use_django_logging()

    dict_config.assert_called_once_with(settings.LOGGING)
