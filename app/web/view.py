"""Presentation helpers the templates call: wording and styling choices, kept out of logic."""

import hashlib
from collections.abc import Sequence

from app.schema import Absence, Band, Duck, Finding, Seat
from app.web.loading import loading_lines

_COIN: dict[Band, str] = {
    Band.RECKLESS: "low",
    Band.UNWISE: "low",
    Band.DEFENSIBLE: "mid",
    Band.SOUND: "high",
    Band.CLEARLY_RIGHT: "high",
}

_ABSENCE: dict[Absence, str] = {
    Absence.REFUSED: "Declined to rule on this case.",
    Absence.TIMED_OUT: "Did not return in time.",
    Absence.FAILED: "Could not be reached.",
}


def coin_class(band: Band) -> str:
    """Orange at the reckless end, brass through the middle, sage at clearly right (D24)."""
    return _COIN[band]


def band_label(band: Band) -> str:
    return band.value.replace("_", " ").capitalize()


def absence_text(absence: Absence | None) -> str:
    return _ABSENCE[absence] if absence else ""


def verdict_word(finding: Finding) -> str:
    if finding.split:
        return "A split decision"
    if finding.in_favour > finding.against:
        return "The bench is in favour"
    if finding.against > finding.in_favour:
        return "The bench is against"
    return "The bench is undecided"


def finding_summary(finding: Finding, seats: Sequence[Seat]) -> str:
    """One paragraph a person would say out loud about the result."""
    names = {seat.duck.id: seat.duck.name for seat in seats}
    scores = {seat.duck.id: seat.verdict.score for seat in seats if seat.verdict is not None}

    ruled = f"{finding.voted} {'duck' if finding.voted == 1 else 'ducks'} ruled"
    empty = finding.sitting - finding.voted
    if empty:
        ruled += f" and {empty} {'chair was' if empty == 1 else 'chairs were'} left empty"
    parts = [f"{ruled}."]

    tally = f"{finding.in_favour} in favour, {finding.against} against"
    if finding.undecided:
        tally += f", {finding.undecided} undecided"
    parts.append(f"{tally}.")

    if finding.lowest and finding.highest:
        parts.append(
            f"The bench was furthest divided between {names[finding.lowest]} "
            f"({scores[finding.lowest]}) and {names[finding.highest]} ({scores[finding.highest]})."
        )
    return " ".join(parts)


def voted_seats(roster: Sequence[Duck], seats: Sequence[Seat]) -> list[Seat]:
    """Seats that returned a verdict, in roster order: the order the finding reads them."""
    by_id = {seat.duck.id: seat for seat in seats}
    return [seat for duck in roster if (seat := by_id.get(duck.id)) and seat.verdict is not None]


def monogram(duck: Duck) -> str:
    """Initials for a duck with no portrait (D14)."""
    words = [word for word in duck.name.split() if word[:1].isalnum()]
    return "".join(word[0] for word in words[:2]).upper() or "?"


def monogram_hue(duck: Duck) -> int:
    """A stable colour per duck, so the same duck always wears the same monogram."""
    return int(hashlib.sha256(duck.id.encode("utf-8")).hexdigest()[:4], 16) % 360


def sse_event(event: str, data: str) -> str:
    """Frame one server-sent event. Each line of `data` needs its own `data:` prefix."""
    lines = data.splitlines() or [""]
    return f"event: {event}\n" + "".join(f"data: {line}\n" for line in lines) + "\n"


TEMPLATE_GLOBALS = {
    "coin_class": coin_class,
    "band_label": band_label,
    "absence_text": absence_text,
    "verdict_word": verdict_word,
    "finding_summary": finding_summary,
    "voted_seats": voted_seats,
    "loading_lines": loading_lines,
    "monogram": monogram,
    "monogram_hue": monogram_hue,
}
