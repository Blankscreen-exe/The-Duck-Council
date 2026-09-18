"""Test doubles. A scripted provider gives each duck an exact answer, delay or failure."""

import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.providers import ProviderConfig
from app.providers.base import ConnectionCheck
from app.providers.claude_code import ClaudeCodeProvider
from app.schema import BAND_CENTRE, Band, Case, Duck, Register, Ruling, Tone, Verdict


def verdict_scoring(score: int, line: str = "A verdict.") -> Verdict:
    """Build a verdict that computes to exactly `score`."""
    band = min(Band, key=lambda b: abs(BAND_CENTRE[b] - score))
    return Verdict(read="Noted.", band=band, nudge=score - BAND_CENTRE[band], line=line)


@dataclass
class Script:
    verdict: Verdict | None = None
    delay: float = 0.0
    error: Exception | None = None


@dataclass
class ScriptedProvider:
    scripts: dict[str, Script]
    ruling: Ruling | Exception = field(
        default_factory=lambda: Ruling(reason="A joke.", hear_as=Register.PLAY)
    )
    max_concurrency: int = 64
    timeout: float = 5.0
    name: str = "scripted"
    calls: int = 0
    in_flight: int = 0
    peak: int = 0
    cancelled: set[str] = field(default_factory=set)
    tones: list[Tone] = field(default_factory=list)

    async def judge(self, duck: Duck, case: Case, tone: Tone = "cautious") -> Verdict:
        script = self.scripts[duck.id]
        self.calls += 1
        self.tones.append(tone)
        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        try:
            await asyncio.sleep(script.delay)
            if script.error is not None:
                raise script.error
            assert script.verdict is not None, f"no verdict scripted for {duck.id}"
            return script.verdict
        except asyncio.CancelledError:
            self.cancelled.add(duck.id)
            raise
        finally:
            self.in_flight -= 1

    async def classify(self, case: Case) -> Ruling:
        if isinstance(self.ruling, Exception):
            raise self.ruling
        return self.ruling

    async def check_connection(self) -> ConnectionCheck:
        return ConnectionCheck(ok=True, message="scripted")


@dataclass
class FakeBuilt:
    """A provider from `FakeBuilder`. Its connection check fails when its model is "broken"."""

    config: ProviderConfig
    max_concurrency: int = 8
    timeout: float = 5.0
    name: str = field(init=False)

    def __post_init__(self) -> None:
        self.name = self.config.kind  # so the demo still reads as "demo"

    async def judge(self, duck: Duck, case: Case, tone: Tone = "cautious") -> Verdict:
        return verdict_scoring(60, line=f"Judged by {self.config.model}.")

    async def classify(self, case: Case) -> Ruling:
        return Ruling(reason="A joke.", hear_as=Register.PLAY)

    async def check_connection(self) -> ConnectionCheck:
        if self.config.model == "broken":
            return ConnectionCheck(ok=False, message="Invalid API key.")
        return ConnectionCheck(ok=True, message=f"Connected to {self.config.model}")


@dataclass
class FakeBuilder:
    """Stands in for `build_provider`, remembering every configuration it was given."""

    built: list[ProviderConfig] = field(default_factory=list)

    def __call__(self, config: ProviderConfig) -> FakeBuilt:
        self.built.append(config)
        return FakeBuilt(config)


FAKE_CLAUDE = Path(__file__).with_name("fake_claude.py")
# The base interpreter rather than a virtualenv launcher: killing a launcher can
# leave the real interpreter running, which would make the kill test meaningless.
PYTHON = getattr(sys, "_base_executable", sys.executable)


def fake_claude_code(**kwargs: Any) -> ClaudeCodeProvider:
    """A real ClaudeCodeProvider whose `claude` is the stand-in in fake_claude.py."""
    return ClaudeCodeProvider(executable=(PYTHON, str(FAKE_CLAUDE)), **kwargs)


def recorded(path: Path) -> dict[str, Any]:
    """What the stand-in claude.exe was given, as written to the `record` fixture's file."""
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data
