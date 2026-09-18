"""The Bench page, end to end: seating ducks, presets, commissioning your own."""

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ducks import BUILTIN_DUCKS, DEFAULT_PRESET, DEFAULT_ROSTER
from app.web.main import create_app
from tests.fakes import Script, ScriptedProvider, verdict_scoring

ORIGIN = "http://127.0.0.1:8000"
HTMX = {"origin": ORIGIN, "hx-request": "true"}
PLAIN = {"origin": ORIGIN}  # a normal form post, as with JavaScript switched off
DUCK = {
    "name": "The Landlord",
    "epithet": "Weighs the deposit · blind to friendship",
    "voice": "Terse, and always mentions the tenancy agreement.",
    "weighs": "Property, liability and the deposit.",
    "blind_spot": "Friendship.",
}


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    provider = ScriptedProvider({d.id: Script(verdict=verdict_scoring(50)) for d in BUILTIN_DUCKS})
    app = create_app(provider, database=tmp_path / "council.db", provider_label="Scripted")
    with TestClient(app, base_url=ORIGIN) as test_client:
        yield test_client


def seat(client: TestClient, duck_id: str, sitting: bool) -> None:
    client.post(f"/bench/{duck_id}/seat", data={"sitting": "1" if sitting else "0"}, headers=HTMX)


def sitting_count(client: TestClient) -> int:
    match = re.search(r"<b>(\d+)</b> of \d+ sitting", client.get("/bench").text)
    assert match
    return int(match.group(1))


def commission(client: TestClient, **fields: str) -> str:
    """Commission a duck and return its id."""
    response = client.post("/bench/new", data={**DUCK, **fields}, headers=PLAIN,
                           follow_redirects=False)  # fmt: skip
    assert response.status_code == 303
    ids: list[str] = re.findall(r'id="duck-(u[0-9a-f]+)"', client.get("/bench").text)
    return ids[-1]


def test_the_bench_shows_every_duck_the_default_preset_and_a_blank_notice(
    client: TestClient,
) -> None:
    page = client.get("/bench").text
    for duck in BUILTIN_DUCKS:
        assert f'id="duck-{duck.id}"' in page
    assert DEFAULT_PRESET in page and 'aria-current="true"' in page
    assert "Commission a duck" in page
    assert sitting_count(client) == len(DEFAULT_ROSTER)


def test_standing_a_duck_down_updates_its_notice_the_count_and_the_presets(
    client: TestClient,
) -> None:
    response = client.post("/bench/doctor/seat", data={"sitting": "0"}, headers=HTMX)
    assert response.status_code == 200
    assert 'class="row profile stood"' in response.text
    assert 'id="bench-count" class="count" hx-swap-oob="true"' in response.text
    assert f"<b>{len(DEFAULT_ROSTER) - 1}</b>" in response.text
    # The default line-up is no longer exactly who is sitting, so its tab is not current.
    assert 'aria-current="true"' not in response.text
    assert sitting_count(client) == len(DEFAULT_ROSTER) - 1


def test_the_last_duck_cannot_be_stood_down(client: TestClient) -> None:
    for duck in BUILTIN_DUCKS[1:]:
        client.post(f"/bench/{duck.id}/seat", data={"sitting": "0"}, headers=HTMX)
    response = client.post(f"/bench/{BUILTIN_DUCKS[0].id}/seat", data={"sitting": "0"},
                           headers=HTMX)  # fmt: skip
    assert response.status_code == 422
    assert "at least one duck sitting" in response.text


def test_the_filing_desk_convenes_only_the_sitting_ducks(client: TestClient) -> None:
    for duck in BUILTIN_DUCKS[2:]:
        client.post(f"/bench/{duck.id}/seat", data={"sitting": "0"}, headers=HTMX)
    assert "2 sitting" in client.get("/").text
    board = client.post("/council", data={"situation": "s", "action": "a"}, headers=HTMX).text
    assert board.count('sse-swap="seat-') == 2


def test_presets_save_apply_and_delete(client: TestClient) -> None:
    # A line-up of three: the lawyer, plus the witch and the king.
    for duck_id in DEFAULT_ROSTER:
        if duck_id != "lawyer":
            seat(client, duck_id, sitting=False)
    seat(client, "witch", sitting=True)
    seat(client, "king", sitting=True)
    saved = client.post("/bench/presets", data={"name": "Three Judges"}, headers=HTMX)
    assert saved.status_code == 200 and "Three Judges" in saved.text

    pattern = r'/bench/presets/(\d+)/apply"[^>]*>\s*<button[^>]*>\s*([^<]+?) <small>'
    by_name = {name: pid for pid, name in re.findall(pattern, client.get("/bench").text)}

    client.post(f"/bench/presets/{by_name[DEFAULT_PRESET]}/apply", headers=HTMX)
    assert sitting_count(client) == len(DEFAULT_ROSTER)
    client.post(f"/bench/presets/{by_name['Three Judges']}/apply", headers=HTMX)
    assert sitting_count(client) == 3

    client.post(f"/bench/presets/{by_name['Three Judges']}/delete", headers=HTMX)
    assert "Three Judges" not in client.get("/bench").text


def test_a_duplicate_preset_name_is_explained(client: TestClient) -> None:
    response = client.post("/bench/presets", data={"name": DEFAULT_PRESET.lower()}, headers=HTMX)
    assert response.status_code == 422
    assert "already a preset" in response.text


def test_a_commissioned_duck_joins_the_bench_and_can_be_amended_and_removed(
    client: TestClient,
) -> None:
    duck_id = commission(client)
    page = client.get("/bench").text
    assert "The Landlord" in page and "Yours" in page

    form = client.get(f"/bench/{duck_id}/edit").text
    assert 'value="The Landlord"' in form
    client.post(f"/bench/{duck_id}/edit", data={**DUCK, "name": "The Landlady"}, headers=PLAIN)
    assert "The Landlady" in client.get("/bench").text

    client.post(f"/bench/{duck_id}/delete", headers=PLAIN)
    assert f'id="duck-{duck_id}"' not in client.get("/bench").text


def test_an_incomplete_duck_comes_back_with_reasons(client: TestClient) -> None:
    response = client.post("/bench/new", data={**DUCK, "weighs": "", "name": "x" * 41},
                           headers=PLAIN)  # fmt: skip
    assert response.status_code == 422
    assert "Say what moves its score." in response.text
    assert "Keep it to 40 characters." in response.text
    assert "Terse, and always mentions" in response.text  # what was typed is kept


def test_builtin_ducks_have_no_amend_form(client: TestClient) -> None:
    assert client.get("/bench/king/edit").status_code == 404
    response = client.post("/bench/king/edit", data=DUCK, headers=PLAIN)
    assert response.status_code == 404


def test_a_commissioned_duck_sits_on_the_next_hearing(client: TestClient) -> None:
    duck_id = commission(client)
    board = client.post("/council", data={"situation": "s", "action": "a"}, headers=HTMX).text
    assert f'sse-swap="seat-{duck_id}"' in board
    assert "TL" in board  # its monogram, since it has no portrait
