import asyncio
import statistics

from app.ducks import BUILTIN_DUCKS, DUCKS_BY_ID
from app.providers import DemoProvider
from app.providers.demo import _LINES, DEMO_READ
from app.schema import Case, Duck, Origin

INSTANT = DemoProvider(latency=(0.0, 0.0))


def judge(duck: Duck, case: Case) -> int:
    return asyncio.run(INSTANT.judge(duck, case)).score


def test_same_duck_and_case_always_give_the_same_verdict() -> None:
    case = Case(situation="s", action="a")
    first = asyncio.run(INSTANT.judge(DUCKS_BY_ID["witch"], case))
    again = asyncio.run(INSTANT.judge(DUCKS_BY_ID["witch"], case))
    assert first == again


def test_demo_verdicts_say_no_model_was_consulted() -> None:
    verdict = asyncio.run(INSTANT.judge(DUCKS_BY_ID["king"], Case(situation="s", action="a")))
    assert verdict.read == DEMO_READ


def test_ducks_lean_in_character() -> None:
    cases = [Case(situation=f"situation {i}", action=f"action {i}") for i in range(200)]
    doctor = statistics.mean(judge(DUCKS_BY_ID["doctor"], c) for c in cases)
    ripper = statistics.mean(judge(DUCKS_BY_ID["serial_killer"], c) for c in cases)
    assert doctor < 40 < 60 < ripper


def test_every_builtin_duck_has_demo_lines() -> None:
    # Adding a duck without demo lines would quietly fall back to generic text.
    assert set(_LINES) == {duck.id for duck in BUILTIN_DUCKS}


def test_user_ducks_get_generic_lines() -> None:
    custom = Duck(
        id="landlord",
        name="The Landlord",
        epithet="Weighs the deposit · blind to friendship",
        voice="Terse.",
        weighs="The deposit.",
        blind_spot="Friendship.",
        origin=Origin.USER,
    )
    verdict = asyncio.run(INSTANT.judge(custom, Case(situation="s", action="a")))
    assert "By everything I care about" in verdict.line or "either way" in verdict.line
