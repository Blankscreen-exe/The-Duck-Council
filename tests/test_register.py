"""The Register against real SQLite in a temporary file: the same code the app runs."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.ducks import DUCKS_BY_ID
from app.register import PAGE_SIZE, Register
from app.schema import Absence, Case, Seat
from app.storage import open_database
from app.tally import tally
from tests.fakes import verdict_scoring

CASE = Case(situation="My flatmate eats my leftovers.", action="Hide a ghost pepper in them.")
SEATS = (
    Seat(duck=DUCKS_BY_ID["lawyer"], verdict=verdict_scoring(24, "Counsel objects.")),
    Seat(duck=DUCKS_BY_ID["rebel"], absence=Absence.REFUSED),
    Seat(duck=DUCKS_BY_ID["rich"], verdict=verdict_scoring(73)),
)
DAY = datetime(2026, 9, 18, 14, 30, tzinfo=UTC)


def in_register[T](path: Path, action: Callable[[Register], Awaitable[T]]) -> T:
    """Open the database at `path`, run `action` on its Register, close it again."""

    async def run() -> T:
        db = await open_database(path)
        try:
            return await action(Register(db))
        finally:
            await db.close()

    return asyncio.run(run())


async def enter(register: Register, hearing_id: str, *, when: datetime = DAY, **extra: bool) -> int:
    return await register.record(
        hearing_id=hearing_id,
        filed_at=when,
        case=CASE,
        tone="play",
        heard_by="Claude Code",
        seats=SEATS,
        finding=tally(SEATS),
        **extra,
    )


def test_a_hearing_reads_back_exactly_as_it_was_entered(tmp_path: Path) -> None:
    db = tmp_path / "council.db"
    number = in_register(db, lambda r: enter(r, "h1"))
    stored = in_register(db, lambda r: r.get("h1"))  # a fresh connection: really on disk

    assert stored is not None
    assert stored.number == number == 1
    assert (stored.case, stored.tone, stored.heard_by) == (CASE, "play", "Claude Code")
    assert stored.filed_at == DAY
    assert stored.seats == SEATS  # in roster order, empty chair included
    assert stored.finding == tally(SEATS)
    assert stored.interrupted is False


def test_an_interrupted_hearing_is_kept_and_marked(tmp_path: Path) -> None:
    async def run(register: Register) -> bool:
        await enter(register, "h1", interrupted=True)
        stored = await register.get("h1")
        assert stored is not None
        return stored.interrupted

    assert in_register(tmp_path / "council.db", run) is True


def test_newest_first_a_page_at_a_time(tmp_path: Path) -> None:
    async def run(register: Register) -> None:
        for n in range(PAGE_SIZE + 3):
            await enter(register, f"h{n}", when=DAY + timedelta(minutes=n))
        first, total = await register.page(1)
        second, _ = await register.page(2)
        assert total == PAGE_SIZE + 3
        assert [e.id for e in first][:2] == [f"h{PAGE_SIZE + 2}", f"h{PAGE_SIZE + 1}"]
        assert [e.id for e in second] == ["h2", "h1", "h0"]

    in_register(tmp_path / "council.db", run)


def test_a_docket_number_is_never_given_out_twice(tmp_path: Path) -> None:
    """Like a real register: striking out an entry, or clearing the book, keeps its number used."""

    async def run(register: Register) -> list[int]:
        numbers = [await enter(register, "a"), await enter(register, "b")]
        assert await register.remove("b")
        numbers.append(await enter(register, "c"))
        await register.clear()
        numbers.append(await enter(register, "d"))
        return numbers

    assert in_register(tmp_path / "council.db", run) == [1, 2, 3, 4]


def test_striking_out_takes_the_seats_with_it(tmp_path: Path) -> None:
    async def run(register: Register) -> tuple[bool, bool, int]:
        await enter(register, "h1")
        removed = await register.remove("h1")
        again = await register.remove("h1")
        async with register._db.execute("SELECT COUNT(*) FROM hearing_seats") as cursor:
            row = await cursor.fetchone()
        assert row is not None
        return removed, again, int(row[0])

    assert in_register(tmp_path / "council.db", run) == (True, False, 0)


def test_an_unknown_hearing_is_none(tmp_path: Path) -> None:
    assert in_register(tmp_path / "council.db", lambda r: r.get("nope")) is None
