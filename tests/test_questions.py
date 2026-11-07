import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from oees_agents.questions import (
    Answers,
    Flags,
    LinePrompter,
    QuestionError,
    Suggestions,
    ask,
    detect,
)

from conftest import KITS, write

ALL_DEFAULTS = ("tdd", "git", "observability")
SUGGESTIONS = Suggestions(
    targets=("claude",), name="octohub", default_branch="main", kits=("django-drf",)
)


class Scripted:
    """Answers questions from a list and records what was asked."""

    def __init__(self, *answers: object) -> None:
        self.answers = list(answers)
        self.asked: list[str] = []

    def text(self, message: str, default: str) -> str:
        return str(self._next(message, default))

    def select(self, message: str, choices: Sequence[str], default: str) -> str:
        return str(self._next(message, default))

    def checkbox(self, message: str, choices: Sequence[str], default: Sequence[str]) -> list[str]:
        answer = self._next(message, list(default))
        assert isinstance(answer, list)
        return [str(item) for item in answer]

    def _next(self, message: str, default: object) -> object:
        self.asked.append(message)
        answer = self.answers.pop(0)
        return default if answer is ... else answer


def run_ask(flags: Flags, prompter: Scripted | None) -> Answers:
    return ask(
        flags,
        SUGGESTIONS,
        defaults=ALL_DEFAULTS,
        kits=KITS,
        loops=("tier-0",),
        prompter=prompter,
    )


def test_questions_are_asked_in_the_planned_order() -> None:
    prompter = Scripted(..., ..., "A platform.", "partners", ..., ..., ..., ..., ..., ..., ..., ...)

    run_ask(Flags(), prompter)

    assert [message.split(" (")[0].split("?")[0] for message in prompter.asked] == [
        "Targets",
        "Project name",
        "One-paragraph description",
        "Who uses it",
        "Blast radius",
        "Default branch",
        "Full check command",
        "Fast check command",
        "Kits",
        "Defaults to keep",
        "Subagents",
        "Loops",
    ]


def test_suggestions_are_the_defaults() -> None:
    prompter = Scripted(..., ..., "A platform.", "partners", ..., ..., ..., ..., ..., ..., ..., ...)

    answers = run_ask(Flags(), prompter)

    assert answers.targets == ("claude",)
    assert answers.kits == ("django-drf",)
    assert answers.defaults == ALL_DEFAULTS
    assert answers.project.name == "octohub"
    assert answers.project.check == "make check"


def test_a_flag_answers_its_question_so_it_is_not_asked() -> None:
    prompter = Scripted(..., ..., ..., ..., ..., ..., ..., ..., ...)

    run_ask(
        Flags(description="A platform.", users="partners", kits=("fastapi",)),
        prompter,
    )

    assert not any(
        message.startswith(("One-paragraph", "Who uses", "Kits")) for message in prompter.asked
    )


def test_no_default_flags_answer_the_defaults_question() -> None:
    flags = Flags(description="d", users="u", no_defaults=("git",))

    answers = run_ask(flags, None)

    assert answers.defaults == ("tdd", "observability")


def test_with_yes_every_unanswered_question_takes_its_default() -> None:
    answers = run_ask(Flags(description="d", users="u"), None)

    assert answers.targets == ("claude",)
    assert answers.extras.subagents == "core"
    assert answers.extras.loops == ()


@pytest.mark.parametrize(
    ("flags", "option"),
    [(Flags(users="u"), "--description"), (Flags(description="d"), "--users")],
)
def test_with_yes_the_questions_without_a_default_need_their_flag(
    flags: Flags, option: str
) -> None:
    with pytest.raises(QuestionError, match=option):
        run_ask(flags, None)


@pytest.mark.parametrize(
    ("flags", "message"),
    [
        (Flags(description="d", users="u", kits=("rails",)), "unknown kit 'rails'"),
        (Flags(description="d", users="u", no_defaults=("yolo",)), "unknown default 'yolo'"),
        (Flags(description="d", users="u", targets=("windsurf",)), "unknown target 'windsurf'"),
        (Flags(description="d", users="u", blast_radius="huge"), "blast radius"),
        (Flags(description="d", users="u", subagents="all"), "subagents"),
        (Flags(description="d", users="u", loops=("tier-9",)), "unknown loop 'tier-9'"),
    ],
)
def test_invalid_flag_values_are_rejected(flags: Flags, message: str) -> None:
    with pytest.raises(QuestionError, match=message):
        run_ask(flags, None)


def test_detect_suggests_targets_from_what_exists(tmp_path: Path) -> None:
    (tmp_path / ".cursor").mkdir()
    write(tmp_path / "AGENTS.md", "local\n")

    assert detect(tmp_path, KITS).targets == ("cursor", "codex")


def test_detect_suggests_every_target_in_an_empty_repository(tmp_path: Path) -> None:
    assert detect(tmp_path, KITS).targets == ("claude", "cursor", "codex")


def test_detect_names_the_project_after_its_directory(tmp_path: Path) -> None:
    project = tmp_path / "hermes"
    project.mkdir()

    assert detect(project, KITS).name == "hermes"


def test_detect_reads_the_default_branch_from_origin_head(tmp_path: Path) -> None:
    upstream = tmp_path / "upstream"
    subprocess.run(["git", "init", "-q", "-b", "trunk", str(upstream)], check=True)
    subprocess.run(
        ["git", "-C", str(upstream), "commit", "-q", "--allow-empty", "-m", "start"],
        check=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "PATH": "/usr/bin:/bin",
        },
    )
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(upstream), str(clone)], check=True)

    assert detect(clone, KITS).default_branch == "trunk"


def test_detect_falls_back_to_main_outside_git(tmp_path: Path) -> None:
    assert detect(tmp_path, KITS).default_branch == "main"


@pytest.mark.parametrize(
    ("path", "text", "kit"),
    [
        ("manage.py", "", "django-drf"),
        ("backend/manage.py", "", "django-drf"),
        ("pyproject.toml", 'dependencies = ["fastapi>=0.110"]\n', "fastapi"),
        ("requirements.txt", "FastAPI==0.110\n", "fastapi"),
        ("app/templates/home.html", '<button hx-post="/go">', "htmx-alpine"),
    ],
)
def test_detect_hints_kits_from_the_repository(
    tmp_path: Path, path: str, text: str, kit: str
) -> None:
    write(tmp_path / path, text)

    assert detect(tmp_path, KITS).kits == (kit,)


def test_detect_only_suggests_kits_the_content_has(tmp_path: Path) -> None:
    write(tmp_path / "manage.py", "")

    assert detect(tmp_path, ("fastapi",)).kits == ()


def test_the_line_prompter_reads_piped_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    replies = iter(["", "fastapi, htmx-alpine", "-", "extended"])
    monkeypatch.setattr("typer.prompt", lambda *_, **kwargs: next(replies) or kwargs["default"])
    prompter = LinePrompter()

    assert prompter.text("Name", "octohub") == "octohub"
    assert prompter.checkbox("Kits", ["fastapi", "htmx-alpine"], []) == ["fastapi", "htmx-alpine"]
    assert prompter.checkbox("Loops", ["tier-0"], ["tier-0"]) == []
    assert prompter.select("Subagents", ["none", "core", "extended"], "core") == "extended"


def test_the_line_prompter_rejects_choices_it_does_not_offer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("typer.prompt", lambda *_, **__: "rails")

    with pytest.raises(QuestionError, match="rails"):
        LinePrompter().checkbox("Kits", ["fastapi"], [])
