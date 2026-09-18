"""The Bench: who sits, saved presets, and commissioning your own ducks (D14, D23).

Small actions (seating a duck, applying a preset) answer htmx with just the part
of the page that changed. Every form also posts normally, so the page works with
JavaScript switched off: those requests are sent back to /bench instead.
"""

from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import ValidationError

from app.bench import Bench, BenchError, DuckDraft
from app.portraits import ACCEPT_ATTRIBUTE, MAX_BYTES, PortraitError, PortraitStore, let_go
from app.schema import Duck, Origin
from app.web.deps import BenchDep, PortraitsDep, is_htmx, page_context, templates

router = APIRouter(prefix="/bench")

_FIELD_LIMITS = {"name": 40, "epithet": 48, "voice": 600, "weighs": 300, "blind_spot": 300}
_FIELD_EMPTY = {
    "name": "Give the duck a name.",
    "epithet": "Give it a short line for its card.",
    "voice": "Describe how it talks.",
    "weighs": "Say what moves its score.",
    "blind_spot": "Say what it ignores.",
}


async def _board(bench: Bench, **extra: Any) -> dict[str, Any]:
    entries = await bench.entries()
    sitting = frozenset(entry.duck.id for entry in entries if entry.sitting)
    return {
        "entries": entries,
        "presets": await bench.presets(),
        "sitting_ids": sitting,
        "error": None,
        **extra,
    }


def _back_to_bench() -> RedirectResponse:
    return RedirectResponse("/bench", status_code=303)


@router.get("", response_class=HTMLResponse)
async def bench_page(request: Request, bench: BenchDep) -> HTMLResponse:
    context = {**page_context(request), **await _board(bench)}
    return templates.TemplateResponse(request, "bench.html", context)


@router.post("/{duck_id}/seat")
async def seat(
    request: Request, bench: BenchDep, duck_id: str, sitting: Annotated[str, Form()] = "1"
) -> Response:
    error = None
    try:
        await bench.seat(duck_id, sitting == "1")
    except BenchError as problem:
        error = str(problem)
    if not is_htmx(request):
        return _back_to_bench()
    entry = await bench.entry(duck_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="No such duck.")
    # The notice, plus the count and the preset tabs, which change with it.
    context = await _board(bench, entry=entry, notice_error=error)
    return templates.TemplateResponse(
        request, "_seat_changed.html", context, status_code=422 if error else 200
    )


@router.post("/presets")
async def save_preset(
    request: Request, bench: BenchDep, name: Annotated[str, Form()] = ""
) -> Response:
    error = None
    try:
        await bench.save_preset(name)
    except BenchError as problem:
        error = str(problem)
    if not is_htmx(request):
        return _back_to_bench()
    context = await _board(bench, preset_error=error)
    return templates.TemplateResponse(
        request, "_presets.html", context, status_code=422 if error else 200
    )


@router.post("/presets/{preset_id}/apply")
async def apply_preset(request: Request, bench: BenchDep, preset_id: int) -> Response:
    try:
        await bench.apply_preset(preset_id)
    except BenchError as problem:
        raise HTTPException(status_code=404, detail=str(problem)) from None
    if not is_htmx(request):
        return _back_to_bench()
    return templates.TemplateResponse(request, "_bench_board.html", await _board(bench))


@router.post("/presets/{preset_id}/delete")
async def delete_preset(request: Request, bench: BenchDep, preset_id: int) -> Response:
    error = None
    try:
        await bench.delete_preset(preset_id)
    except BenchError as problem:
        error = str(problem)
    if not is_htmx(request):
        return _back_to_bench()
    context = await _board(bench, preset_error=error)
    return templates.TemplateResponse(
        request, "_presets.html", context, status_code=422 if error else 200
    )


# ── commissioning and amending your own ducks ──────────────────────────────────


def _field_errors(error: ValidationError) -> dict[str, str]:
    found: dict[str, str] = {}
    for problem in error.errors():
        field = str(problem["loc"][0])
        if problem["type"] == "string_too_long":
            found[field] = f"Keep it to {_FIELD_LIMITS[field]} characters."
        else:
            found[field] = _FIELD_EMPTY.get(field, "Check this field.")
    return found


def _form(
    request: Request,
    *,
    values: dict[str, str],
    duck_id: str | None = None,
    portrait: str | None = None,
    errors: dict[str, str] | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    context = {
        **page_context(request),
        "values": values,
        "duck_id": duck_id,
        "portrait": portrait,
        "accept": ACCEPT_ATTRIBUTE,
        "max_bytes": MAX_BYTES,
        "errors": errors or {},
    }
    return templates.TemplateResponse(request, "duck_form.html", context, status_code=status_code)


async def _own_duck(bench: Bench, duck_id: str) -> Duck:
    entry = await bench.entry(duck_id)
    if entry is None or entry.duck.origin is not Origin.USER:
        # Built-in ducks are read-only (D14): there is no form for them.
        raise HTTPException(status_code=404, detail="Only ducks you commissioned can be amended.")
    return entry.duck


def _values(duck: Duck) -> dict[str, str]:
    return duck.model_dump(include=set(_FIELD_LIMITS))


async def _upload(portraits: PortraitStore, upload: UploadFile | None) -> str | None:
    """Save a chosen image as a portrait. None when no file was chosen."""
    if upload is None or not upload.filename:
        return None
    data = await upload.read(MAX_BYTES + 1)  # one byte over is enough to know it is too big
    if not data:
        return None
    return await portraits.save(data)


# A browser cannot put a chosen file back into a form, so after an error it must be
# chosen again. The form says so rather than letting it vanish silently.
_CHOOSE_AGAIN = "Choose the image again: a form sent back with a problem cannot keep it."


@router.get("/new", response_class=HTMLResponse)
async def new_duck(request: Request) -> HTMLResponse:
    return _form(request, values={})


@router.post("/new")
async def commission(
    request: Request,
    bench: BenchDep,
    portraits: PortraitsDep,
    name: Annotated[str, Form()] = "",
    epithet: Annotated[str, Form()] = "",
    voice: Annotated[str, Form()] = "",
    weighs: Annotated[str, Form()] = "",
    blind_spot: Annotated[str, Form()] = "",
    portrait: Annotated[UploadFile | None, File()] = None,
) -> Response:
    values = {"name": name, "epithet": epithet, "voice": voice, "weighs": weighs,
              "blind_spot": blind_spot}  # fmt: skip
    chosen = portrait is not None and bool(portrait.filename)
    try:
        draft = DuckDraft(**values)
    except ValidationError as error:
        errors = _field_errors(error)
        if chosen:
            errors["portrait"] = _CHOOSE_AGAIN
        return _form(request, values=values, errors=errors, status_code=422)
    try:
        saved = await _upload(portraits, portrait)
    except PortraitError as problem:
        return _form(request, values=values, errors={"portrait": str(problem)}, status_code=422)
    await bench.add_duck(draft, portrait=saved)
    return _back_to_bench()


@router.get("/{duck_id}/edit", response_class=HTMLResponse)
async def edit_duck(request: Request, bench: BenchDep, duck_id: str) -> HTMLResponse:
    duck = await _own_duck(bench, duck_id)
    return _form(request, values=_values(duck), duck_id=duck_id, portrait=duck.portrait)


@router.post("/{duck_id}/edit")
async def amend(
    request: Request,
    bench: BenchDep,
    portraits: PortraitsDep,
    duck_id: str,
    name: Annotated[str, Form()] = "",
    epithet: Annotated[str, Form()] = "",
    voice: Annotated[str, Form()] = "",
    weighs: Annotated[str, Form()] = "",
    blind_spot: Annotated[str, Form()] = "",
    portrait: Annotated[UploadFile | None, File()] = None,
    remove_portrait: Annotated[str, Form()] = "",
) -> Response:
    duck = await _own_duck(bench, duck_id)
    values = {"name": name, "epithet": epithet, "voice": voice, "weighs": weighs,
              "blind_spot": blind_spot}  # fmt: skip
    chosen = portrait is not None and bool(portrait.filename)

    def again(errors: dict[str, str]) -> HTMLResponse:
        return _form(request, values=values, duck_id=duck_id, portrait=duck.portrait,
                     errors=errors, status_code=422)  # fmt: skip

    try:
        draft = DuckDraft(**values)
    except ValidationError as error:
        errors = _field_errors(error)
        if chosen:
            errors["portrait"] = _CHOOSE_AGAIN
        return again(errors)
    try:
        saved = await _upload(portraits, portrait)
    except PortraitError as problem:
        return again({"portrait": str(problem)})

    await bench.edit_duck(duck_id, draft)
    # A new image wins over the "remove" box if both were given.
    if saved is not None or remove_portrait:
        previous = await bench.set_portrait(duck_id, saved)
        await let_go(portraits, bench.db, previous)
    return _back_to_bench()


@router.post("/{duck_id}/delete")
async def remove(
    request: Request, bench: BenchDep, portraits: PortraitsDep, duck_id: str
) -> Response:
    error = None
    entry = await bench.entry(duck_id)
    try:
        await bench.remove_duck(duck_id)
    except BenchError as problem:
        error = str(problem)
    else:
        if entry is not None:
            await let_go(portraits, bench.db, entry.duck.portrait)
    if not is_htmx(request):
        return _back_to_bench()
    context = await _board(bench, error=error)
    return templates.TemplateResponse(
        request, "_bench_board.html", context, status_code=422 if error else 200
    )
