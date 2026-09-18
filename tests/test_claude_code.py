"""ClaudeCodeProvider against a stand-in program that records what it was sent."""

import asyncio
import time
from pathlib import Path

import pytest

from app.ducks import DUCKS_BY_ID
from app.prompts import user_message
from app.providers import ProviderError, Refused
from app.providers.claude_code import ClaudeCodeProvider
from app.schema import Case, Duck, Origin
from tests.fakes import fake_claude_code, recorded

REPO = Path(__file__).resolve().parent.parent

DUCK = DUCKS_BY_ID["doctor"]
CASE = Case(situation="SITUATION-MARKER leftovers", action="ACTION-MARKER curry")
provider = fake_claude_code


def test_a_structured_verdict_comes_back(record: Path) -> None:
    verdict = asyncio.run(provider().judge(DUCK, CASE))
    assert (verdict.band, verdict.score, verdict.line) == ("sound", 72, "Fine by me.")


def test_every_call_is_locked_down(record: Path) -> None:
    asyncio.run(provider().judge(DUCK, CASE))
    argv = recorded(record)["argv"]
    assert "--bare" not in argv  # would silently switch off the subscription login
    assert argv[argv.index("--tools") + 1] == ""  # no tools at all
    assert "--restricted" in argv
    assert "--no-session-persistence" in argv
    assert "--json-schema" in argv


def test_the_persona_travels_in_a_file_not_as_an_argument(record: Path) -> None:
    written = Duck(
        id="mole",
        name="Mole",
        epithet="Weighs nothing",
        voice="PERSONA-MARKER speaks softly.",
        weighs="Nothing.",
        blind_spot="Everything.",
        origin=Origin.USER,
    )
    asyncio.run(provider().judge(written, CASE))
    seen = recorded(record)
    assert "PERSONA-MARKER" not in " ".join(seen["argv"])
    assert "PERSONA-MARKER" in seen["system"]


def test_the_case_is_one_argument_directly_after_print(record: Path) -> None:
    asyncio.run(provider().judge(DUCK, CASE))
    seen = recorded(record)
    argv = seen["argv"]
    assert argv[argv.index("-p") + 1] == user_message(CASE)
    assert seen["stdin"] == ""  # input is closed, so Claude Code never waits for it


@pytest.mark.parametrize(
    "situation",
    [
        'She said "hide it" and I said \\"no\\"',  # quotes and backslashes
        "ends with a backslash \\",
        "nospaces",
        "--model opus --tools Bash",  # looks like options; must stay plain text
        "line one\nline two\ttabbed",
    ],
)
def test_awkward_text_arrives_as_exactly_one_argument(record: Path, situation: str) -> None:
    case = Case(situation=situation, action="x")
    asyncio.run(provider().judge(DUCK, case))
    argv = recorded(record)["argv"]
    assert argv[argv.index("-p") + 1] == user_message(case)
    assert "opus" not in argv[argv.index("-p") + 2 :]  # nothing leaked out as an option


def test_it_runs_in_an_empty_folder_outside_the_project(record: Path) -> None:
    asyncio.run(provider().judge(DUCK, CASE))
    seen = recorded(record)
    assert Path(seen["cwd"]).resolve() != REPO
    assert seen["files"] == ["system.txt"]  # in particular, no CLAUDE.md to pick up


def test_model_and_effort_are_passed_only_when_chosen(record: Path) -> None:
    asyncio.run(provider(model="sonnet", effort="medium").judge(DUCK, CASE))
    argv = recorded(record)["argv"]
    assert argv[argv.index("--model") + 1] == "sonnet"
    assert argv[argv.index("--effort") + 1] == "medium"

    asyncio.run(provider(effort=None).judge(DUCK, CASE))
    argv = recorded(record)["argv"]
    assert "--model" not in argv  # "default" leaves the choice to the user's Claude Code
    assert "--effort" not in argv


@pytest.mark.parametrize(
    ("mode", "error", "message"),
    [
        ("error", ProviderError, "Not logged in"),
        ("refusal", Refused, None),
        ("no_structured", ProviderError, "no structured answer"),
        ("garbage", ProviderError, "did not return JSON"),
    ],
)
def test_bad_replies_become_clear_errors(
    monkeypatch: pytest.MonkeyPatch, mode: str, error: type[Exception], message: str | None
) -> None:
    monkeypatch.setenv("FAKE_CLAUDE_MODE", mode)
    with pytest.raises(error, match=message):
        asyncio.run(provider().judge(DUCK, CASE))


def test_a_missing_program_is_explained() -> None:
    missing = ClaudeCodeProvider(executable=("definitely-not-installed-xyz",))
    with pytest.raises(ProviderError, match="was not found"):
        asyncio.run(missing.judge(DUCK, CASE))


def test_a_timed_out_duck_kills_the_program(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    done = tmp_path / "done"
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "sleep")
    monkeypatch.setenv("FAKE_CLAUDE_DONE", str(done))

    async def give_up_early() -> None:
        async with asyncio.timeout(0.8):
            await provider().judge(DUCK, CASE)

    with pytest.raises(TimeoutError):
        asyncio.run(give_up_early())
    time.sleep(2.0)  # long enough for a surviving process to have finished
    assert not done.exists(), "the program kept running after its duck was timed out"


def test_connection_check_reports_both_ways(monkeypatch: pytest.MonkeyPatch) -> None:
    ok = asyncio.run(provider().check_connection())
    assert ok.ok and "OK" in ok.message

    monkeypatch.setenv("FAKE_CLAUDE_MODE", "error")
    failed = asyncio.run(provider().check_connection())
    assert not failed.ok and "Not logged in" in failed.message
