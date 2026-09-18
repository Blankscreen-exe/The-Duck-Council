import asyncio
from contextlib import aclosing

import pytest

from app.council import convene, hear
from app.ducks import DUCKS_BY_ID
from app.providers import Refused
from app.schema import Absence, Case
from tests.fakes import Script, ScriptedProvider, verdict_scoring

CASE = Case(situation="My flatmate keeps eating my food.", action="Hide a ghost pepper in it.")
DOCTOR, RICH, REBEL, KING = (DUCKS_BY_ID[i] for i in ("doctor", "rich", "rebel", "king"))


def test_failures_cost_one_chair_not_the_council() -> None:
    provider = ScriptedProvider(
        {
            "doctor": Script(verdict=verdict_scoring(12)),
            "rich": Script(error=Refused()),
            "rebel": Script(delay=5.0, verdict=verdict_scoring(90)),
            "king": Script(error=RuntimeError("connection reset")),
        }
    )
    seats, finding = asyncio.run(hear([DOCTOR, RICH, REBEL, KING], CASE, provider, timeout=0.05))

    assert [seat.absence for seat in seats] == [
        None,
        Absence.REFUSED,
        Absence.TIMED_OUT,
        Absence.FAILED,
    ]
    assert seats[0].verdict is not None and seats[0].verdict.score == 12
    assert (finding.sitting, finding.voted, finding.median) == (4, 1, 12)


def test_seats_stream_in_the_order_ducks_finish() -> None:
    provider = ScriptedProvider(
        {
            "doctor": Script(delay=0.06, verdict=verdict_scoring(10)),
            "rich": Script(delay=0.00, verdict=verdict_scoring(90)),
            "rebel": Script(delay=0.03, verdict=verdict_scoring(70)),
        }
    )

    async def order() -> list[str]:
        return [seat.duck.id async for seat in convene([DOCTOR, RICH, REBEL], CASE, provider)]

    assert asyncio.run(order()) == ["rich", "rebel", "doctor"]


def test_hear_returns_roster_order_regardless_of_finish_order() -> None:
    provider = ScriptedProvider(
        {
            "doctor": Script(delay=0.04, verdict=verdict_scoring(10)),
            "rich": Script(delay=0.00, verdict=verdict_scoring(90)),
        }
    )
    seats, _ = asyncio.run(hear([DOCTOR, RICH], CASE, provider))
    assert [seat.duck.id for seat in seats] == ["doctor", "rich"]


def test_concurrency_limit_is_respected() -> None:
    ducks = [DOCTOR, RICH, REBEL, KING]
    provider = ScriptedProvider(
        {d.id: Script(delay=0.02, verdict=verdict_scoring(50)) for d in ducks}, max_concurrency=2
    )
    asyncio.run(hear(ducks, CASE, provider))
    assert provider.peak == 2


def test_timeout_does_not_start_until_a_slot_is_free() -> None:
    # Two ducks, one slot, each takes 0.06s against a 0.1s timeout. The second waits
    # 0.06s in the queue, which must not count against it.
    provider = ScriptedProvider(
        {d.id: Script(delay=0.06, verdict=verdict_scoring(50)) for d in (DOCTOR, RICH)},
        max_concurrency=1,
    )
    seats, _ = asyncio.run(hear([DOCTOR, RICH], CASE, provider, timeout=0.1))
    assert all(seat.verdict is not None for seat in seats)


def test_stopping_early_cancels_the_ducks_still_deliberating() -> None:
    provider = ScriptedProvider(
        {
            "doctor": Script(delay=0.0, verdict=verdict_scoring(10)),
            "rich": Script(delay=5.0, verdict=verdict_scoring(90)),
        }
    )

    async def first_then_leave() -> None:
        async with aclosing(convene([DOCTOR, RICH], CASE, provider)) as seats:
            async for _ in seats:
                break
        await asyncio.sleep(0)  # let the cancellation land

    asyncio.run(first_then_leave())
    assert provider.cancelled == {"rich"}


@pytest.mark.parametrize(
    ("roster", "message"),
    [([], "at least one duck"), ([DOCTOR, DOCTOR], "twice")],
)
def test_invalid_rosters_are_rejected(roster: list[object], message: str) -> None:
    provider = ScriptedProvider({"doctor": Script(verdict=verdict_scoring(50))})

    async def drain() -> None:
        async for _ in convene(roster, CASE, provider):  # type: ignore[arg-type]
            pass

    with pytest.raises(ValueError, match=message):
        asyncio.run(drain())
