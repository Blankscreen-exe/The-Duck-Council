"""The web app, end to end through FastAPI's test client, with a scripted provider."""

import html
import json
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ducks import BUILTIN_DUCKS, DEFAULT_ROSTER
from app.keystore import MemoryKeyStore
from app.providers import Refused
from app.schema import Register, Ruling
from app.web.main import create_app
from tests.fakes import Script, ScriptedProvider, verdict_scoring

ORIGIN = "http://127.0.0.1:8000"
FROM_PAGE = {"origin": ORIGIN, "hx-request": "true"}
CASE = {
    "situation": "My flatmate eats my labelled leftovers.",
    "action": "Hide a ghost pepper in them.",
}


def scripted() -> ScriptedProvider:
    scripts = {
        duck.id: Script(verdict=verdict_scoring(10 + 6 * index))
        for index, duck in enumerate(BUILTIN_DUCKS)
    }
    scripts["rebel"] = Script(error=Refused())
    return ScriptedProvider(scripts)


@pytest.fixture
def provider() -> ScriptedProvider:
    return scripted()


@pytest.fixture
def client(provider: ScriptedProvider, tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(provider, database=tmp_path / "council.db", keystore=MemoryKeyStore(),
                     provider_label="Scripted")  # fmt: skip
    with TestClient(app, base_url=ORIGIN) as test_client:
        yield test_client


def file_case(client: TestClient, **fields: str) -> str:
    """File a case and return the new hearing's id."""
    response = client.post("/council", data={**CASE, **fields}, headers=FROM_PAGE)
    assert response.status_code == 200, response.text
    marker = 'sse-connect="/council/'
    start = response.text.index(marker) + len(marker)
    return response.text[start : response.text.index("/stream", start)]


def read_events(client: TestClient, run_id: str) -> list[tuple[str, str]]:
    events: list[tuple[str, str]] = []
    name, data = None, []
    with client.stream("GET", f"/council/{run_id}/stream") as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        for line in response.iter_lines():
            if line.startswith("event: "):
                name = line.removeprefix("event: ")
            elif line.startswith("data: "):
                data.append(line.removeprefix("data: "))
            elif line == "" and name is not None:
                events.append((name, "\n".join(data)))
                name, data = None, []
    return events


# --- the filing desk ------------------------------------------------------------------


def test_the_desk_offers_both_fields_and_the_whole_roster(client: TestClient) -> None:
    page = client.get("/").text
    assert 'name="situation"' in page and 'name="action"' in page
    assert f"{len(DEFAULT_ROSTER)} sitting" in page
    assert "Sitting today: <b>Scripted</b>" in page


def test_an_incomplete_filing_comes_back_with_a_reason_and_the_text_kept(
    client: TestClient,
) -> None:
    response = client.post(
        "/council", data={"situation": "  ", "action": "Keep this text"}, headers=FROM_PAGE
    )
    assert response.status_code == 422
    assert "Describe the situation." in response.text
    assert "Keep this text" in response.text


def test_what_people_type_is_escaped(client: TestClient) -> None:
    response = client.post(
        "/council", data={**CASE, "situation": "<script>alert(1)</script>"}, headers=FROM_PAGE
    )
    assert "<script>alert(1)" not in response.text
    assert "&lt;script&gt;alert(1)" in response.text


# --- a live hearing -------------------------------------------------------------------


def test_filing_returns_a_full_size_board_before_any_verdict(client: TestClient) -> None:
    response = client.post("/council", data=CASE, headers=FROM_PAGE)
    assert "<html" not in response.text  # a fragment for htmx, not a page
    assert response.text.count('sse-swap="seat-') == len(DEFAULT_ROSTER)
    for duck_id in DEFAULT_ROSTER:
        assert f'sse-swap="seat-{duck_id}"' in response.text
    assert CASE["situation"] in response.text


def test_the_stream_sends_every_seat_then_the_finding_then_done(client: TestClient) -> None:
    events = read_events(client, file_case(client))
    names = [name for name, _ in events]

    assert sorted(names[:-2]) == sorted(f"seat-{duck_id}" for duck_id in DEFAULT_ROSTER)
    assert names[-2:] == ["finding", "done"]
    seats = dict(events)
    assert "stamped" in seats["seat-doctor"]  # arriving live, so it slams in
    assert "Empty chair" in seats["seat-rebel"]  # refused (D8)
    assert "The finding of the bench" in seats["finding"]


def test_reconnecting_replays_without_hearing_the_case_again(
    client: TestClient, provider: ScriptedProvider
) -> None:
    run_id = file_case(client)
    first = read_events(client, run_id)
    calls = provider.calls
    again = read_events(client, run_id)  # what a browser does after a dropped connection
    assert again == first
    assert provider.calls == calls == len(DEFAULT_ROSTER)


def test_a_finished_hearing_has_its_own_still_page(client: TestClient) -> None:
    run_id = file_case(client)
    read_events(client, run_id)  # let it finish
    page = client.get(f"/council/{run_id}").text
    assert "<html" in page
    assert "sse-connect" not in page and "stamped" not in page  # no replayed slams (D25)
    assert "The finding of the bench" in page


def test_amending_brings_the_case_back_to_the_desk(client: TestClient) -> None:
    run_id = file_case(client)
    form = client.get(f"/council/{run_id}/amend", headers={"hx-request": "true"}).text
    assert f">{CASE['situation']}</textarea>" in form


def test_an_unknown_hearing_is_not_found(client: TestClient) -> None:
    assert client.get("/council/nope").status_code == 404
    assert client.get("/council/nope/stream").status_code == 404


def test_without_javascript_filing_goes_to_the_hearing_page(client: TestClient) -> None:
    response = client.post(
        "/council", data=CASE, headers={"origin": ORIGIN}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/council/")


# --- the local server's defences (D12) --------------------------------------------------


@pytest.mark.parametrize("origin", ["http://evil.example", "http://localhost:3000", None])
def test_posts_from_anywhere_but_this_app_are_refused(
    client: TestClient, origin: str | None
) -> None:
    headers = {"hx-request": "true"} | ({"origin": origin} if origin else {})
    assert client.post("/council", data=CASE, headers=headers).status_code == 403


def test_a_foreign_host_name_is_refused(client: TestClient) -> None:
    # What a DNS-rebinding attack looks like from the server's side.
    assert client.get("/", headers={"host": "evil.example"}).status_code == 400


def test_pages_carry_a_content_security_policy(client: TestClient) -> None:
    policy = client.get("/").headers["content-security-policy"]
    assert "script-src 'self'" in policy
    assert "frame-ancestors 'none'" in policy


def test_the_page_needs_nothing_from_the_internet(client: TestClient) -> None:
    page = client.get("/").text
    assert "https://" not in page and "http://" not in page
    for asset in (
        "/static/vendor/htmx-2.0.10.min.js",
        "/static/css/council.css",
        "/static/sounds/stamp.mp3",
        "/static/fonts/karla-400.woff2",
    ):
        assert client.get(asset).status_code == 200, asset


def test_a_verdict_carries_what_it_needs_to_be_read_in_full(client: TestClient) -> None:
    events = dict(read_events(client, file_case(client)))
    notice = events["seat-doctor"]
    assert ">Pick it up</button>" in notice  # every notice can be picked up (D40)
    assert ">Pick it up</button>" in events["seat-rebel"]  # empty chairs too
    assert 'class="noticed" data-reader-only hidden' in notice  # the duck's reasoning
    assert '<dialog id="reader"' in client.get("/").text


# --- the clerk (D20, D22, D41) ----------------------------------------------------------


def clerked_client(tmp_path: Path, ruling: object) -> TestClient:
    provider = scripted()
    provider.ruling = ruling  # type: ignore[assignment]
    app = create_app(provider, database=tmp_path / "council.db", keystore=MemoryKeyStore(),
                     provider_label="Scripted")  # fmt: skip
    client = TestClient(app, base_url=ORIGIN)
    client.provider = provider  # type: ignore[attr-defined]
    return client


def test_a_crisis_never_reaches_a_single_duck(tmp_path: Path) -> None:
    with clerked_client(tmp_path, Ruling(reason="Sincere.", hear_as=Register.CRISIS)) as client:
        response = client.post("/council", data=CASE, headers=FROM_PAGE)
        assert "The council won't sit for this one" in response.text
        assert "findahelpline.com" in response.text
        assert "sse-connect" not in response.text and "row pending" not in response.text
        assert client.provider.calls == 0  # type: ignore[attr-defined]


def test_a_joke_is_heard_in_full_character(tmp_path: Path) -> None:
    with clerked_client(tmp_path, Ruling(reason="Absurd.", hear_as=Register.PLAY)) as client:
        read_events(client, file_case(client))
        assert set(client.provider.tones) == {"play"}  # type: ignore[attr-defined]


def test_when_the_clerk_fails_the_case_is_heard_cautiously(tmp_path: Path) -> None:
    with clerked_client(tmp_path, RuntimeError("clerk unreachable")) as client:
        read_events(client, file_case(client))
        assert set(client.provider.tones) == {"cautious"}  # type: ignore[attr-defined]


# --- the loading card (D42) ---------------------------------------------------------------


def loader_lines(page: str) -> list[str]:
    match = re.search(r"data-lines='([^']*)'", page)
    assert match, "no loading card"
    lines: list[str] = json.loads(html.unescape(match.group(1)))
    return lines


def test_a_joke_gets_fun_lines_about_the_ducks_actually_sitting(tmp_path: Path) -> None:
    with clerked_client(tmp_path, Ruling(reason="Absurd.", hear_as=Register.PLAY)) as client:
        board = client.post("/council", data=CASE, headers=FROM_PAGE).text
        lines = loader_lines(board)
        assert "Ruffling feathers…" in lines
        assert any("Quack the Ripper" in line for line in lines)  # sitting
        assert not any("Obscura" in line for line in lines)  # not sitting


def test_a_serious_or_unruled_case_gets_gentle_lines(tmp_path: Path) -> None:
    for ruling in (Ruling(reason="Sincere.", hear_as=Register.WEIGHTY), RuntimeError("down")):
        with clerked_client(tmp_path / type(ruling).__name__, ruling) as client:
            lines = loader_lines(client.post("/council", data=CASE, headers=FROM_PAGE).text)
            assert "The council is weighing this carefully…" in lines
            assert not any("Ripper is sharpening" in line for line in lines)


def test_a_finished_hearing_has_no_loading_card(client: TestClient) -> None:
    run_id = file_case(client)
    read_events(client, run_id)
    assert "data-loader" not in client.get(f"/council/{run_id}").text
