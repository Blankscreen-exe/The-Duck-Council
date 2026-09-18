"""The SQLite database the app keeps its state in (D15), and its schema versions.

The Bench and Chambers share one connection. The schema version lives in
`PRAGMA user_version`; each migration below moves it up by one. A migration that
has shipped must never be edited, because it has already run on someone's
machine: changes go in a new migration after it.
"""

from pathlib import Path

import aiosqlite

MIGRATIONS: tuple[str, ...] = (
    # 1: the Bench (D14, D23)
    """
    CREATE TABLE ducks (
        id         TEXT    PRIMARY KEY,
        name       TEXT    NOT NULL,
        epithet    TEXT    NOT NULL,
        voice      TEXT    NOT NULL,
        weighs     TEXT    NOT NULL,
        blind_spot TEXT    NOT NULL,
        portrait   TEXT,
        origin     TEXT    NOT NULL CHECK (origin IN ('builtin', 'user')),
        position   INTEGER NOT NULL,
        sitting    INTEGER NOT NULL DEFAULT 1 CHECK (sitting IN (0, 1))
    );
    CREATE TABLE presets (
        id         INTEGER PRIMARY KEY,
        name       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
        is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1))
    );
    CREATE TABLE preset_ducks (
        preset_id INTEGER NOT NULL REFERENCES presets (id) ON DELETE CASCADE,
        duck_id   TEXT    NOT NULL REFERENCES ducks (id)   ON DELETE CASCADE,
        PRIMARY KEY (preset_id, duck_id)
    );
    """,
    # 2: Chambers (D38). API keys are never stored here: they live in the OS
    # credential store (D12), keyed by provider id.
    """
    CREATE TABLE providers (
        id            INTEGER PRIMARY KEY,
        preset        TEXT    NOT NULL,
        label         TEXT    NOT NULL,
        model         TEXT    NOT NULL,
        base_url      TEXT,
        effort        TEXT,
        is_default    INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
        checked_at    TEXT,
        check_ok      INTEGER CHECK (check_ok IN (0, 1)),
        check_message TEXT
    );
    -- At most one default provider, enforced by the database itself.
    CREATE UNIQUE INDEX one_default_provider ON providers (is_default) WHERE is_default = 1;
    """,
)


async def open_database(path: Path) -> aiosqlite.Connection:
    """Open (creating if needed) the database at `path`, migrated to the latest version."""
    path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute("PRAGMA journal_mode = WAL")

    async with db.execute("PRAGMA user_version") as cursor:
        row = await cursor.fetchone()
    version = int(row[0]) if row else 0
    for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
        await db.executescript(script)
        await db.execute(f"PRAGMA user_version = {number}")
    await db.commit()
    return db
