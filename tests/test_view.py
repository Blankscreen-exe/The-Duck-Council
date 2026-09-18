from app.ducks import DUCKS_BY_ID
from app.schema import Absence, Duck, Origin, Seat
from app.tally import tally
from app.web.view import finding_summary, monogram, monogram_hue, sse_event, verdict_word
from tests.fakes import verdict_scoring


def seat(duck_id: str, score: int | None) -> Seat:
    duck = DUCKS_BY_ID[duck_id]
    if score is None:
        return Seat(duck=duck, absence=Absence.TIMED_OUT)
    return Seat(duck=duck, verdict=verdict_scoring(score))


def test_the_finding_reads_like_a_sentence() -> None:
    seats = [seat("doctor", 12), seat("rich", 90), seat("king", 30), seat("witch", None)]
    text = finding_summary(tally(seats), seats)
    assert text == (
        "3 ducks ruled and 1 chair was left empty. 1 in favour, 2 against. "
        "The bench was furthest divided between Dr. Beakman Quackson, MD (12) "
        "and Sir Bill Quackington IV (90)."
    )


def test_verdict_words() -> None:
    assert verdict_word(tally([seat("doctor", 20), seat("rich", 80)])) == "A split decision"
    assert verdict_word(tally([seat("doctor", 80), seat("rich", 90)])) == "The bench is in favour"
    assert verdict_word(tally([seat("doctor", 20)])) == "The bench is against"


def test_a_monogram_is_initials_with_a_stable_colour() -> None:
    landlord = Duck(
        id="landlord",
        name="The Landlord",
        epithet="Weighs the deposit",
        voice="v",
        weighs="w",
        blind_spot="b",
        origin=Origin.USER,
    )
    assert monogram(landlord) == "TL"
    assert monogram_hue(landlord) == monogram_hue(landlord)


def test_every_line_of_a_multi_line_event_gets_its_own_data_prefix() -> None:
    assert sse_event("seat-king", "<p>\nhi\n</p>") == (
        "event: seat-king\ndata: <p>\ndata: hi\ndata: </p>\n\n"
    )
    assert sse_event("done", "") == "event: done\ndata: \n\n"
