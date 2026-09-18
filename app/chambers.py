"""Chambers: the AI providers the council can use, and which one it uses (D31, D38).

A saved list, one of which is the default that hearings use. Each entry keeps the
result of its last connection check; one that is failing can stay on the list but
cannot become the default. The demo is always on the list and cannot be removed,
so there is always something that works (D17).

Settings live in SQLite; API keys live in the OS credential store (`keystore.py`).
Building a real provider is injected (`build`), so tests can check behaviour
without contacting any service.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import aiosqlite
from pydantic import SecretStr

from app.keystore import KeyStore, key_hint
from app.providers import (
    PRESETS,
    PRESETS_BY_ID,
    ConnectionCheck,
    Preset,
    Provider,
    ProviderConfig,
    build_provider,
)
from app.providers.base import Effort

# Custom commands stay terminal-only (owner's call): a web form that makes the server
# run a program you name is the one field an attacker would most want.
ADDABLE: tuple[Preset, ...] = tuple(p for p in PRESETS if p.kind not in ("demo", "command"))
ADDABLE_BY_ID = {preset.id: preset for preset in ADDABLE}

EFFORTS: tuple[Effort, ...] = ("low", "medium", "high", "xhigh", "max")
TAKES_EFFORT = frozenset({"claude_code", "anthropic"})

Builder = Callable[[ProviderConfig], Provider]


class ChambersError(ValueError):
    """Something a person asked for that Chambers will not do. Fit to show them."""


@dataclass(frozen=True)
class SavedProvider:
    id: int
    preset: Preset
    label: str
    model: str
    base_url: str | None
    effort: Effort | None
    is_default: bool
    check: ConnectionCheck | None
    checked_at: str | None
    key_hint: str | None

    @property
    def is_demo(self) -> bool:
        return self.preset.kind == "demo"

    @property
    def usable(self) -> bool:
        """Fit to be the default: the demo always, anything else only after a passing check."""
        return self.is_demo or (self.check is not None and self.check.ok)


def _key_name(provider_id: int) -> str:
    return f"provider-{provider_id}"


def _effort(value: str | None) -> Effort | None:
    return next((effort for effort in EFFORTS if effort == value), None)


class Chambers:
    def __init__(
        self, db: aiosqlite.Connection, keystore: KeyStore, build: Builder = build_provider
    ) -> None:
        self._db = db
        self._keystore = keystore
        self._build = build
        self.current: SavedProvider
        """The default provider's settings, kept in step with the database."""
        self.provider: Provider
        """The default provider itself, built once and rebuilt when it changes."""

    @property
    def can_keep_keys(self) -> bool:
        return self._keystore.writable

    async def sync(self) -> None:
        """Make sure the demo is on the list, and that something is the default."""
        await self._db.execute(
            "INSERT INTO providers (preset, label, model, is_default) "
            "SELECT 'demo', ?, 'demo', NOT EXISTS (SELECT 1 FROM providers WHERE is_default = 1) "
            "WHERE NOT EXISTS (SELECT 1 FROM providers WHERE preset = 'demo')",
            (PRESETS_BY_ID["demo"].label,),
        )
        await self._db.execute(
            "UPDATE providers SET is_default = 1 WHERE preset = 'demo' "
            "AND NOT EXISTS (SELECT 1 FROM providers WHERE is_default = 1)"
        )
        await self._db.commit()
        await self._refresh()

    # ── reading ──────────────────────────────────────────────────────────────

    def _saved(self, row: aiosqlite.Row) -> SavedProvider:
        key = self._keystore.get(_key_name(row["id"]))
        check = None
        if row["check_ok"] is not None:
            check = ConnectionCheck(ok=bool(row["check_ok"]), message=row["check_message"] or "")
        return SavedProvider(
            id=row["id"],
            preset=PRESETS_BY_ID[row["preset"]],
            label=row["label"],
            model=row["model"],
            base_url=row["base_url"],
            effort=_effort(row["effort"]),
            is_default=bool(row["is_default"]),
            check=check,
            checked_at=row["checked_at"],
            key_hint=key_hint(key) if key else None,
        )

    async def all(self) -> list[SavedProvider]:
        async with self._db.execute(
            "SELECT * FROM providers ORDER BY preset = 'demo' DESC, id"
        ) as cursor:
            rows = await cursor.fetchall()
        return [self._saved(row) for row in rows]

    async def get(self, provider_id: int) -> SavedProvider | None:
        async with self._db.execute(
            "SELECT * FROM providers WHERE id = ?", (provider_id,)
        ) as cursor:
            row = await cursor.fetchone()
        return self._saved(row) if row else None

    async def has_preset(self, preset_id: str) -> bool:
        async with self._db.execute(
            "SELECT 1 FROM providers WHERE preset = ?", (preset_id,)
        ) as cursor:
            return await cursor.fetchone() is not None

    def build(self, saved: SavedProvider) -> Provider:
        key = self._keystore.get(_key_name(saved.id))
        config = ProviderConfig(
            kind=saved.preset.kind,
            model=saved.model,
            base_url=saved.base_url,
            api_key=SecretStr(key) if key else None,
            effort=saved.effort,
        )
        return self._build(config)

    async def _refresh(self) -> None:
        async with self._db.execute("SELECT * FROM providers WHERE is_default = 1") as cursor:
            row = await cursor.fetchone()
        assert row is not None, "sync() guarantees a default provider"
        self.current = self._saved(row)
        self.provider = self.build(self.current)

    # ── changing the list ────────────────────────────────────────────────────

    def _clean(
        self, preset: Preset, model: str, base_url: str | None, key: str | None
    ) -> tuple[str, str | None]:
        model = model.strip() or preset.default_model
        if not model:
            raise ChambersError("Enter the model to use.")
        base_url = (base_url or "").strip() or preset.base_url
        if preset.kind == "openai_compatible" and not base_url:
            raise ChambersError("Enter the endpoint's base URL.")
        if key and not self._keystore.writable:
            raise ChambersError("This system has no credential store, so keys cannot be kept.")
        return model, base_url or None

    async def add(
        self,
        preset_id: str,
        *,
        model: str = "",
        base_url: str | None = None,
        api_key: str | None = None,
        label: str = "",
        effort: str | None = "low",
    ) -> SavedProvider:
        preset = ADDABLE_BY_ID.get(preset_id)
        if preset is None:
            raise ChambersError("That provider cannot be added here.")
        key = (api_key or "").strip() or None
        if preset.requires_key and not key:
            raise ChambersError(f"{preset.label} needs an API key.")
        model, base_url = self._clean(preset, model, base_url, key)
        cursor = await self._db.execute(
            "INSERT INTO providers (preset, label, model, base_url, effort) VALUES (?, ?, ?, ?, ?)",
            (preset.id, label.strip() or preset.label, model, base_url,
             _effort(effort) if preset.kind in TAKES_EFFORT else None),
        )  # fmt: skip
        await self._db.commit()
        assert cursor.lastrowid is not None
        if key:
            self._keystore.put(_key_name(cursor.lastrowid), key)
        saved = await self.get(cursor.lastrowid)
        assert saved is not None
        return saved

    async def amend(
        self,
        provider_id: int,
        *,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        label: str = "",
        effort: str | None = "low",
    ) -> SavedProvider:
        """A blank key means keep the one already stored: the form never holds the real key."""
        saved = await self.get(provider_id)
        if saved is None or saved.is_demo:
            raise ChambersError("That provider cannot be amended.")
        key = (api_key or "").strip() or None
        model, base_url = self._clean(saved.preset, model, base_url, key)
        # Changed settings mean the old check no longer says anything about this provider.
        await self._db.execute(
            "UPDATE providers SET label = ?, model = ?, base_url = ?, effort = ?, "
            "checked_at = NULL, check_ok = NULL, check_message = NULL WHERE id = ?",
            (label.strip() or saved.preset.label, model, base_url,
             _effort(effort) if saved.preset.kind in TAKES_EFFORT else None, provider_id),
        )  # fmt: skip
        await self._db.commit()
        if key:
            self._keystore.put(_key_name(provider_id), key)
        if saved.is_default:
            await self._refresh()
        amended = await self.get(provider_id)
        assert amended is not None
        return amended

    async def remove(self, provider_id: int) -> None:
        saved = await self.get(provider_id)
        if saved is None or saved.is_demo:
            raise ChambersError("The demo cannot be removed.")
        await self._db.execute("DELETE FROM providers WHERE id = ?", (provider_id,))
        if saved.is_default:
            await self._db.execute("UPDATE providers SET is_default = 1 WHERE preset = 'demo'")
        await self._db.commit()
        self._keystore.delete(_key_name(provider_id))
        await self._refresh()

    async def make_default(self, provider_id: int) -> None:
        saved = await self.get(provider_id)
        if saved is None:
            raise ChambersError("There is no such provider.")
        if not saved.usable:
            raise ChambersError(
                f"{saved.label} has to pass its connection test before it can be the default."
            )
        # Two statements in one transaction; the unique index forbids two defaults at once.
        await self._db.execute("UPDATE providers SET is_default = 0 WHERE is_default = 1")
        await self._db.execute("UPDATE providers SET is_default = 1 WHERE id = ?", (provider_id,))
        await self._db.commit()
        await self._refresh()

    async def check(self, provider_id: int) -> SavedProvider:
        """Test the connection and remember the answer."""
        saved = await self.get(provider_id)
        if saved is None:
            raise ChambersError("There is no such provider.")
        try:
            result = await self.build(saved).check_connection()
        except ValueError as error:  # e.g. settings the adapter itself rejects
            result = ConnectionCheck(ok=False, message=str(error))
        await self._db.execute(
            "UPDATE providers SET checked_at = ?, check_ok = ?, check_message = ? WHERE id = ?",
            (datetime.now(UTC).isoformat(timespec="seconds"), int(result.ok), result.message,
             provider_id),
        )  # fmt: skip
        await self._db.commit()
        if saved.is_default:
            await self._refresh()
        checked = await self.get(provider_id)
        assert checked is not None
        return checked
