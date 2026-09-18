"""The clerk (D20, D22, D41): one ruling before any duck, and what each ruling does."""

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx2
import pytest

from app.clerk import is_crisis, rule, tone_for
from app.council import hear
from app.ducks import DUCKS_BY_ID, VOICE_EXAMPLES
from app.prompts import CLERK_PROMPT, FRAME, format_instructions, system_prompt
from app.providers import DemoProvider, Refused
from app.providers.anthropic_api import CLERK_MODEL, AnthropicProvider
from app.schema import Case, Register, Ruling, Verdict
from tests.fakes import Script, ScriptedProvider, recorded, verdict_scoring
from tests.fakes import fake_claude_code as claude_code

CAT = Case(situation="i have a fat helpless cat", action="im gonna brew him in the coffee cauldron")
PLAY = Ruling(reason="Absurd.", hear_as=Register.PLAY)


def scripted(ruling: Ruling | Exception = PLAY) -> ScriptedProvider:
    return ScriptedProvider({"doctor": Script(verdict=verdict_scoring(50))}, ruling=ruling)


# --- ruling, and what a missing ruling means --------------------------------------------


def test_the_clerk_returns_the_providers_ruling() -> None:
    assert asyncio.run(rule(CAT, scripted())) == PLAY


@pytest.mark.parametrize("failure", [Refused(), RuntimeError("connection reset")])
def test_a_clerk_that_cannot_rule_means_a_cautious_hearing(failure: Exception) -> None:
    ruling = asyncio.run(rule(CAT, scripted(failure)))
    assert ruling is None
    assert tone_for(ruling) == "cautious"
    assert not is_crisis(ruling)


def test_a_clerk_that_takes_too_long_means_a_cautious_hearing() -> None:
    class Slow(ScriptedProvider):
        async def classify(self, case: Case) -> Ruling:
            await asyncio.sleep(5)
            return PLAY

    slow = Slow({}, timeout=0.05)
    assert asyncio.run(rule(CAT, slow)) is None


def test_each_ruling_sets_the_ducks_tone() -> None:
    assert tone_for(Ruling(reason="r", hear_as=Register.PLAY)) == "play"
    assert tone_for(Ruling(reason="r", hear_as=Register.WEIGHTY)) == "weighty"
    crisis = Ruling(reason="r", hear_as=Register.CRISIS)
    assert is_crisis(crisis)
    with pytest.raises(ValueError, match="not heard"):
        tone_for(crisis)  # a crisis never reaches the ducks, so asking for its tone is a bug


def test_every_duck_hears_the_tone_it_was_given() -> None:
    provider = scripted()
    asyncio.run(hear([DUCKS_BY_ID["doctor"]], CAT, provider, tone="play"))
    assert provider.tones == ["play"]


# --- what the ducks are told ------------------------------------------------------------


def test_play_tells_ducks_to_commit_and_cautious_adds_nothing() -> None:
    ripper = DUCKS_BY_ID["serial_killer"]
    play, weighty, cautious = (system_prompt(ripper, t) for t in ("play", "weighty", "cautious"))
    assert "commit to your" in play and "if you actually" in play
    assert "real stakes" in weighty
    assert "The clerk" not in cautious  # exactly the council as it was before the clerk
    assert all(p.startswith(FRAME) for p in (play, weighty, cautious))  # still cacheable


def test_only_the_four_wild_ducks_carry_voice_examples() -> None:
    assert set(VOICE_EXAMPLES) == {"serial_killer", "witch", "gangsta", "spiritual_medium"}
    assert "<examples>" in system_prompt(DUCKS_BY_ID["serial_killer"])
    assert "<examples>" not in system_prompt(DUCKS_BY_ID["doctor"])


def test_the_clerk_is_not_taught_the_case_we_test_it_with() -> None:
    # A failing case copied into the prompt as an example could never prove a fix.
    assert "cauldron" not in CLERK_PROMPT.lower()
    assert all("cauldron" not in e.action.lower() for ex in VOICE_EXAMPLES.values() for e in ex)


def test_the_format_in_words_matches_each_schema() -> None:
    assert '"hear_as": one of "play", "weighty", "crisis"' in format_instructions(Ruling)
    assert '"nudge": integer from -10 to 10' in format_instructions(Verdict)


# --- the clerk on each provider ---------------------------------------------------------


def test_the_demo_clerk_is_a_word_check_that_leans_to_play() -> None:
    demo = DemoProvider(latency=(0.0, 0.0))
    assert asyncio.run(demo.classify(CAT)).hear_as is Register.PLAY
    worried = Case(situation="Nothing helps any more.", action="I want to die.")
    assert asyncio.run(demo.classify(worried)).hear_as is Register.CRISIS


def test_claude_code_asks_the_clerk_on_haiku_without_effort(record: Path) -> None:
    ruling = asyncio.run(claude_code().classify(CAT))
    assert ruling.hear_as is Register.PLAY
    argv = recorded(record)["argv"]
    assert argv[argv.index("--model") + 1] == "haiku"
    assert "--effort" not in argv
    assert "clerk of the Duck Council" in recorded(record)["system"]


def test_claude_code_passes_the_clerks_ruling_through(
    record: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_CLAUDE_REGISTER", "crisis")
    assert asyncio.run(claude_code().classify(CAT)).hear_as is Register.CRISIS


def test_the_anthropic_clerk_runs_on_haiku_without_effort() -> None:
    seen: dict[str, Any] = {}
    reply = {"reason": "Absurd.", "hear_as": "play"}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.update(json.loads(request.content))
        return httpx2.Response(200, json={
            "id": "msg", "type": "message", "role": "assistant", "model": CLERK_MODEL,
            "content": [{"type": "text", "text": json.dumps(reply)}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        })  # fmt: skip

    client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    provider = AnthropicProvider(api_key="k", http_client=client)
    assert asyncio.run(provider.classify(CAT)) == PLAY
    assert seen["model"] == "claude-haiku-4-5"
    assert "effort" not in seen.get("output_config", {})
