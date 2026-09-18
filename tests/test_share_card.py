"""The hearing as an image to share (D45)."""

from io import BytesIO
from pathlib import Path

from PIL import Image

from app.ducks import DUCKS_BY_ID
from app.schema import Absence, Case, Seat
from app.tally import tally
from app.web.share_card import BODY, WIDTH, render, wrap
from tests.fakes import Script, verdict_scoring
from tests.test_web import CASE, FROM_PAGE, file_case, read_events, scripted
from tests.test_web_register import app_on, hear

SHORT = Case(situation="My flatmate eats my food.", action="Hide a ghost pepper in it.")


def seats(line: str, count: int = 3) -> list[Seat]:
    ducks = [DUCKS_BY_ID[d] for d in ("lawyer", "doctor", "rich", "witch", "king")][:count]
    return [
        Seat(duck=duck, verdict=verdict_scoring(20 + 20 * i, line)) for i, duck in enumerate(ducks)
    ]


def card(case: Case = SHORT, sitting: list[Seat] | None = None) -> Image.Image:
    sitting = sitting if sitting is not None else seats("A verdict.")
    png = render(case=case, seats=sitting, finding=tally(sitting), heard_by="Scripted",
                 portraits=lambda duck: None)  # fmt: skip
    return Image.open(BytesIO(png))


def test_the_card_is_a_png_as_wide_as_every_platform_takes() -> None:
    image = card()
    assert image.format == "PNG"
    assert image.width == WIDTH


def test_the_card_grows_so_no_verdict_is_ever_cut() -> None:
    short = card(sitting=seats("Fine."))
    long = card(sitting=seats("A much longer verdict that goes on. " * 12))
    more = card(sitting=seats("Fine.", count=5))
    assert long.height > short.height
    assert more.height > short.height


def test_an_empty_chair_and_an_empty_council_still_draw() -> None:
    absent = [Seat(duck=DUCKS_BY_ID["rebel"], absence=Absence.REFUSED)]
    assert card(sitting=absent).width == WIDTH


def test_long_words_are_broken_to_fit() -> None:
    lines = wrap("see https://example.com/" + "x" * 300, BODY, 400)
    assert len(lines) > 2
    assert all(BODY.getlength(line) <= 400 for line in lines)


def test_line_breaks_the_writer_made_are_kept() -> None:
    assert wrap("one\ntwo", BODY, 900) == ["one", "two"]


# --- on the hearing page ------------------------------------------------------------


def test_a_finished_hearing_downloads_as_an_image(tmp_path: Path) -> None:
    with app_on(tmp_path / "council.db") as client:
        run_id = hear(client)
        assert (
            f'href="/council/{run_id}/card.png" download' in client.get(f"/council/{run_id}").text
        )
        response = client.get(f"/council/{run_id}/card.png")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        disposition = response.headers["content-disposition"]
        assert disposition == 'attachment; filename="duck-council-001.png"'
        assert Image.open(BytesIO(response.content)).width == WIDTH


def test_it_works_for_an_old_hearing_after_a_restart(tmp_path: Path) -> None:
    db = tmp_path / "council.db"
    with app_on(db) as client:
        run_id = hear(client)
    with app_on(db) as restarted:
        assert restarted.get(f"/council/{run_id}/card.png").status_code == 200


def test_the_finished_actions_arrive_with_the_live_finding(tmp_path: Path) -> None:
    """No reload needed: the finding carries a fresh action row, swapped in out of band."""
    with app_on(tmp_path / "council.db") as client:
        board = client.post("/council", data=CASE, headers=FROM_PAGE).text
        assert "Save as image" not in board and "Hear it again" not in board
        run_id = board.split('sse-connect="/council/', 1)[1].split("/stream", 1)[0]
        finding = dict(read_events(client, run_id))["finding"]
        assert '<div class="after" id="after" hx-swap-oob="true">' in finding
        assert "Save as image" in finding and "Hear it again" in finding


def test_an_unfinished_hearing_has_no_image_yet(tmp_path: Path) -> None:
    slow = scripted()
    slow.scripts["lawyer"] = Script(delay=60)
    with app_on(tmp_path / "council.db", slow) as client:
        run_id = file_case(client)
        assert client.get(f"/council/{run_id}/card.png").status_code == 409


def test_an_unknown_hearing_has_no_image(tmp_path: Path) -> None:
    with app_on(tmp_path / "council.db") as client:
        assert client.get("/council/nope/card.png").status_code == 404
