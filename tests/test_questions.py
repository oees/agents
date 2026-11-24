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
    ask_scope,
    detect,
    detect_machine,
)

from conftest import KITS, write

ALL_DEFAULTS = ("tdd", "git", "observability")
SUGGESTIONS = Suggestions(
    targets=("claude",), name="portal", default_branch="main", kits=("django-drf",)
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
        prompter=prompter,
        scope="project",
    )


def test_questions_are_asked_in_the_planned_order() -> None:
    prompter = Scripted(..., ..., "A platform.", "partners", ..., ..., ..., ..., ..., ..., ...)

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
    ]


def test_suggestions_are_the_defaults() -> None:
    prompter = Scripted(..., ..., "A platform.", "partners", ..., ..., ..., ..., ..., ..., ...)

    answers = run_ask(Flags(), prompter)

    assert answers.targets == ("claude",)
    assert answers.kits == ("django-drf",)
    assert answers.defaults == ALL_DEFAULTS
    assert answers.project is not None
    assert answers.project.name == "portal"
    assert answers.project.check == "make check"


def test_a_flag_answers_its_question_so_it_is_not_asked() -> None:
    prompter = Scripted(..., ..., ..., ..., ..., ..., ..., ...)

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
    project = tmp_path / "relay"
    project.mkdir()

    assert detect(project, KITS).name == "relay"


def test_detect_reads_the_default_branch_from_origin_head(tmp_path: Path) -> None:
    upstream = tmp_path / "upstream"
    subprocess.run(["git", "init", "-q", "-b", "trunk", str(upstream)], check=True)
    subprocess.run(
        ["git", "-C", str(upstream), "commit", "-q", "--allow-empty", "-m", "start"],
        check=True,
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

    assert prompter.text("Name", "portal") == "portal"
    assert prompter.checkbox("Kits", ["fastapi", "htmx-alpine"], []) == ["fastapi", "htmx-alpine"]
    assert prompter.checkbox("Defaults to keep", ["tdd"], ["tdd"]) == []
    assert prompter.select("Subagents", ["none", "core", "extended"], "core") == "extended"


def test_a_typed_answer_that_is_not_offered_is_rejected() -> None:
    flags = Flags(targets=("claude",), description="d", users="u")
    prompter = Scripted(..., ..., ..., ..., ..., ["rails"])

    with pytest.raises(QuestionError, match="unknown kit 'rails'"):
        run_ask(flags, prompter)


def test_init_needs_at_least_one_target() -> None:
    with pytest.raises(QuestionError, match="at least one target"):
        run_ask(Flags(description="d", users="u"), Scripted([]))


def run_machine_ask(flags: Flags, prompter: Scripted | None) -> Answers:
    return ask(
        flags,
        detect_machine(Path("/nonexistent-home")),
        defaults=ALL_DEFAULTS,
        kits=KITS,
        prompter=prompter,
        scope="machine",
    )


def test_scope_is_the_first_question_and_defaults_to_the_project() -> None:
    prompter = Scripted(...)

    assert ask_scope(Flags(), prompter) == "project"
    assert prompter.asked[0].startswith("Install for")
    assert ask_scope(Flags(), None) == "project"
    assert ask_scope(Flags(scope="machine"), None) == "machine"


def test_a_machine_install_asks_no_project_questions() -> None:
    prompter = Scripted(..., ..., ..., ...)

    answers = run_machine_ask(Flags(), prompter)

    assert [message.split(" (")[0] for message in prompter.asked] == [
        "Targets",
        "Kits",
        "Defaults to keep",
        "Subagents",
    ]
    assert answers.project is None
    assert answers.targets == ("claude", "codex")
    assert answers.kits == ()


def test_a_machine_install_refuses_cursor() -> None:
    with pytest.raises(QuestionError, match="Cursor has no machine-wide rules"):
        run_machine_ask(Flags(targets=("claude", "cursor")), None)
