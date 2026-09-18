"""The Register in the browser: hearings are entered, read back, struck out (D43)."""

import html
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.keystore import MemoryKeyStore
from app.schema import Register, Ruling
from app.web.main import create_app
from tests.fakes import Script, ScriptedProvider
from tests.test_web import CASE, FROM_PAGE, ORIGIN, clerked_client, file_case, read_events, scripted


def app_on(path: Path, provider: ScriptedProvider | None = None) -> TestClient:
    app = create_app(provider or scripted(), database=path, keystore=MemoryKeyStore(),
                     provider_label="Scripted")  # fmt: skip
    return TestClient(app, base_url=ORIGIN)


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with app_on(tmp_path / "council.db") as test_client:
        yield test_client


def hear(client: TestClient) -> str:
    """File the case and wait for the hearing to finish. Returns its id."""
    run_id = file_case(client)
    read_events(client, run_id)
    return run_id


def test_an_empty_register_says_so(client: TestClient) -> None:
    page = client.get("/register").text
    assert "Nothing entered yet." in page
    assert 'aria-current="page">The Register</a>' in page


def test_a_finished_hearing_is_entered_with_who_heard_it(client: TestClient) -> None:
    run_id = hear(client)
    page = client.get("/register").text
    assert f'href="/council/{run_id}"' in page
    assert html.escape(CASE["situation"]) in page
    assert ">001</td>" in page
    assert ">Scripted</td>" in page  # which AI heard it (owner's call)


def test_the_hearing_page_names_its_entry_and_who_heard_it(client: TestClient) -> None:
    page = client.get(f"/council/{hear(client)}").text
    assert "Entered as No. 001" in page
    assert "Heard by Scripted" in page


def test_an_old_hearing_still_opens_after_a_restart(tmp_path: Path) -> None:
    db = tmp_path / "council.db"
    with app_on(db) as first:
        run_id = hear(first)
    with app_on(db) as restarted:  # nothing in memory any more
        page = restarted.get(f"/council/{run_id}").text
        assert "The finding of the bench" in page
        assert "Entered as No. 001" in page
        assert "sse-connect" not in page  # read back still, never heard again
        assert restarted.get(f"/council/{run_id}/stream").status_code == 404
        form = restarted.get(f"/council/{run_id}/amend", headers={"hx-request": "true"}).text
        assert f">{CASE['situation']}</textarea>" in form


def test_hear_it_again_files_the_same_case_afresh(client: TestClient) -> None:
    page = client.get(f"/council/{hear(client)}").text
    assert "Hear it again" in page
    assert f'name="situation" value="{html.escape(CASE["situation"])}"' in page
    assert f'name="action" value="{html.escape(CASE["action"])}"' in page

    hear(client)  # what the button posts: the same two fields
    assert ">002</td>" in client.get("/register").text


def test_a_hearing_still_in_progress_offers_no_hear_it_again(client: TestClient) -> None:
    response = client.post("/council", data=CASE, headers=FROM_PAGE)
    assert "Hear it again" not in response.text


def test_a_crisis_is_never_written_down(tmp_path: Path) -> None:
    with clerked_client(tmp_path, Ruling(reason="Sincere.", hear_as=Register.CRISIS)) as client:
        client.post("/council", data=CASE, headers=FROM_PAGE)
        assert "Nothing entered yet." in client.get("/register").text


def test_a_hearing_cut_short_is_kept_and_marked_adjourned(tmp_path: Path) -> None:
    db = tmp_path / "council.db"
    slow = scripted()
    slow.scripts["lawyer"] = Script(delay=60)
    with app_on(db, slow) as client:
        client.post("/council", data=CASE, headers=FROM_PAGE)
    # Leaving the block shut the server down mid-hearing.
    with app_on(db) as restarted:
        assert "adjourned" in restarted.get("/register").text


def test_striking_out_one_hearing(client: TestClient) -> None:
    kept, struck = hear(client), hear(client)
    book = client.post(f"/register/{struck}/delete", headers=FROM_PAGE).text
    assert "<html" not in book  # just the book, for htmx
    assert f"/council/{kept}" in book and f"/council/{struck}" not in book


def test_clearing_the_register(client: TestClient) -> None:
    hear(client)
    hear(client)
    book = client.post("/register/clear", headers=FROM_PAGE).text
    assert "Nothing entered yet." in book
    assert "Nothing entered yet." in client.get("/register").text


def test_without_javascript_changes_come_back_to_the_register(client: TestClient) -> None:
    run_id = hear(client)
    response = client.post(
        f"/register/{run_id}/delete", headers={"origin": ORIGIN}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/register")


def test_the_register_refuses_writes_from_other_sites(client: TestClient) -> None:
    hear(client)
    response = client.post("/register/clear", headers={"origin": "http://evil.example"})
    assert response.status_code == 403
    assert ">001</td>" in client.get("/register").text


def test_a_page_past_the_end_shows_the_last_page(client: TestClient) -> None:
    hear(client)
    page = client.get("/register?page=9").text
    assert ">001</td>" in page


def test_the_finding_names_who_heard_it_as_it_lands(client: TestClient) -> None:
    events = dict(read_events(client, file_case(client)))
    assert '<p class="by">Heard by Scripted</p>' in events["finding"]
