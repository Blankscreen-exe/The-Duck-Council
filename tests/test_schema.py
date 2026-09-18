import pytest
from pydantic import ValidationError

from app.ducks import DUCKS_BY_ID
from app.schema import BAND_CENTRE, NUDGE_LIMIT, Absence, Band, Case, Seat, Verdict


def test_score_is_band_centre_plus_nudge() -> None:
    verdict = Verdict(read="r", band=Band.SOUND, nudge=-3, line="l")
    assert verdict.score == BAND_CENTRE[Band.SOUND] - 3


def test_every_possible_verdict_scores_within_0_to_100() -> None:
    scores = {
        Verdict(read="r", band=band, nudge=nudge, line="l").score
        for band in Band
        for nudge in range(-NUDGE_LIMIT, NUDGE_LIMIT + 1)
    }
    assert min(scores) == 0
    assert max(scores) == 100


@pytest.mark.parametrize("nudge", [-NUDGE_LIMIT - 1, NUDGE_LIMIT + 1])
def test_nudge_outside_the_limit_is_rejected(nudge: int) -> None:
    with pytest.raises(ValidationError):
        Verdict(read="r", band=Band.DEFENSIBLE, nudge=nudge, line="l")


def test_verdict_asks_for_reasoning_before_the_band() -> None:
    # D4: generation is left to right, so field order is a design decision, not style.
    assert list(Verdict.model_fields) == ["read", "band", "nudge", "line"]


def test_verdict_rejects_a_model_emitting_its_own_score() -> None:
    with pytest.raises(ValidationError):
        Verdict.model_validate({"read": "r", "band": "sound", "nudge": 0, "line": "l", "score": 99})


def test_seat_needs_exactly_one_outcome() -> None:
    duck = DUCKS_BY_ID["king"]
    verdict = Verdict(read="r", band=Band.SOUND, nudge=0, line="l")
    with pytest.raises(ValidationError):
        Seat(duck=duck)
    with pytest.raises(ValidationError):
        Seat(duck=duck, verdict=verdict, absence=Absence.FAILED)


def test_case_is_trimmed_and_cannot_be_blank() -> None:
    assert Case(situation="  a  ", action=" b ").situation == "a"
    with pytest.raises(ValidationError):
        Case(situation="   ", action="b")
