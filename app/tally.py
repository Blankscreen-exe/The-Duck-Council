"""Turn a council's seats into its finding (D16). Pure arithmetic, no I/O."""

import math
import statistics
from collections.abc import Sequence

from app.schema import BAND_CENTRE, Band, Finding, Seat

MIDPOINT = BAND_CENTRE[Band.DEFENSIBLE]
"""Scores above this count in favour, below it against, exactly on it undecided."""


def _round_half_up(value: float) -> int:
    # Python's round() sends 52.5 to 52 (banker's rounding). A council median of
    # 52.5 should read as 53, the way a person would round it.
    return math.floor(value + 0.5)


def tally(seats: Sequence[Seat]) -> Finding:
    """Summarise the council. Seats must be in roster order; it settles ties in the widest gap."""
    votes = [(seat.duck.id, seat.verdict.score) for seat in seats if seat.verdict is not None]
    scores = [score for _, score in votes]

    if not votes:
        return Finding(
            sitting=len(seats),
            voted=0,
            median=None,
            in_favour=0,
            against=0,
            undecided=0,
            split=False,
            lowest=None,
            highest=None,
        )

    in_favour = sum(score > MIDPOINT for score in scores)
    against = sum(score < MIDPOINT for score in scores)

    # Split: at least a third of the voting ducks on each side (D30).
    # Integer comparison, so there is no floating-point edge at exactly one third.
    split = len(votes) >= 2 and 3 * min(in_favour, against) >= len(votes)

    low, high = min(scores), max(scores)
    has_gap = high > low
    return Finding(
        sitting=len(seats),
        voted=len(votes),
        median=_round_half_up(statistics.median(scores)),
        in_favour=in_favour,
        against=against,
        undecided=len(votes) - in_favour - against,
        split=split,
        lowest=next(duck_id for duck_id, s in votes if s == low) if has_gap else None,
        highest=next(duck_id for duck_id, s in votes if s == high) if has_gap else None,
    )
