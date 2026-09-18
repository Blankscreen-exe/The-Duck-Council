from app.ducks import BUILTIN_DUCKS, DUCKS_BY_ID
from app.schema import Absence, Seat
from app.tally import tally
from tests.fakes import verdict_scoring


def seats_scoring(**scores: int | None) -> list[Seat]:
    """Seats in the given order; None means that duck's chair is empty."""
    return [
        Seat(duck=DUCKS_BY_ID[duck_id], absence=Absence.FAILED)
        if score is None
        else Seat(duck=DUCKS_BY_ID[duck_id], verdict=verdict_scoring(score))
        for duck_id, score in scores.items()
    ]


def test_the_mockup_council() -> None:
    # The scene in docs/theme/4-greenbench.html, with a built-in duck in the landlord's seat.
    finding = tally(
        seats_scoring(
            lawyer=34, witch=72, serial_killer=94, doctor=12, gangsta=55, gamer=68, king=30
        )
    )
    assert finding.median == 55
    assert (finding.in_favour, finding.against, finding.undecided) == (4, 3, 0)
    assert finding.split
    assert (finding.lowest, finding.highest) == ("doctor", "serial_killer")


def test_even_councils_round_the_median_half_up() -> None:
    assert tally(seats_scoring(doctor=30, rich=75)).median == 53  # 52.5, not banker's 52


def test_empty_chairs_do_not_vote() -> None:
    finding = tally(seats_scoring(doctor=10, rich=None, rebel=90))
    assert (finding.sitting, finding.voted) == (3, 2)
    assert finding.median == 50


def test_a_council_of_empty_chairs_finds_nothing() -> None:
    finding = tally(seats_scoring(doctor=None, rich=None))
    assert finding.median is None
    assert not finding.split
    assert finding.lowest is None


def test_a_third_on_each_side_is_a_split() -> None:
    seven = [duck.id for duck in BUILTIN_DUCKS[:7]]
    three_against_four = dict(zip(seven, [20] * 3 + [80] * 4, strict=True))
    two_against_five = dict(zip(seven, [20] * 2 + [80] * 5, strict=True))
    assert tally(seats_scoring(**three_against_four)).split
    assert not tally(seats_scoring(**two_against_five)).split


def test_one_duck_is_never_split() -> None:
    assert not tally(seats_scoring(doctor=10)).split


def test_exactly_fifty_is_undecided() -> None:
    finding = tally(seats_scoring(doctor=50, rich=90))
    assert (finding.in_favour, finding.against, finding.undecided) == (1, 0, 1)


def test_a_unanimous_score_has_no_widest_gap() -> None:
    finding = tally(seats_scoring(doctor=70, rich=70))
    assert finding.lowest is None and finding.highest is None


def test_ties_in_the_gap_go_to_the_first_duck_in_roster_order() -> None:
    finding = tally(seats_scoring(lawyer=10, doctor=10, rich=90, rebel=90))
    assert (finding.lowest, finding.highest) == ("lawyer", "rich")
