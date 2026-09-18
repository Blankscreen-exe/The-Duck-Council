"""A hearing, and where hearings are kept.

A hearing runs as a background task, not inside the browser's connection (D34).
Browsers reconnect a dropped event stream on their own; if the hearing lived in
the connection, every reconnect would convene the council again and pay for
every duck twice. Detached, a reconnect only replays what has already arrived.
"""

import asyncio
import secrets
from collections import OrderedDict
from contextlib import aclosing
from dataclasses import dataclass, field
from typing import Protocol

from app.council import convene
from app.providers import Provider
from app.schema import Case, Duck, Finding, Ruling, Seat, Tone
from app.tally import tally


def new_run_id() -> str:
    """Short, URL-safe and unguessable, so hearings cannot be enumerated by number."""
    return secrets.token_urlsafe(9)


@dataclass(eq=False)
class Run:
    id: str
    case: Case
    roster: tuple[Duck, ...]
    tone: Tone = "cautious"
    ruling: Ruling | None = None
    """The clerk's ruling (D20); None when it could not rule. Not shown on the page."""
    seats: list[Seat] = field(default_factory=list)
    """In the order the ducks finished, which is the order they are streamed."""
    finding: Finding | None = None
    done: bool = False
    changed: asyncio.Condition = field(default_factory=asyncio.Condition)
    """Notified whenever a seat lands or the hearing ends."""

    def seat_for(self, duck_id: str) -> Seat | None:
        return next((seat for seat in self.seats if seat.duck.id == duck_id), None)


class RunStore(Protocol):
    def add(self, run: Run) -> None: ...

    def get(self, run_id: str) -> Run | None: ...


class InMemoryRunStore:
    """Hearings kept in memory until SQLite arrives (D15); the oldest are forgotten first."""

    def __init__(self, capacity: int = 200) -> None:
        self._runs: OrderedDict[str, Run] = OrderedDict()
        self._capacity = capacity

    def add(self, run: Run) -> None:
        self._runs[run.id] = run
        while len(self._runs) > self._capacity:
            self._runs.popitem(last=False)

    def get(self, run_id: str) -> Run | None:
        return self._runs.get(run_id)


async def hold_hearing(run: Run, provider: Provider) -> None:
    """Convene the council for `run`, recording each seat as it lands."""
    try:
        async with aclosing(convene(run.roster, run.case, provider, tone=run.tone)) as arriving:
            async for seat in arriving:
                async with run.changed:
                    run.seats.append(seat)
                    run.changed.notify_all()
    finally:
        # Also on cancellation (the server shutting down), so no listener waits forever.
        in_roster_order = [s for duck in run.roster if (s := run.seat_for(duck.id)) is not None]
        async with run.changed:
            run.finding = tally(in_roster_order)
            run.done = True
            run.changed.notify_all()
