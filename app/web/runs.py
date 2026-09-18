"""A hearing, and where hearings are kept.

A hearing runs as a background task, not inside the browser's connection (D34).
Browsers reconnect a dropped event stream on their own; if the hearing lived in
the connection, every reconnect would convene the council again and pay for
every duck twice. Detached, a reconnect only replays what has already arrived.
"""

import asyncio
import logging
import secrets
from collections import OrderedDict
from contextlib import aclosing
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from app.council import convene
from app.providers import Provider
from app.register import Register, StoredHearing
from app.schema import Case, Duck, Finding, Ruling, Seat, Tone
from app.tally import tally

log = logging.getLogger(__name__)


def new_run_id() -> str:
    """Short, URL-safe and unguessable, so hearings cannot be enumerated by number."""
    return secrets.token_urlsafe(9)


@dataclass(eq=False)
class Run:
    id: str
    case: Case
    roster: tuple[Duck, ...]
    tone: Tone = "cautious"
    heard_by: str = ""
    """The provider's name when the case was filed (owner's call: shown on the page)."""
    filed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    number: int | None = None
    """The Register's docket number, once the hearing has been entered."""
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


async def hold_hearing(run: Run, provider: Provider, register: Register | None = None) -> None:
    """Convene the council for `run`, recording each seat as it lands, then enter it."""
    completed = False
    try:
        async with aclosing(convene(run.roster, run.case, provider, tone=run.tone)) as arriving:
            async for seat in arriving:
                async with run.changed:
                    run.seats.append(seat)
                    run.changed.notify_all()
        completed = True
    finally:
        # Also on cancellation (the server shutting down), so no listener waits forever.
        in_roster_order = [s for duck in run.roster if (s := run.seat_for(duck.id)) is not None]
        finding = tally(in_roster_order)
        # Entered before "done" is announced, so the Register never lags the page.
        if register is not None:
            # A hearing cut short is still kept, with whatever arrived, marked as such.
            try:
                run.number = await register.record(
                    hearing_id=run.id,
                    filed_at=run.filed_at,
                    case=run.case,
                    tone=run.tone,
                    heard_by=run.heard_by,
                    seats=in_roster_order,
                    finding=finding,
                    interrupted=not completed,
                )
            except Exception:
                log.exception("could not enter hearing %s in the Register", run.id)
        async with run.changed:
            run.finding = finding
            run.done = True
            run.changed.notify_all()


def run_from_register(stored: StoredHearing) -> Run:
    """A finished hearing read back from the Register, in the shape the pages expect."""
    return Run(
        id=stored.id,
        case=stored.case,
        roster=tuple(seat.duck for seat in stored.seats),
        tone=stored.tone,
        heard_by=stored.heard_by,
        filed_at=stored.filed_at,
        number=stored.number,
        seats=list(stored.seats),
        finding=stored.finding,
        done=True,
    )
