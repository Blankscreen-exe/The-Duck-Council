"""A finished hearing drawn as one image, to post anywhere (D45).

A card designed for sharing, not a screenshot of the page: 1080 pixels wide, which
every platform accepts, and as tall as it needs to be so that every verdict is
printed in full at a readable size. It is drawn here with Pillow in the Green
Bench's colours and the app's own bundled fonts, so it comes out the same on every
machine and needs no browser.

The layout is measured before anything is drawn: each block reports its height,
the canvas is made exactly tall enough, and then the blocks paint themselves.
"""

import colorsys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.schema import Case, Duck, Finding, Seat
from app.web.view import absence_text, band_label, coin_class, monogram, monogram_hue, verdict_word

WIDTH = 1080
PAD = 64
REPO = "github.com/Blankscreen-exe/The-Duck-Council"

FELT = (18, 59, 43)
FELT_DARK = (11, 36, 26)
CREAM = (247, 240, 222)
PAPER = (251, 245, 227)
BRASS = (199, 154, 46)
BRASS_LIGHT = (233, 197, 102)
INK = (20, 24, 15)
MUTED = (92, 90, 80)
COIN = {
    "low": ((217, 100, 30), (251, 246, 232)),
    "mid": ((199, 154, 46), (11, 36, 26)),
    "high": ((110, 155, 106), (251, 246, 232)),
    "empty": ((167, 160, 138), (251, 246, 232)),
}

_FONTS = Path(__file__).parent.parent / "static" / "fonts"
_BUILTIN_PORTRAITS = Path(__file__).parent.parent / "static" / "images"


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(_FONTS / f"{name}.woff2", size)


SERIF = _font("dm-serif-display-400", 38)
SERIF_ITALIC = _font("dm-serif-display-400-italic", 40)
SCORE = _font("dm-serif-display-400", 150)
NAME = _font("dm-serif-display-400", 36)
COIN_NUMBER = _font("dm-serif-display-400", 38)
BODY = _font("karla-400", 30)
BODY_BOLD = _font("karla-700", 30)
LABEL = _font("karla-700", 20)
SMALL = _font("karla-700", 22)


@dataclass(frozen=True)
class Block:
    height: int
    paint: Callable[[ImageDraw.ImageDraw, Image.Image, int], None]
    """Draws the block with its top edge at the given y."""


# ── text ─────────────────────────────────────────────────────────────────────────


def wrap(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    """Break text into lines no wider than `width`, keeping the writer's line breaks."""
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        line = ""
        for word in paragraph.split():
            # A single word wider than the line (a long URL) is broken by characters.
            while font.getlength(word) > width:
                cut = len(word)
                while cut > 1 and font.getlength(word[:cut]) > width:
                    cut -= 1
                if line:
                    lines.append(line)
                    line = ""
                lines.append(word[:cut])
                word = word[cut:]
            candidate = f"{line} {word}" if line else word
            if font.getlength(candidate) <= width:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def clip(lines: list[str], most: int, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    """At most `most` lines, the last ending in an ellipsis if anything was cut."""
    if len(lines) <= most:
        return lines
    last = lines[most - 1]
    while last and font.getlength(last + "…") > width:
        last = last[:-1]
    return [*lines[: most - 1], last.rstrip() + "…"]


def _line_height(font: ImageFont.FreeTypeFont, spacing: float = 1.4) -> int:
    return round(font.size * spacing)


def _text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    lines: Sequence[str],
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    spacing: float = 1.4,
) -> None:
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += _line_height(font, spacing)


def _spaced(text: str) -> str:
    """Small capitals with air between letters, as the page's labels are set."""
    return " ".join(text.upper())


# ── the parts of the card ───────────────────────────────────────────────────────


def _masthead(case: Case) -> Block:
    inner = WIDTH - 2 * PAD
    situation = clip(wrap(case.situation, BODY, inner), 5, BODY, inner)
    action = clip(wrap(case.action, BODY, inner), 5, BODY, inner)
    body = _line_height(BODY)
    height = 56 + 40 + 60 + 44 + len(situation) * body + 30 + 44 + len(action) * body + 60

    def paint(draw: ImageDraw.ImageDraw, card: Image.Image, top: int) -> None:
        draw.rectangle((0, top, WIDTH, top + height), fill=FELT)
        y = top + 56
        kick = _spaced("The Duck Council")
        draw.text(((WIDTH - LABEL.getlength(kick)) / 2, y), kick, font=LABEL, fill=BRASS_LIGHT)
        y += 40
        title = "The Council has heard this case"
        draw.text(((WIDTH - SERIF.getlength(title)) / 2, y), title, font=SERIF, fill=CREAM)
        y += 60 + 10
        draw.line((PAD, y - 18, WIDTH - PAD, y - 18), fill=BRASS, width=1)
        for number, label, lines in (
            ("I.", "The situation", situation),
            ("II.", "The action proposed", action),
        ):
            draw.text((PAD, y), number, font=SERIF, fill=BRASS_LIGHT)
            draw.text((PAD + 58, y + 12), _spaced(label), font=LABEL, fill=BRASS_LIGHT)
            y += 44 + 6
            _text(draw, (PAD, y), lines, BODY, CREAM)
            y += len(lines) * body + 24
        draw.rectangle((0, top + height - 8, WIDTH, top + height), fill=BRASS)

    return Block(height, paint)


def _finding(finding: Finding, seats: Sequence[Seat], heard_by: str) -> Block:
    scores = [(seat, seat.verdict.score) for seat in seats if seat.verdict is not None]
    height = 470 if finding.median is not None else 250

    def paint(draw: ImageDraw.ImageDraw, card: Image.Image, top: int) -> None:
        draw.rectangle((0, top, WIDTH, top + height), fill=FELT_DARK)
        y = top + 44
        kick = _spaced("The finding of the bench")
        draw.text(((WIDTH - LABEL.getlength(kick)) / 2, y), kick, font=LABEL, fill=BRASS_LIGHT)
        y += 40
        if finding.median is None:
            word = "Every chair is empty"
            draw.text(
                ((WIDTH - SERIF_ITALIC.getlength(word)) / 2, y), word, font=SERIF_ITALIC, fill=CREAM
            )
            y += 70
        else:
            number, out_of = str(finding.median), "/100"
            total = SCORE.getlength(number) + 8 + SERIF.getlength(out_of)
            x = (WIDTH - total) / 2
            draw.text((x, y), number, font=SCORE, fill=BRASS_LIGHT)
            draw.text(
                (x + SCORE.getlength(number) + 8, y + 104), out_of, font=SERIF, fill=(150, 150, 120)
            )
            y += 176
            word = verdict_word(finding)
            draw.text(
                ((WIDTH - SERIF_ITALIC.getlength(word)) / 2, y), word, font=SERIF_ITALIC, fill=CREAM
            )
            y += 64
        by = _spaced(f"Heard by {heard_by}") if len(heard_by) < 34 else f"Heard by {heard_by}"
        draw.text(((WIDTH - SMALL.getlength(by)) / 2, y), by, font=SMALL, fill=BRASS_LIGHT)
        if finding.median is None:
            return
        # The scale: every duck's mark, and the median's needle.
        y += 64
        left, right = PAD + 40, WIDTH - PAD - 40
        span = right - left
        draw.rounded_rectangle((left, y, right, y + 10), radius=5, fill=(40, 70, 55))
        for step in range(0, 101, 20):
            x = left + span * step / 100
            draw.line((x, y - 6, x, y + 16), fill=(80, 110, 90), width=2)
            tick = str(step)
            draw.text(
                (x - SMALL.getlength(tick) / 2, y + 26), tick, font=SMALL, fill=(170, 175, 150)
            )
        for seat, score in scores:
            assert seat.verdict is not None
            colour = COIN[coin_class(seat.verdict.band)][0]
            x = left + span * score / 100
            draw.ellipse((x - 12, y - 7, x + 12, y + 17), fill=colour, outline=FELT_DARK, width=3)
        x = left + span * finding.median / 100
        draw.polygon([(x - 11, y - 26), (x + 11, y - 26), (x, y - 8)], fill=BRASS_LIGHT)

    return Block(height, paint)


def _portrait(duck: Duck, portrait_path: Path | None, size: tuple[int, int]) -> Image.Image:
    if portrait_path is not None and portrait_path.is_file():
        with Image.open(portrait_path) as source:
            return ImageOps.fit(source.convert("RGB"), size, Image.Resampling.LANCZOS)
    # No portrait: the same monogram, in the same colour, as on the page.
    r, g, b = colorsys.hls_to_rgb(monogram_hue(duck) / 360, 0.38, 0.32)
    tile = Image.new("RGB", size, (round(r * 255), round(g * 255), round(b * 255)))
    draw = ImageDraw.Draw(tile)
    letters = monogram(duck)
    font = _font("dm-serif-display-400", 44)
    box = draw.textbbox((0, 0), letters, font=font)
    draw.text(
        ((size[0] - (box[2] - box[0])) / 2 - box[0], (size[1] - (box[3] - box[1])) / 2 - box[1]),
        letters,
        font=font,
        fill=CREAM,
    )
    return tile


def _seat(seat: Seat, portrait_path: Path | None) -> Block:
    photo_w, photo_h = 112, 138
    coin = 96
    text_left = PAD + 28 + photo_w + 28
    text_width = WIDTH - PAD - 28 - text_left
    head_width = text_width - coin - 20
    name = clip(wrap(seat.duck.name, NAME, head_width), 2, NAME, head_width)
    epithet = clip(wrap(seat.duck.epithet, SMALL, head_width), 2, SMALL, head_width)
    if seat.verdict is not None:
        words = wrap(seat.verdict.line, BODY, text_width)
        words_font, words_fill = BODY, INK
    else:
        words = wrap(absence_text(seat.absence), BODY, text_width)
        words_font, words_fill = BODY, MUTED
    head = len(name) * _line_height(NAME, 1.15) + 8 + len(epithet) * _line_height(SMALL, 1.3)
    head = max(head, coin + 26, photo_h - 30)
    height = 30 + head + 18 + len(words) * _line_height(words_font) + 30

    def paint(draw: ImageDraw.ImageDraw, card: Image.Image, top: int) -> None:
        box = (PAD, top, WIDTH - PAD, top + height)
        draw.rectangle((box[0] + 4, box[1] + 6, box[2] + 4, box[3] + 6), fill=(214, 204, 178))
        draw.rectangle(box, fill=PAPER, outline=(222, 210, 180), width=2)
        # the portrait, framed like the page's
        x, y = PAD + 28, top + 30
        draw.rectangle((x - 4, y - 4, x + photo_w + 4, y + photo_h + 4), fill=FELT)
        card.paste(_portrait(seat.duck, portrait_path, (photo_w, photo_h)), (x, y))
        draw.rectangle((x - 1, y - 1, x + photo_w, y + photo_h), outline=BRASS, width=1)
        # the name and card line
        ty = top + 28
        _text(draw, (text_left, ty), name, NAME, INK, 1.15)
        ty += len(name) * _line_height(NAME, 1.15) + 8
        _text(draw, (text_left, ty), epithet, SMALL, FELT, 1.3)
        # the medallion
        cx, cy = WIDTH - PAD - 28 - coin // 2, top + 30 + coin // 2
        if seat.verdict is not None:
            fill, number_colour = COIN[coin_class(seat.verdict.band)]
            number = str(seat.verdict.score)
            band = band_label(seat.verdict.band)
        else:
            fill, number_colour = COIN["empty"]
            number, band = "–", "Empty chair"  # an en dash
        draw.ellipse((cx - coin // 2, cy - coin // 2, cx + coin // 2, cy + coin // 2), fill=fill)
        draw.ellipse(
            (cx - coin // 2 + 5, cy - coin // 2 + 5, cx + coin // 2 - 5, cy + coin // 2 - 5),
            outline=(255, 255, 255),
            width=2,
        )
        nb = draw.textbbox((0, 0), number, font=COIN_NUMBER)
        draw.text(
            (cx - (nb[2] - nb[0]) / 2 - nb[0], cy - (nb[3] - nb[1]) / 2 - nb[1]),
            number,
            font=COIN_NUMBER,
            fill=number_colour,
        )
        label = band.upper()
        draw.text(
            (cx - LABEL.getlength(label) / 2, cy + coin // 2 + 6), label, font=LABEL, fill=MUTED
        )
        # the verdict, in full
        _text(draw, (text_left, top + 30 + head + 18), words, words_font, words_fill)

    return Block(height, paint)


def _footer() -> Block:
    height = 120

    def paint(draw: ImageDraw.ImageDraw, card: Image.Image, top: int) -> None:
        draw.rectangle((0, top, WIDTH, top + height), fill=FELT)
        draw.rectangle((0, top, WIDTH, top + 6), fill=BRASS)
        name = "The Duck Council"
        draw.text(((WIDTH - SERIF.getlength(name)) / 2, top + 22), name, font=SERIF, fill=CREAM)
        draw.text(
            ((WIDTH - SMALL.getlength(REPO)) / 2, top + 76), REPO, font=SMALL, fill=BRASS_LIGHT
        )

    return Block(height, paint)


def _gap(height: int) -> Block:
    return Block(height, lambda draw, card, top: None)


# ── the whole card ───────────────────────────────────────────────────────────────


def portrait_file(duck: Duck, uploaded: Callable[[str], Path | None]) -> Path | None:
    """Where a duck's portrait is on disk: built-ins ship with the app, yours are uploads."""
    if duck.portrait is None:
        return None
    if duck.origin.value == "user":
        return uploaded(duck.portrait)
    path = _BUILTIN_PORTRAITS / duck.portrait
    return path if path.is_file() else None


def render(
    *,
    case: Case,
    seats: Sequence[Seat],
    finding: Finding,
    heard_by: str,
    portraits: Callable[[Duck], Path | None],
) -> bytes:
    """The hearing as a PNG. `seats` in roster order; `portraits` finds a duck's image."""
    blocks = [_masthead(case), _finding(finding, seats, heard_by), _gap(44)]
    for seat in seats:
        blocks += [_seat(seat, portraits(seat.duck)), _gap(26)]
    blocks += [_gap(18), _footer()]

    card = Image.new("RGB", (WIDTH, sum(block.height for block in blocks)), CREAM)
    draw = ImageDraw.Draw(card)
    top = 0
    for block in blocks:
        block.paint(draw, card, top)
        top += block.height
    out = BytesIO()
    card.save(out, "PNG", optimize=True)
    return out.getvalue()
