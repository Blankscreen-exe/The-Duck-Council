"""Chambers in the browser: adding, testing and choosing providers, with fake providers."""

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.keystore import MemoryKeyStore
from app.web.main import create_app
from tests.fakes import FakeBuilder

ORIGIN = "http://127.0.0.1:8000"
HTMX = {"origin": ORIGIN, "hx-request": "true"}
KEY = "sk-ant-api03-very-secret-3f9a"


def make_client(tmp_path: Path, *, claude_installed: bool = False) -> TestClient:
    app = create_app(
        database=tmp_path / "council.db",
        keystore=MemoryKeyStore(),
        build=FakeBuilder(),
        find_program=lambda name: "C:/claude.exe" if claude_installed else None,
    )
    return TestClient(app, base_url=ORIGIN)


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with make_client(tmp_path) as test_client:
        yield test_client


def provider_ids(page: str) -> list[str]:
    """Ids of the entries that can be amended: everything except the demo, in list order."""
    return re.findall(r'href="/providers/(\d+)/edit"', page)


def add(client: TestClient, **form: str) -> str:
    response = client.post("/providers", data=form, headers=HTMX)
    assert response.status_code == 200, response.text
    return response.text


def test_chambers_starts_with_the_demo_as_default(client: TestClient) -> None:
    page = client.get("/providers").text
    assert "Demo (no AI)" in page and "Default" in page
    assert 'href="/providers" aria-current="page"' in page


def test_adding_a_provider_tests_it_and_never_shows_the_key(client: TestClient) -> None:
    section = add(client, preset="anthropic", model="claude-opus-5", api_key=KEY)
    assert "Working. Connected to claude-opus-5" in section
    assert "key …3f9a" in section
    assert KEY not in section and KEY not in client.get("/providers").text


def test_a_failing_provider_is_kept_but_cannot_be_made_default(client: TestClient) -> None:
    section = add(client, preset="anthropic", model="broken", api_key=KEY)
    assert "Failing: Invalid API key." in section
    assert 'disabled title="Pass the test first"' in section


def test_a_rejected_form_keeps_what_was_typed_except_the_key(client: TestClient) -> None:
    response = client.post(
        "/providers",
        data={"preset": "custom", "model": "my-model", "api_key": KEY},  # no base URL
        headers=HTMX,
    )
    assert response.status_code == 422
    assert "base URL" in response.text
    assert 'value="my-model"' in response.text
    assert KEY not in response.text


def test_making_a_provider_default_changes_who_hears_the_next_case(client: TestClient) -> None:
    add(client, preset="anthropic", model="claude-opus-5", api_key=KEY)
    (provider_id,) = provider_ids(client.get("/providers").text)
    client.post(f"/providers/{provider_id}/default", headers=HTMX)

    assert "Sitting today: <b>Anthropic API (Claude)</b>" in client.get("/").text
    board = client.post("/council", data={"situation": "s", "action": "a"}, headers=HTMX).text
    match = re.search(r'sse-connect="/council/([^/"]+)/stream"', board)
    assert match
    run_id = match.group(1)
    with client.stream("GET", f"/council/{run_id}/stream") as stream:
        assert "Judged by claude-opus-5." in "".join(stream.iter_text())


def test_fields_follow_the_chosen_provider(client: TestClient) -> None:
    ollama = client.get("/providers/fields", params={"preset": "ollama"}).text
    assert 'value="http://localhost:11434/v1"' in ollama and "(optional)" in ollama
    claude = client.get("/providers/fields", params={"preset": "claude-code"}).text
    assert 'name="api_key"' not in claude and 'name="effort"' in claude
    assert client.get("/providers/fields", params={"preset": "command"}).status_code == 404


def test_claude_code_is_suggested_only_when_installed(tmp_path: Path) -> None:
    with make_client(tmp_path / "without") as client:
        assert "Found on this computer" not in client.get("/providers").text

    with make_client(tmp_path / "with", claude_installed=True) as client:
        assert "Found on this computer: Claude Code" in client.get("/providers").text
        section = client.post("/providers/claude-code", headers=HTMX).text
        assert "Found on this computer" not in section  # added, so no longer suggested
        assert "Sitting today: <b>Claude Code (installed on this PC)</b>" in client.get("/").text


def test_the_demo_cannot_be_amended(client: TestClient) -> None:
    assert provider_ids(client.get("/providers").text) == []  # it offers no amend link
    # On a fresh database the demo is the first row, so its id is 1.
    assert client.get("/providers/1/edit").status_code == 404


def test_removing_a_provider(client: TestClient) -> None:
    add(client, preset="ollama")
    (provider_id,) = provider_ids(client.get("/providers").text)
    section = client.post(f"/providers/{provider_id}/delete", headers=HTMX).text
    assert provider_ids(section) == []
