"""The bench against real SQLite in a temporary file: the same code the app runs."""

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

import aiosqlite
import pytest

from app.bench import MIGRATIONS, Bench, BenchError, DuckDraft
from app.ducks import BUILTIN_DUCKS, DEFAULT_PRESET, DEFAULT_ROSTER
from app.schema import Origin

DRAFT = DuckDraft(
    name="The Landlord",
    epithet="Weighs the deposit · blind to friendship",
    voice="Terse, and always mentions the tenancy agreement.",
    weighs="Property, liability and the deposit.",
    blind_spot="Friendship.",
)


def on_bench[T](path: Path, action: Callable[[Bench], Awaitable[T]]) -> T:
    """Open the bench at `path`, run `action`, close it again."""

    async def run() -> T:
        bench = await Bench.open(path)
        try:
            return await action(bench)
        finally:
            await bench.close()

    return asyncio.run(run())


@pytest.fixture
def db(tmp_path: Path) -> Path:
    return tmp_path / "council.db"


def test_a_new_bench_seats_the_quackorum_and_nobody_else(db: Path) -> None:
    async def check(bench: Bench) -> None:
        assert {duck.id for duck in await bench.roster()} == set(DEFAULT_ROSTER)
        assert len(await bench.entries()) == len(BUILTIN_DUCKS)  # everyone is on the bench
        (preset,) = await bench.presets()
        assert preset.name == DEFAULT_PRESET and preset.is_default
        assert preset.duck_ids == set(DEFAULT_ROSTER)

    on_bench(db, check)


def test_reopening_keeps_choices_and_takes_builtin_text_from_the_code(db: Path) -> None:
    async def tamper(bench: Bench) -> None:
        await bench.seat("doctor", sitting=False)
        await bench.seat("king", sitting=True)
        await bench._db.execute("UPDATE ducks SET voice = 'stale' WHERE id = 'king'")
        await bench._db.commit()

    on_bench(db, tamper)

    async def check(bench: Bench) -> None:
        king = await bench.entry("king")
        doctor = await bench.entry("doctor")
        assert king is not None and king.duck.voice != "stale"  # code wins for built-ins
        assert king.sitting and doctor is not None and not doctor.sitting  # choices survive

    on_bench(db, check)


def test_the_schema_is_versioned_and_migrations_run_once(db: Path) -> None:
    on_bench(db, lambda bench: bench.roster())
    on_bench(db, lambda bench: bench.roster())  # reopening must not re-run CREATE TABLE

    async def version() -> int:
        async with (
            aiosqlite.connect(db) as connection,
            connection.execute("PRAGMA user_version") as cursor,
        ):
            row = await cursor.fetchone()
        assert row is not None
        return int(row[0])

    assert asyncio.run(version()) == len(MIGRATIONS)


def test_the_last_sitting_duck_cannot_stand_down(db: Path) -> None:
    async def check(bench: Bench) -> None:
        for duck in BUILTIN_DUCKS[1:]:
            await bench.seat(duck.id, sitting=False)
        with pytest.raises(BenchError, match="at least one duck"):
            await bench.seat(BUILTIN_DUCKS[0].id, sitting=False)
        assert len(await bench.roster()) == 1

    on_bench(db, check)


def test_user_ducks_can_be_commissioned_amended_and_removed(db: Path) -> None:
    async def check(bench: Bench) -> None:
        duck = await bench.add_duck(DRAFT)
        assert duck.origin is Origin.USER and duck.portrait is None
        assert (await bench.roster())[-1].id == duck.id  # sits, after the built-ins

        amended = await bench.edit_duck(duck.id, DRAFT.model_copy(update={"name": "Landlady"}))
        assert amended.name == "Landlady"

        await bench.remove_duck(duck.id)
        assert await bench.entry(duck.id) is None

    on_bench(db, check)


def test_builtin_ducks_cannot_be_amended_or_removed(db: Path) -> None:
    async def check(bench: Bench) -> None:
        with pytest.raises(BenchError, match="commissioned"):
            await bench.edit_duck("king", DRAFT)
        with pytest.raises(BenchError, match="commissioned"):
            await bench.remove_duck("king")

    on_bench(db, check)


def test_the_last_sitting_duck_cannot_be_removed(db: Path) -> None:
    async def check(bench: Bench) -> None:
        duck = await bench.add_duck(DRAFT)
        for other in BUILTIN_DUCKS:
            await bench.seat(other.id, sitting=False)
        with pytest.raises(BenchError, match="last one sitting"):
            await bench.remove_duck(duck.id)

    on_bench(db, check)


def test_presets_save_and_restore_who_sits(db: Path) -> None:
    async def check(bench: Bench) -> None:
        for duck in BUILTIN_DUCKS[2:]:
            await bench.seat(duck.id, sitting=False)
        pair = await bench.save_preset("  The   First   Two ")
        assert pair.name == "The First Two"
        assert pair.duck_ids == {BUILTIN_DUCKS[0].id, BUILTIN_DUCKS[1].id}

        default = next(p for p in await bench.presets() if p.is_default)
        await bench.apply_preset(default.id)
        assert {duck.id for duck in await bench.roster()} == set(DEFAULT_ROSTER)

        await bench.apply_preset(pair.id)
        assert {duck.id for duck in await bench.roster()} == pair.duck_ids

    on_bench(db, check)


def test_preset_names_are_unique_ignoring_case(db: Path) -> None:
    async def check(bench: Bench) -> None:
        with pytest.raises(BenchError, match="already a preset"):
            await bench.save_preset(DEFAULT_PRESET.upper())

    on_bench(db, check)


def test_a_preset_emptied_by_removals_falls_back_to_the_default(db: Path) -> None:
    async def check(bench: Bench) -> None:
        duck = await bench.add_duck(DRAFT)
        for other in BUILTIN_DUCKS:
            await bench.seat(other.id, sitting=False)
        only_mine = await bench.save_preset("Just mine")
        await bench.seat(BUILTIN_DUCKS[0].id, sitting=True)
        await bench.remove_duck(duck.id)

        await bench.apply_preset(only_mine.id)  # its only duck is gone
        assert {duck.id for duck in await bench.roster()} == set(DEFAULT_ROSTER)

    on_bench(db, check)


def test_the_default_preset_cannot_be_deleted(db: Path) -> None:
    async def check(bench: Bench) -> None:
        default = next(p for p in await bench.presets() if p.is_default)
        with pytest.raises(BenchError, match="default"):
            await bench.delete_preset(default.id)
        mine = await bench.save_preset("Mine")
        await bench.delete_preset(mine.id)
        assert [p.name for p in await bench.presets()] == [DEFAULT_PRESET]

    on_bench(db, check)
