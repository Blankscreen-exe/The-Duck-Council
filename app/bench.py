"""The bench: every duck, which of them are sitting, and saved rosters (D14, D23).

Kept in SQLite (D15). Built-in ducks and the default preset are copied in from
`app/ducks.py` every time the bench opens: the code is their source of truth, so
tuning a duck's wording reaches the database without a migration, and the user's
choice of who sits is kept. User ducks are never touched by that sync.

The bench's rules (never an empty council, built-ins cannot be edited) are
enforced inside the SQL statements themselves, so two browser tabs acting at the
same moment cannot slip past a check made a moment earlier.
"""

import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import aiosqlite
from pydantic import BaseModel, ConfigDict, Field

from app.ducks import BUILTIN_DUCKS, DEFAULT_PRESET, DEFAULT_ROSTER
from app.schema import Duck, Origin
from app.storage import open_database

_ORDER = "ORDER BY origin = 'user', position"  # built-ins first, in code order


class BenchError(ValueError):
    """A rule of the bench was broken. The message is fit to show a person."""


class DuckDraft(BaseModel):
    """What a person writes to commission or amend a duck (D14, D29)."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=40)
    epithet: str = Field(min_length=1, max_length=48)
    voice: str = Field(min_length=1, max_length=600)
    weighs: str = Field(min_length=1, max_length=300)
    blind_spot: str = Field(min_length=1, max_length=300)


@dataclass(frozen=True)
class BenchEntry:
    duck: Duck
    sitting: bool


@dataclass(frozen=True)
class RosterPreset:
    id: int
    name: str
    duck_ids: frozenset[str]
    is_default: bool


def _duck(row: aiosqlite.Row) -> Duck:
    return Duck(
        id=row["id"],
        name=row["name"],
        epithet=row["epithet"],
        voice=row["voice"],
        weighs=row["weighs"],
        blind_spot=row["blind_spot"],
        portrait=row["portrait"],
        origin=Origin(row["origin"]),
    )


class Bench:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    @property
    def db(self) -> aiosqlite.Connection:
        """The shared connection, for checks that span the Bench and the Register."""
        return self._db

    @classmethod
    async def open(cls, path: Path) -> Self:
        """Open a bench on its own connection (used by tests). `close()` closes it."""
        bench = cls(await open_database(path))
        await bench.sync()
        return bench

    async def close(self) -> None:
        await self._db.close()

    # ── setup ────────────────────────────────────────────────────────────────

    async def sync(self) -> None:
        """Bring built-in ducks and the default preset in line with the code."""
        for position, duck in enumerate(BUILTIN_DUCKS):
            await self._db.execute(
                """
                INSERT INTO ducks (id, name, epithet, voice, weighs, blind_spot, portrait,
                                   origin, position)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'builtin', ?)
                ON CONFLICT (id) DO UPDATE SET
                    name = excluded.name, epithet = excluded.epithet, voice = excluded.voice,
                    weighs = excluded.weighs, blind_spot = excluded.blind_spot,
                    portrait = excluded.portrait, position = excluded.position
                WHERE ducks.origin = 'builtin'
                """,
                (duck.id, duck.name, duck.epithet, duck.voice, duck.weighs, duck.blind_spot,
                 duck.portrait, position),
            )  # fmt: skip
        known = [duck.id for duck in BUILTIN_DUCKS]
        marks = ", ".join("?" for _ in known)
        await self._db.execute(
            f"DELETE FROM ducks WHERE origin = 'builtin' AND id NOT IN ({marks})", known
        )

        await self._sync_default_preset()
        await self._db.commit()

    async def _sync_default_preset(self) -> None:
        """The shipped default preset (D23): defined in code, cannot be deleted."""
        async with self._db.execute("SELECT id FROM presets WHERE is_default = 1") as cursor:
            row = await cursor.fetchone()
        first_run = row is None
        if row is None:
            cursor = await self._db.execute(
                "INSERT INTO presets (name, is_default) VALUES (?, 1)", (DEFAULT_PRESET,)
            )
            preset_id = cursor.lastrowid
        else:
            preset_id = row["id"]
            await self._db.execute(
                "UPDATE presets SET name = ? WHERE id = ?", (DEFAULT_PRESET, preset_id)
            )

        marks = ", ".join("?" for _ in DEFAULT_ROSTER)
        await self._db.execute(
            f"DELETE FROM preset_ducks WHERE preset_id = ? AND duck_id NOT IN ({marks})",
            (preset_id, *DEFAULT_ROSTER),
        )
        await self._db.executemany(
            "INSERT OR IGNORE INTO preset_ducks (preset_id, duck_id) VALUES (?, ?)",
            [(preset_id, duck_id) for duck_id in DEFAULT_ROSTER],
        )
        if first_run:
            # A fresh install sits the default line-up, not every duck.
            await self._db.execute(f"UPDATE ducks SET sitting = (id IN ({marks}))", DEFAULT_ROSTER)

    # ── reading ──────────────────────────────────────────────────────────────

    async def entries(self) -> list[BenchEntry]:
        async with self._db.execute(f"SELECT * FROM ducks {_ORDER}") as cursor:
            rows = await cursor.fetchall()
        return [BenchEntry(duck=_duck(row), sitting=bool(row["sitting"])) for row in rows]

    async def roster(self) -> tuple[Duck, ...]:
        """The ducks sitting today, in bench order."""
        async with self._db.execute(f"SELECT * FROM ducks WHERE sitting = 1 {_ORDER}") as cursor:
            rows = await cursor.fetchall()
        return tuple(_duck(row) for row in rows)

    async def entry(self, duck_id: str) -> BenchEntry | None:
        async with self._db.execute("SELECT * FROM ducks WHERE id = ?", (duck_id,)) as cursor:
            row = await cursor.fetchone()
        return BenchEntry(duck=_duck(row), sitting=bool(row["sitting"])) if row else None

    async def presets(self) -> list[RosterPreset]:
        async with self._db.execute(
            "SELECT presets.id, presets.name, presets.is_default, preset_ducks.duck_id "
            "FROM presets LEFT JOIN preset_ducks ON preset_ducks.preset_id = presets.id "
            "ORDER BY presets.is_default DESC, presets.name"
        ) as cursor:
            rows = await cursor.fetchall()
        headers: dict[int, tuple[str, bool]] = {}
        members: dict[int, set[str]] = {}
        for row in rows:
            headers[row["id"]] = (row["name"], bool(row["is_default"]))
            ids = members.setdefault(row["id"], set())
            if row["duck_id"] is not None:  # a preset whose ducks were all removed
                ids.add(row["duck_id"])
        return [
            RosterPreset(id=pid, name=name, duck_ids=frozenset(members[pid]), is_default=default)
            for pid, (name, default) in headers.items()
        ]

    # ── changing who sits ────────────────────────────────────────────────────

    async def seat(self, duck_id: str, sitting: bool) -> None:
        if sitting:
            cursor = await self._db.execute("UPDATE ducks SET sitting = 1 WHERE id = ?", (duck_id,))
        else:
            # One statement, so the last-duck check and the change cannot be separated.
            cursor = await self._db.execute(
                "UPDATE ducks SET sitting = 0 WHERE id = ? "
                "AND (sitting = 0 OR (SELECT COUNT(*) FROM ducks WHERE sitting = 1) > 1)",
                (duck_id,),
            )
        await self._db.commit()
        if cursor.rowcount == 0:
            if await self.entry(duck_id) is None:
                raise BenchError("There is no such duck.")
            raise BenchError("The council needs at least one duck sitting.")

    async def apply_preset(self, preset_id: int) -> None:
        presets = {preset.id: preset for preset in await self.presets()}
        preset = presets.get(preset_id)
        if preset is None:
            raise BenchError("There is no such preset.")
        if not preset.duck_ids:
            # Every duck in it has been removed: fall back to the default (D23).
            preset = next(p for p in presets.values() if p.is_default)
        marks = ", ".join("?" for _ in preset.duck_ids)
        await self._db.execute(
            f"UPDATE ducks SET sitting = (id IN ({marks}))", tuple(preset.duck_ids)
        )
        await self._db.commit()

    async def save_preset(self, name: str) -> RosterPreset:
        """Save whoever is sitting now under `name`."""
        name = " ".join(name.split())
        if not name or len(name) > 40:
            raise BenchError("A preset needs a name of up to 40 characters.")
        try:
            cursor = await self._db.execute("INSERT INTO presets (name) VALUES (?)", (name,))
        except aiosqlite.IntegrityError:
            raise BenchError(f"There is already a preset called “{name}”.") from None
        preset_id = cursor.lastrowid
        await self._db.execute(
            "INSERT INTO preset_ducks (preset_id, duck_id) "
            "SELECT ?, id FROM ducks WHERE sitting = 1",
            (preset_id,),
        )
        await self._db.commit()
        return next(p for p in await self.presets() if p.id == preset_id)

    async def delete_preset(self, preset_id: int) -> None:
        cursor = await self._db.execute(
            "DELETE FROM presets WHERE id = ? AND is_default = 0", (preset_id,)
        )
        await self._db.commit()
        if cursor.rowcount == 0:
            raise BenchError("The default preset cannot be deleted.")

    # ── user ducks (D14): full create, edit and delete ───────────────────────

    async def add_duck(self, draft: DuckDraft, portrait: str | None = None) -> Duck:
        # "u" and random hex: always a valid duck id, never a built-in's.
        duck_id = f"u{secrets.token_hex(5)}"
        await self._db.execute(
            """
            INSERT INTO ducks (id, name, epithet, voice, weighs, blind_spot, portrait, origin,
                               position)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'user',
                    (SELECT COALESCE(MAX(position), 0) + 1 FROM ducks WHERE origin = 'user'))
            """,
            (duck_id, draft.name, draft.epithet, draft.voice, draft.weighs, draft.blind_spot,
             portrait),
        )  # fmt: skip
        await self._db.commit()
        entry = await self.entry(duck_id)
        assert entry is not None
        return entry.duck

    async def edit_duck(self, duck_id: str, draft: DuckDraft) -> Duck:
        cursor = await self._db.execute(
            "UPDATE ducks SET name = ?, epithet = ?, voice = ?, weighs = ?, blind_spot = ? "
            "WHERE id = ? AND origin = 'user'",
            (draft.name, draft.epithet, draft.voice, draft.weighs, draft.blind_spot, duck_id),
        )
        await self._db.commit()
        if cursor.rowcount == 0:
            raise BenchError("Only ducks you commissioned can be amended.")
        entry = await self.entry(duck_id)
        assert entry is not None
        return entry.duck

    async def set_portrait(self, duck_id: str, portrait: str | None) -> str | None:
        """Give one of your ducks a new portrait, or none. Returns the one it had before."""
        entry = await self.entry(duck_id)
        if entry is None or entry.duck.origin is not Origin.USER:
            raise BenchError("Only ducks you commissioned can have their portrait changed.")
        await self._db.execute(
            "UPDATE ducks SET portrait = ? WHERE id = ? AND origin = 'user'", (portrait, duck_id)
        )
        await self._db.commit()
        return entry.duck.portrait

    async def remove_duck(self, duck_id: str) -> None:
        cursor = await self._db.execute(
            "DELETE FROM ducks WHERE id = ? AND origin = 'user' "
            "AND NOT (sitting = 1 AND (SELECT COUNT(*) FROM ducks WHERE sitting = 1) = 1)",
            (duck_id,),
        )
        await self._db.commit()
        if cursor.rowcount == 0:
            entry = await self.entry(duck_id)
            if entry is None or entry.duck.origin is not Origin.USER:
                raise BenchError("Only ducks you commissioned can be removed.")
            raise BenchError("Seat another duck before removing the last one sitting.")
