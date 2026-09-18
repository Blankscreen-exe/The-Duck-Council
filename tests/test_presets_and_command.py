import asyncio
import sys

import pytest

from app.ducks import DUCKS_BY_ID
from app.providers import PRESETS, ProviderConfig, ProviderError, build_provider
from app.providers._text import parse_reply
from app.providers.command import CommandProvider
from app.providers.presets import Preset, ProviderKind
from app.schema import Case, Verdict

PYTHON = getattr(sys, "_base_executable", sys.executable)
CASE = Case(situation="s", action="a")

EXPECTED_NAME: dict[ProviderKind, str] = {
    "demo": "demo",
    "claude_code": "claude_code",
    "anthropic": "anthropic",
    "openai_compatible": "openai_compatible",
    "command": "command",
}


@pytest.mark.parametrize("preset", PRESETS, ids=lambda preset: preset.id)
def test_every_preset_builds_a_provider(preset: Preset) -> None:
    config = ProviderConfig.from_preset(
        preset.id,
        model=preset.default_model or "some-model",
        base_url=preset.base_url or "http://localhost:9/v1",
        api_key="test-key",
        command=("some-program",),
    )
    assert build_provider(config).name == EXPECTED_NAME[preset.kind]


def test_unknown_presets_are_rejected() -> None:
    with pytest.raises(ValueError, match="unknown provider"):
        ProviderConfig.from_preset("carrier-pigeon")


def test_a_custom_endpoint_needs_a_base_url() -> None:
    with pytest.raises(ValueError, match="base URL"):
        build_provider(ProviderConfig.from_preset("custom", model="m"))


def test_a_command_provider_needs_a_program() -> None:
    with pytest.raises(ValueError, match="program"):
        build_provider(ProviderConfig.from_preset("command"))


def test_the_key_never_shows_in_a_printed_config() -> None:
    config = ProviderConfig.from_preset("anthropic", api_key="sk-ant-very-secret")
    assert "very-secret" not in repr(config)
    assert "very-secret" not in str(config)


# --- reading verdicts out of text -----------------------------------------------------


def test_a_verdict_is_found_after_other_braces_and_prose() -> None:
    text = 'Thinking {not json}. {"read":"r","band":"sound","nudge":1,"line":"Yes."} Done.'
    assert parse_reply(text, Verdict).score == 71


@pytest.mark.parametrize(
    "text",
    [
        "no json here",
        '{"read":"r","band":"brilliant","nudge":0,"line":"x"}',  # not a real band
        '{"read":"r","band":"sound","nudge":40,"line":"x"}',  # nudge out of range
    ],
)
def test_text_without_a_valid_verdict_is_rejected(text: str) -> None:
    with pytest.raises(ProviderError):
        parse_reply(text, Verdict)


# --- custom command -------------------------------------------------------------------

_PRINT_VERDICT = (
    "import sys; sys.stdin.read(); "
    'print(\'Sure! {"read":"r","band":"unwise","nudge":-1,"line":"No."}\')'
)


def test_a_custom_command_can_judge() -> None:
    command = CommandProvider((PYTHON, "-c", _PRINT_VERDICT))
    verdict = asyncio.run(command.judge(DUCKS_BY_ID["king"], CASE))
    assert verdict.score == 29


def test_a_custom_command_receives_the_format_in_words() -> None:
    echo = CommandProvider((PYTHON, "-c", "import sys; print(sys.stdin.read())"))
    with pytest.raises(ProviderError):  # the echo is not a verdict...
        asyncio.run(echo.judge(DUCKS_BY_ID["king"], CASE))
    check = asyncio.run(echo.check_connection())  # ...but the connection works
    assert check.ok and "Reply with exactly: OK" in check.message
