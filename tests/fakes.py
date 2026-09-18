"""Test doubles. A scripted provider gives each duck an exact answer, delay or failure."""

import asyncio
from dataclasses import dataclass, field

from app.providers.base import ConnectionCheck
from app.schema import BAND_CENTRE, Band, Case, Duck, Verdict


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
    max_concurrency: int = 64
    timeout: float = 5.0
    name: str = "scripted"
    calls: int = 0
    in_flight: int = 0
    peak: int = 0
    cancelled: set[str] = field(default_factory=set)

    async def judge(self, duck: Duck, case: Case) -> Verdict:
        script = self.scripts[duck.id]
        self.calls += 1
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

    async def check_connection(self) -> ConnectionCheck:
        return ConnectionCheck(ok=True, message="scripted")
