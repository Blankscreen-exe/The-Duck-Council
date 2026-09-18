"""Portraits for your own ducks (D44): what is accepted, what is kept, and where."""

import asyncio
import re
from collections.abc import Iterator
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.ducks import BUILTIN_DUCKS
from app.keystore import MemoryKeyStore
from app.portraits import SIZE, PortraitError, PortraitStore
from app.web.main import create_app
from tests.fakes import Script, ScriptedProvider, verdict_scoring
from tests.test_web import FROM_PAGE, file_case, read_events
from tests.test_web_bench import DUCK, ORIGIN, PLAIN, commission


def image(width: int = 800, height: int = 600, fmt: str = "PNG", mode: str = "RGB") -> bytes:
    out = BytesIO()
    Image.new(mode, (width, height), (200, 120, 40) if mode == "RGB" else (0, 0, 0, 0)).save(
        out, fmt
    )
    return out.getvalue()


def phone_photo() -> bytes:
    """A JPEG carrying EXIF, as a phone would write (here: the camera maker)."""
    out = BytesIO()
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"
    Image.new("RGB", (600, 600), "white").save(out, "JPEG", exif=exif)
    return out.getvalue()


# --- the store: only real images, always re-made -------------------------------------


def store_save(tmp_path: Path, data: bytes) -> tuple[PortraitStore, str]:
    store = PortraitStore(tmp_path / "portraits")
    return store, asyncio.run(store.save(data))


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP"])
def test_any_accepted_image_becomes_a_square_jpeg(tmp_path: Path, fmt: str) -> None:
    store, name = store_save(tmp_path, image(900, 400, fmt))
    path = store.path(name)
    assert path is not None
    with Image.open(path) as saved:
        assert saved.format == "JPEG"
        assert saved.size == (SIZE, SIZE)


def test_hidden_metadata_is_not_kept(tmp_path: Path) -> None:
    assert b"PhoneMaker" in phone_photo()
    store, name = store_save(tmp_path, phone_photo())
    path = store.path(name)
    assert path is not None
    assert b"PhoneMaker" not in path.read_bytes()


def test_a_transparent_image_is_laid_on_paper(tmp_path: Path) -> None:
    store, name = store_save(tmp_path, image(400, 400, "PNG", mode="RGBA"))
    path = store.path(name)
    assert path is not None
    with Image.open(path) as saved:
        r, g, b = saved.convert("RGB").getpixel((10, 10))  # type: ignore[misc]
        assert r > 230 and g > 225 and b > 200  # cream, not black


@pytest.mark.parametrize(
    ("data", "says"),
    [
        (b"not an image at all", "not an image"),
        (image(100, 100), "too small"),
        (image(300, 300, "GIF"), "JPEG, PNG or WebP"),
        (b"\x89PNG\r\n\x1a\n" + b"\0" * 5_300_000, "over 5 MB"),
    ],
    ids=["not-an-image", "too-small", "gif", "too-big"],
)
def test_what_cannot_be_a_portrait_is_refused_plainly(
    tmp_path: Path, data: bytes, says: str
) -> None:
    with pytest.raises(PortraitError, match=says):
        store_save(tmp_path, data)
    assert not (tmp_path / "portraits").exists() or not any((tmp_path / "portraits").iterdir())


def test_a_name_the_store_did_not_make_is_never_looked_up(tmp_path: Path) -> None:
    store = PortraitStore(tmp_path / "portraits")
    (tmp_path / "secret.txt").write_text("x")
    for name in ["../secret.txt", "..\\secret.txt", "secret.txt", "a" * 32 + ".png"]:
        assert store.path(name) is None


# --- on the Bench -------------------------------------------------------------------


def app_on(db: Path) -> TestClient:
    provider = ScriptedProvider({d.id: Script(verdict=verdict_scoring(50)) for d in BUILTIN_DUCKS})
    app = create_app(provider, database=db, keystore=MemoryKeyStore(), provider_label="Scripted")
    return TestClient(app, base_url=ORIGIN)


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with app_on(tmp_path / "council.db") as test_client:
        yield test_client


def upload(data: bytes, filename: str = "duck.png") -> dict[str, tuple[str, bytes, str]]:
    return {"portrait": (filename, data, "image/png")}


def commission_with(client: TestClient, data: bytes) -> str:
    response = client.post("/bench/new", data=DUCK, files=upload(data), headers=PLAIN,
                           follow_redirects=False)  # fmt: skip
    assert response.status_code == 303, response.text
    ids: list[str] = re.findall(r'id="duck-(u[0-9a-f]+)"', client.get("/bench").text)
    return ids[-1]


def portrait_of(client: TestClient, duck_id: str) -> str | None:
    card = client.get("/bench").text.split(f'id="duck-{duck_id}"', 1)[1]
    match = re.search(r'src="/portraits/([0-9a-f]{32}\.jpg)"', card[:3000])
    return match.group(1) if match else None


def files_in(tmp_path: Path) -> set[str]:
    folder = tmp_path / "portraits"
    return {p.name for p in folder.iterdir()} if folder.exists() else set()


def test_the_form_offers_an_upload_with_its_guideline(client: TestClient) -> None:
    form = client.get("/bench/new").text
    assert 'enctype="multipart/form-data"' in form
    assert 'type="file" name="portrait" accept="image/jpeg,image/png,image/webp"' in form
    assert "At least 256&times;256 pixels" in form
    assert "On its card" in form and "In the roster" in form


def test_a_duck_commissioned_with_a_portrait_wears_it(client: TestClient, tmp_path: Path) -> None:
    duck_id = commission_with(client, image())
    name = portrait_of(client, duck_id)
    assert name is not None
    assert files_in(tmp_path) == {name}  # beside the database, not in the app
    served = client.get(f"/portraits/{name}")
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/jpeg"


def test_a_duck_without_one_still_wears_a_monogram(client: TestClient) -> None:
    duck_id = commission(client)
    assert portrait_of(client, duck_id) is None


def test_a_bad_image_comes_back_with_a_reason_and_saves_nothing(
    client: TestClient, tmp_path: Path
) -> None:
    response = client.post("/bench/new", data=DUCK, files=upload(image(80, 80)), headers=PLAIN)
    assert response.status_code == 422
    assert "too small" in response.text
    assert DUCK["voice"] in response.text  # the typing is kept
    assert files_in(tmp_path) == set()
    assert "The Landlord" not in client.get("/bench").text


def test_a_field_problem_asks_for_the_image_again(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        "/bench/new", data={**DUCK, "name": ""}, files=upload(image()), headers=PLAIN
    )
    assert response.status_code == 422
    assert "Choose the image again" in response.text
    assert files_in(tmp_path) == set()


def test_amending_replaces_the_portrait_and_lets_the_old_one_go(
    client: TestClient, tmp_path: Path
) -> None:
    duck_id = commission_with(client, image())
    first = portrait_of(client, duck_id)
    client.post(f"/bench/{duck_id}/edit", data=DUCK, files=upload(image(700, 700)), headers=PLAIN)
    second = portrait_of(client, duck_id)
    assert second is not None and second != first
    assert files_in(tmp_path) == {second}


def test_amending_without_a_file_keeps_the_portrait(client: TestClient) -> None:
    duck_id = commission_with(client, image())
    before = portrait_of(client, duck_id)
    client.post(f"/bench/{duck_id}/edit", data={**DUCK, "name": "Renamed"}, headers=PLAIN)
    assert portrait_of(client, duck_id) == before
    assert "Remove the portrait" in client.get(f"/bench/{duck_id}/edit").text


def test_the_portrait_can_be_removed(client: TestClient, tmp_path: Path) -> None:
    duck_id = commission_with(client, image())
    client.post(f"/bench/{duck_id}/edit", data={**DUCK, "remove_portrait": "1"}, headers=PLAIN)
    assert portrait_of(client, duck_id) is None
    assert files_in(tmp_path) == set()


def test_removing_the_duck_removes_its_portrait(client: TestClient, tmp_path: Path) -> None:
    duck_id = commission_with(client, image())
    client.post(f"/bench/{duck_id}/delete", headers=PLAIN)
    assert files_in(tmp_path) == set()


def test_an_old_hearing_keeps_the_portrait_its_duck_wore(
    client: TestClient, tmp_path: Path
) -> None:
    """The Register shows ducks as they were (D43), so their portraits must stay."""
    duck_id = commission_with(client, image())
    name = portrait_of(client, duck_id)
    for builtin in BUILTIN_DUCKS:  # make the new duck the only one sitting
        client.post(f"/bench/{builtin.id}/seat", data={"sitting": "0"}, headers=FROM_PAGE)
    run_id = file_case(client)
    read_events(client, run_id)

    client.post(f"/bench/{duck_id}/seat", data={"sitting": "0"}, headers=FROM_PAGE)
    client.post(f"/bench/{BUILTIN_DUCKS[0].id}/seat", data={"sitting": "1"}, headers=FROM_PAGE)
    client.post(f"/bench/{duck_id}/delete", headers=PLAIN)
    assert files_in(tmp_path) == {name}
    assert f"/portraits/{name}" in client.get(f"/council/{run_id}").text


def test_startup_clears_portraits_nothing_uses(tmp_path: Path) -> None:
    stray = tmp_path / "portraits" / ("0" * 32 + ".jpg")
    stray.parent.mkdir()
    stray.write_bytes(image(300, 300, "JPEG"))
    with app_on(tmp_path / "council.db") as client:
        duck_id = commission_with(client, image())
        kept = portrait_of(client, duck_id)
    with app_on(tmp_path / "council.db"):
        assert files_in(tmp_path) == {kept}


def test_unknown_or_crafted_portrait_names_are_not_found(client: TestClient) -> None:
    for name in ["nope.jpg", "..%2Fcouncil.db", "0" * 32 + ".jpg"]:
        assert client.get(f"/portraits/{name}").status_code == 404
