"""Convene the council: ask every duck at once, report each answer as it lands (D8).

`convene` streams seats in the order ducks finish, which is what the web page
will use to stamp notices onto the board one by one (D9, D26). `hear` waits for
everyone and returns the full result, which is what the CLI and tests use.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator, Sequence

from app.providers.base import Provider, Refused
from app.schema import Absence, Case, Duck, Finding, Seat
from app.tally import tally

log = logging.getLogger(__name__)


async def _hear_one(duck: Duck, case: Case, provider: Provider, timeout: float) -> Seat:
    try:
        # The clock starts once the duck is actually being asked, not while it waits
        # for a concurrency slot, so a busy provider does not time out the queue.
        async with asyncio.timeout(timeout):
            verdict = await provider.judge(duck, case)
    except Refused:
        return Seat(duck=duck, absence=Absence.REFUSED)
    except TimeoutError:
        return Seat(duck=duck, absence=Absence.TIMED_OUT)
    except Exception:
        # One duck failing costs one duck, never the council.
        log.exception("duck %r failed on provider %r", duck.id, provider.name)
        return Seat(duck=duck, absence=Absence.FAILED)
    return Seat(duck=duck, verdict=verdict)


async def convene(
    ducks: Sequence[Duck],
    case: Case,
    provider: Provider,
    *,
    timeout: float | None = None,
) -> AsyncGenerator[Seat]:
    """Yield each duck's seat as soon as it is ready, fastest first.

    `timeout` defaults to the provider's own: Claude Code needs far longer per duck
    than an HTTP API does, so one number for every provider would be wrong for most.

    A caller that might stop listening early should wrap this in
    `contextlib.aclosing(...)`, so the cleanup below runs immediately rather
    than whenever the generator happens to be garbage-collected.
    """
    if not ducks:
        raise ValueError("the council needs at least one duck")  # D14's guard
    if len({duck.id for duck in ducks}) != len(ducks):
        raise ValueError("a duck cannot sit on the council twice")

    slots = asyncio.Semaphore(provider.max_concurrency)
    limit = provider.timeout if timeout is None else timeout

    async def limited(duck: Duck) -> Seat:
        async with slots:
            return await _hear_one(duck, case, provider, limit)

    tasks = [asyncio.create_task(limited(duck)) for duck in ducks]
    try:
        for next_seat in asyncio.as_completed(tasks):
            yield await next_seat
    finally:
        # If whoever is listening stops early (say, the browser tab closes), stop
        # the remaining calls instead of paying for answers nobody will see.
        for task in tasks:
            task.cancel()


async def hear(
    ducks: Sequence[Duck],
    case: Case,
    provider: Provider,
    *,
    timeout: float | None = None,
) -> tuple[list[Seat], Finding]:
    """Wait for the whole council. Seats come back in roster order, not finish order."""
    finished = {
        seat.duck.id: seat async for seat in convene(ducks, case, provider, timeout=timeout)
    }
    seats = [finished[duck.id] for duck in ducks]
    return seats, tally(seats)
