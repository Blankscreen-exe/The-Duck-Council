"""The Register: every hearing the council has held, kept for good (D21, D43).

A hearing is written once, when it ends; one the server stopped part-way through
is kept with whatever arrived and marked interrupted. Each seat keeps a copy of
its duck as it was on the day. A case the clerk ruled a crisis is never written
here at all (owner's call).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import aiosqlite

from app.schema import Absence, Case, Duck, Finding, Seat, Tone, Verdict

PAGE_SIZE = 20


@dataclass(frozen=True)
class Entry:
    """One line of the Register."""

    number: int
    id: str
    filed_at: datetime
    case: Case
    heard_by: str
    finding: Finding
    interrupted: bool


@dataclass(frozen=True)
class StoredHearing(Entry):
    """A whole hearing, as it was recorded."""

    tone: Tone
    seats: tuple[Seat, ...]
    """In roster order."""


def _tone(value: str) -> Tone:
    return "play" if value == "play" else "weighty" if value == "weighty" else "cautious"


def _entry(row: aiosqlite.Row) -> Entry:
    return Entry(
        number=row["number"],
        id=row["id"],
        filed_at=datetime.fromisoformat(row["filed_at"]),
        case=Case(situation=row["situation"], action=row["action"]),
        heard_by=row["heard_by"],
        finding=Finding.model_validate_json(row["finding"]),
        interrupted=bool(row["interrupted"]),
    )


class Register:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def record(
        self,
        *,
        hearing_id: str,
        filed_at: datetime,
        case: Case,
        tone: Tone,
        heard_by: str,
        seats: Sequence[Seat],
        finding: Finding,
        interrupted: bool = False,
    ) -> int:
        """Enter a finished hearing. Returns its docket number."""
        cursor = await self._db.execute(
            "INSERT INTO hearings (id, filed_at, situation, action, tone, heard_by, finding, "
            "interrupted) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (hearing_id, filed_at.isoformat(), case.situation, case.action, tone, heard_by,
             finding.model_dump_json(), int(interrupted)),
        )  # fmt: skip
        await self._db.executemany(
            "INSERT INTO hearing_seats (hearing_id, position, duck, verdict, absence) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (hearing_id, position, seat.duck.model_dump_json(),
                 seat.verdict.model_dump_json() if seat.verdict else None,
                 seat.absence.value if seat.absence else None)
                for position, seat in enumerate(seats)
            ],
        )  # fmt: skip
        await self._db.commit()
        assert cursor.lastrowid is not None
        return cursor.lastrowid

    async def page(self, page: int = 1) -> tuple[list[Entry], int]:
        """Newest first. Returns the entries on `page` and how many there are in all."""
        page = max(1, page)
        async with self._db.execute("SELECT COUNT(*) FROM hearings") as cursor:
            row = await cursor.fetchone()
        total = int(row[0]) if row else 0
        async with self._db.execute(
            "SELECT * FROM hearings ORDER BY number DESC LIMIT ? OFFSET ?",
            (PAGE_SIZE, (page - 1) * PAGE_SIZE),
        ) as cursor:
            rows = await cursor.fetchall()
        return [_entry(row) for row in rows], total

    async def get(self, hearing_id: str) -> StoredHearing | None:
        async with self._db.execute("SELECT * FROM hearings WHERE id = ?", (hearing_id,)) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        async with self._db.execute(
            "SELECT * FROM hearing_seats WHERE hearing_id = ? ORDER BY position", (hearing_id,)
        ) as cursor:
            seat_rows = await cursor.fetchall()
        seats = tuple(
            Seat(
                duck=Duck.model_validate_json(seat["duck"]),
                verdict=Verdict.model_validate_json(seat["verdict"]) if seat["verdict"] else None,
                absence=Absence(seat["absence"]) if seat["absence"] else None,
            )
            for seat in seat_rows
        )
        entry = _entry(row)
        return StoredHearing(**vars(entry), tone=_tone(row["tone"]), seats=seats)

    async def remove(self, hearing_id: str) -> bool:
        cursor = await self._db.execute("DELETE FROM hearings WHERE id = ?", (hearing_id,))
        await self._db.commit()
        return cursor.rowcount > 0

    async def clear(self) -> None:
        """Remove every hearing. Docket numbers still carry on from where they were."""
        await self._db.execute("DELETE FROM hearings")
        await self._db.commit()
