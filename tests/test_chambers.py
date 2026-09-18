"""Chambers against real SQLite, an in-memory key store and a fake provider builder."""

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

import aiosqlite
import pytest

from app.chambers import Chambers, ChambersError
from app.keystore import MemoryKeyStore
from app.storage import open_database
from tests.fakes import FakeBuilder

KEY = "sk-ant-api03-very-secret-3f9a"


def in_chambers[T](
    db_path: Path,
    action: Callable[[Chambers], Awaitable[T]],
    *,
    keystore: MemoryKeyStore | None = None,
    builder: FakeBuilder | None = None,
) -> T:
    async def run() -> T:
        db = await open_database(db_path)
        chambers = Chambers(db, keystore or MemoryKeyStore(), builder or FakeBuilder())
        await chambers.sync()
        try:
            return await action(chambers)
        finally:
            await db.close()

    return asyncio.run(run())


@pytest.fixture
def db(tmp_path: Path) -> Path:
    return tmp_path / "council.db"


def test_a_fresh_install_has_only_the_demo_and_it_is_the_default(db: Path) -> None:
    async def check(chambers: Chambers) -> None:
        (demo,) = await chambers.all()
        assert demo.is_demo and demo.is_default and demo.usable
        assert chambers.current.id == demo.id
        assert chambers.provider.name == "demo"

    in_chambers(db, check)


def test_a_key_lives_in_the_key_store_and_nowhere_in_the_database(db: Path) -> None:
    keystore = MemoryKeyStore()

    async def add(chambers: Chambers) -> None:
        saved = await chambers.add("anthropic", api_key=KEY)
        assert saved.key_hint == "…3f9a"
        assert keystore.keys == {f"provider-{saved.id}": KEY}

    in_chambers(db, add, keystore=keystore)
    for part in db.parent.glob(db.name + "*"):  # the database and its write-ahead log
        assert KEY.encode() not in part.read_bytes(), part.name


def test_providers_that_need_a_key_refuse_to_be_added_without_one(db: Path) -> None:
    async def check(chambers: Chambers) -> None:
        with pytest.raises(ChambersError, match="needs an API key"):
            await chambers.add("anthropic")
        with pytest.raises(ChambersError, match="base URL"):
            await chambers.add("custom", api_key=KEY, model="m")

    in_chambers(db, check)


@pytest.mark.parametrize("preset", ["command", "demo"])
def test_custom_commands_and_extra_demos_cannot_be_added(db: Path, preset: str) -> None:
    async def check(chambers: Chambers) -> None:
        with pytest.raises(ChambersError, match="cannot be added here"):
            await chambers.add(preset, model="x")

    in_chambers(db, check)


def test_a_passing_provider_can_become_the_default_and_is_built_with_its_key(
    db: Path,
) -> None:
    builder = FakeBuilder()

    async def check(chambers: Chambers) -> None:
        saved = await chambers.add("anthropic", api_key=KEY, model="claude-opus-5")
        assert (await chambers.check(saved.id)).usable
        await chambers.make_default(saved.id)
        assert chambers.current.id == saved.id
        assert chambers.provider.name == "anthropic"
        config = builder.built[-1]
        assert config.api_key is not None and config.api_key.get_secret_value() == KEY

    in_chambers(db, check, builder=builder)


def test_a_failing_or_untested_provider_cannot_be_the_default(db: Path) -> None:
    async def check(chambers: Chambers) -> None:
        untested = await chambers.add("ollama")
        with pytest.raises(ChambersError, match="pass its connection test"):
            await chambers.make_default(untested.id)

        broken = await chambers.add("anthropic", api_key=KEY, model="broken")
        checked = await chambers.check(broken.id)
        assert checked.check is not None and checked.check.message == "Invalid API key."
        with pytest.raises(ChambersError, match="pass its connection test"):
            await chambers.make_default(broken.id)
        assert chambers.current.is_demo

    in_chambers(db, check)


def test_amending_with_a_blank_key_keeps_it_and_forgets_the_old_test(db: Path) -> None:
    keystore = MemoryKeyStore()

    async def check(chambers: Chambers) -> None:
        saved = await chambers.add("anthropic", api_key=KEY)
        await chambers.check(saved.id)
        amended = await chambers.amend(saved.id, model="claude-sonnet-5", api_key="")
        assert amended.model == "claude-sonnet-5"
        assert amended.check is None  # new settings, so the old result no longer applies
        assert keystore.keys[f"provider-{saved.id}"] == KEY

        await chambers.amend(saved.id, model="claude-sonnet-5", api_key="sk-new-key-0000abcd")
        assert keystore.keys[f"provider-{saved.id}"] == "sk-new-key-0000abcd"

    in_chambers(db, check, keystore=keystore)


def test_removing_the_default_falls_back_to_the_demo_and_deletes_the_key(db: Path) -> None:
    keystore = MemoryKeyStore()

    async def check(chambers: Chambers) -> None:
        saved = await chambers.add("anthropic", api_key=KEY)
        await chambers.check(saved.id)
        await chambers.make_default(saved.id)
        await chambers.remove(saved.id)
        assert chambers.current.is_demo
        assert keystore.keys == {}

        with pytest.raises(ChambersError, match="demo cannot be removed"):
            await chambers.remove(chambers.current.id)

    in_chambers(db, check, keystore=keystore)


def test_the_database_itself_refuses_two_defaults(db: Path) -> None:
    async def check(chambers: Chambers) -> None:
        await chambers.add("ollama")
        with pytest.raises(aiosqlite.IntegrityError):
            await chambers._db.execute("UPDATE providers SET is_default = 1")

    in_chambers(db, check)


def test_keys_are_refused_where_there_is_no_credential_store(db: Path) -> None:
    async def check(chambers: Chambers) -> None:
        assert not chambers.can_keep_keys
        with pytest.raises(ChambersError, match="no credential store"):
            await chambers.add("anthropic", api_key=KEY)

    in_chambers(db, check, keystore=MemoryKeyStore(writable=False))
