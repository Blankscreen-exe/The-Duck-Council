"""The web app, end to end through FastAPI's test client, with a scripted provider."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.ducks import BUILTIN_DUCKS
from app.providers import Refused
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
    scripts["witch"] = Script(error=Refused())
    return ScriptedProvider(scripts)


@pytest.fixture
def provider() -> ScriptedProvider:
    return scripted()


@pytest.fixture
def client(provider: ScriptedProvider) -> Iterator[TestClient]:
    app = create_app(provider, provider_label="Scripted")
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
    assert f"{len(BUILTIN_DUCKS)} sitting" in page
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
    for duck in BUILTIN_DUCKS:
        assert f'sse-swap="seat-{duck.id}"' in response.text
    assert CASE["situation"] in response.text


def test_the_stream_sends_every_seat_then_the_finding_then_done(client: TestClient) -> None:
    events = read_events(client, file_case(client))
    names = [name for name, _ in events]

    assert sorted(names[:-2]) == sorted(f"seat-{duck.id}" for duck in BUILTIN_DUCKS)
    assert names[-2:] == ["finding", "done"]
    seats = dict(events)
    assert "stamped" in seats["seat-king"]  # arriving live, so it slams in
    assert "Empty chair" in seats["seat-witch"]  # refused (D8)
    assert "The finding of the bench" in seats["finding"]


def test_reconnecting_replays_without_hearing_the_case_again(
    client: TestClient, provider: ScriptedProvider
) -> None:
    run_id = file_case(client)
    first = read_events(client, run_id)
    calls = provider.calls
    again = read_events(client, run_id)  # what a browser does after a dropped connection
    assert again == first
    assert provider.calls == calls == len(BUILTIN_DUCKS)


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
