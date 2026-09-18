"""Portraits people upload for their own ducks, kept in the app's data folder (D44).

Nothing uploaded is kept as it arrived. Each image is opened, checked, cropped to
a centred square, shrunk to `SIZE` and saved as a fresh JPEG. So every portrait
matches the built-ins, stays small, and carries no hidden metadata (a phone photo
can hold the GPS position it was taken at). Only something that decodes as a real
image survives the trip.

Files get random names. A name never comes from the person, so it can never point
anywhere outside the portraits folder.
"""

import asyncio
import re
import secrets
import warnings
from io import BytesIO
from pathlib import Path

import aiosqlite
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 5 * 1024 * 1024
MIN_SIDE = 256
SIZE = 512
ACCEPTED = {"JPEG", "PNG", "WEBP"}
ACCEPT_ATTRIBUTE = "image/jpeg,image/png,image/webp"
_PAPER = (247, 240, 222)  # --cream, behind any transparent parts
_NAME = re.compile(r"^[0-9a-f]{32}\.jpg$")

# A small file can still claim to be a gigantic image and exhaust memory when opened.
_MAX_PIXELS = 40_000_000


class PortraitError(ValueError):
    """An upload that cannot become a portrait. The message is shown to the person."""


def is_portrait_name(name: str) -> bool:
    return _NAME.fullmatch(name) is not None


def _process(data: bytes) -> bytes:
    if len(data) > MAX_BYTES:
        raise PortraitError("That image is over 5 MB. Choose a smaller one.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in ACCEPTED:
                    raise PortraitError("Use a JPEG, PNG or WebP image.")
                if image.width * image.height > _MAX_PIXELS:
                    raise PortraitError("That image is too large to open.")
                image.load()
                upright = ImageOps.exif_transpose(image)
    except PortraitError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise PortraitError("That file is not an image this app can read.") from None
    except (OSError, SyntaxError, ValueError):
        raise PortraitError("That image seems to be damaged.") from None

    if min(upright.size) < MIN_SIDE:
        raise PortraitError(
            f"That image is too small. Use one at least {MIN_SIDE} by {MIN_SIDE} pixels."
        )

    if upright.mode in ("RGBA", "LA", "P"):
        rgba = upright.convert("RGBA")
        flat = Image.new("RGB", rgba.size, _PAPER)
        flat.paste(rgba, mask=rgba.getchannel("A"))
        upright = flat
    square = ImageOps.fit(upright.convert("RGB"), (SIZE, SIZE), Image.Resampling.LANCZOS)
    out = BytesIO()
    square.save(out, "JPEG", quality=86, optimize=True)  # no EXIF passed: none is written
    return out.getvalue()


class PortraitStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    async def save(self, data: bytes) -> str:
        """Turn an upload into a portrait file. Returns its name."""
        jpeg = await asyncio.to_thread(_process, data)  # image work would stall every hearing
        name = f"{secrets.token_hex(16)}.jpg"
        self.directory.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread((self.directory / name).write_bytes, jpeg)
        return name

    def path(self, name: str) -> Path | None:
        """Where a portrait lives, or None for a name this store would never have made."""
        if not is_portrait_name(name):
            return None
        path = self.directory / name
        return path if path.is_file() else None

    def names(self) -> set[str]:
        if not self.directory.is_dir():
            return set()
        return {p.name for p in self.directory.iterdir() if is_portrait_name(p.name)}

    def delete(self, name: str) -> None:
        if is_portrait_name(name):
            (self.directory / name).unlink(missing_ok=True)


# ── which portraits are still wanted ─────────────────────────────────────────────
# A portrait is in use while a duck wears it, or while an old hearing in the Register
# shows it (each hearing keeps a copy of its ducks as they were, D43).


async def in_use(db: aiosqlite.Connection, name: str) -> bool:
    async with db.execute(
        "SELECT 1 FROM ducks WHERE portrait = ? UNION ALL "
        "SELECT 1 FROM hearing_seats WHERE json_extract(duck, '$.portrait') = ? LIMIT 1",
        (name, name),
    ) as cursor:
        return await cursor.fetchone() is not None


async def all_in_use(db: aiosqlite.Connection) -> set[str]:
    async with db.execute(
        "SELECT portrait FROM ducks WHERE portrait IS NOT NULL UNION "
        "SELECT json_extract(duck, '$.portrait') FROM hearing_seats"
    ) as cursor:
        return {row[0] for row in await cursor.fetchall() if row[0]}


async def let_go(store: PortraitStore, db: aiosqlite.Connection, name: str | None) -> None:
    """Delete a portrait nobody wears or shows any more. Called once it is replaced."""
    if name and not await in_use(db, name):
        store.delete(name)


async def tidy(store: PortraitStore, db: aiosqlite.Connection) -> None:
    """At startup: delete portraits left behind (by a struck-out hearing, say)."""
    for name in store.names() - await all_in_use(db):
        store.delete(name)
