"""Where API keys live: the operating system's credential store, never the database (D12, D18).

On Windows that is the Credential Manager, reached through the `keyring` library.
A key goes in once, is read only when a provider is built, and is never sent back
to the browser: the page only ever sees its last four characters.

`KeyStore` is an interface because it has two real implementations: the OS store
for the app, and an in-memory one so that tests never write into the owner's
actual credential store.
"""

from contextlib import suppress
from typing import Protocol

import keyring
import keyring.backends.fail
import keyring.errors


class KeyStore(Protocol):
    writable: bool
    """False when this machine has no credential store, so keys cannot be kept."""

    def get(self, name: str) -> str | None: ...

    def put(self, name: str, value: str) -> None: ...

    def delete(self, name: str) -> None: ...


class OsKeyStore:
    """The operating system's credential store."""

    SERVICE = "duck-council"

    def __init__(self) -> None:
        self.writable = not isinstance(keyring.get_keyring(), keyring.backends.fail.Keyring)

    def get(self, name: str) -> str | None:
        return keyring.get_password(self.SERVICE, name)

    def put(self, name: str, value: str) -> None:
        keyring.set_password(self.SERVICE, name, value)

    def delete(self, name: str) -> None:
        with suppress(keyring.errors.PasswordDeleteError):  # already gone is fine
            keyring.delete_password(self.SERVICE, name)


class MemoryKeyStore:
    """Keys in a dictionary: for tests, so the real credential store is never touched."""

    def __init__(self, *, writable: bool = True) -> None:
        self.writable = writable
        self.keys: dict[str, str] = {}

    def get(self, name: str) -> str | None:
        return self.keys.get(name)

    def put(self, name: str, value: str) -> None:
        self.keys[name] = value

    def delete(self, name: str) -> None:
        self.keys.pop(name, None)


def key_hint(key: str) -> str:
    """What the page may show of a key: its last four characters, and only for long keys."""
    return f"…{key[-4:]}" if len(key) >= 12 else "set"
