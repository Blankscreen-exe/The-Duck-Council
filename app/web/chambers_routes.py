"""Chambers (/providers): set up AI providers, test them, choose the default (D38).

Adding or amending a provider tests it straight away, so its status is always
current. A provider that fails is still saved, marked failing, and cannot become
the default until it passes (owner's call).

API keys only ever travel from the browser to the server. They are never put back
into a page, not even into a form that is being redisplayed with an error: the
person types the key again instead (D12).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.chambers import ADDABLE, ADDABLE_BY_ID, EFFORTS, TAKES_EFFORT, Chambers, ChambersError
from app.web.deps import ChambersDep, is_htmx, page_context, templates

router = APIRouter(prefix="/providers")

CLAUDE_CODE = "claude-code"


async def _context(request: Request, chambers: Chambers, **extra: Any) -> dict[str, Any]:
    found = request.app.state.find_program("claude") is not None
    return {
        **page_context(request),
        "providers": await chambers.all(),
        "addable": ADDABLE,
        "efforts": EFFORTS,
        "takes_effort": TAKES_EFFORT,
        "can_keep_keys": chambers.can_keep_keys,
        "suggest_claude": found and not await chambers.has_preset(CLAUDE_CODE),
        "preset": ADDABLE_BY_ID[CLAUDE_CODE],
        "values": {},
        "editing": None,
        "error": None,
        **extra,
    }


async def _section(
    request: Request, chambers: Chambers, *, status_code: int = 200, **extra: Any
) -> Response:
    if not is_htmx(request):
        return RedirectResponse("/providers", status_code=303)
    context = await _context(request, chambers, **extra)
    return templates.TemplateResponse(
        request, "_chambers_section.html", context, status_code=status_code
    )


@router.get("", response_class=HTMLResponse)
async def chambers_page(request: Request, chambers: ChambersDep) -> HTMLResponse:
    context = await _context(request, chambers)
    return templates.TemplateResponse(request, "chambers.html", context)


@router.get("/fields", response_class=HTMLResponse)
async def fields(request: Request, chambers: ChambersDep, preset: str) -> HTMLResponse:
    """The add form's fields for one kind of provider, swapped in when the choice changes."""
    chosen = ADDABLE_BY_ID.get(preset)
    if chosen is None:
        raise HTTPException(status_code=404, detail="No such provider.")
    context = await _context(request, chambers, preset=chosen)
    return templates.TemplateResponse(request, "_provider_fields.html", context)


@router.post("")
async def add(
    request: Request,
    chambers: ChambersDep,
    preset: Annotated[str, Form()],
    label: Annotated[str, Form()] = "",
    model: Annotated[str, Form()] = "",
    base_url: Annotated[str, Form()] = "",
    api_key: Annotated[str, Form()] = "",
    effort: Annotated[str, Form()] = "low",
) -> Response:
    try:
        saved = await chambers.add(
            preset, label=label, model=model, base_url=base_url, api_key=api_key, effort=effort
        )
    except ChambersError as error:
        # The typed values come back so nothing is lost, except the key (D12).
        values = {"label": label, "model": model, "base_url": base_url, "effort": effort}
        chosen = ADDABLE_BY_ID.get(preset, ADDABLE_BY_ID[CLAUDE_CODE])
        return await _section(
            request, chambers, status_code=422, error=str(error), preset=chosen, values=values
        )
    await chambers.check(saved.id)
    return await _section(request, chambers)


@router.post("/claude-code")
async def use_claude_code(request: Request, chambers: ChambersDep) -> Response:
    """The first-run suggestion: add Claude Code, test it, and make it the default if it works."""
    saved = await chambers.add(CLAUDE_CODE)
    checked = await chambers.check(saved.id)
    if checked.usable:
        await chambers.make_default(saved.id)
    return await _section(request, chambers)


@router.post("/{provider_id}/check")
async def check(request: Request, chambers: ChambersDep, provider_id: int) -> Response:
    try:
        await chambers.check(provider_id)
    except ChambersError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    return await _section(request, chambers)


@router.post("/{provider_id}/default")
async def make_default(request: Request, chambers: ChambersDep, provider_id: int) -> Response:
    try:
        await chambers.make_default(provider_id)
    except ChambersError as error:
        return await _section(request, chambers, status_code=422, error=str(error))
    return await _section(request, chambers)


@router.post("/{provider_id}/delete")
async def remove(request: Request, chambers: ChambersDep, provider_id: int) -> Response:
    try:
        await chambers.remove(provider_id)
    except ChambersError as error:
        return await _section(request, chambers, status_code=422, error=str(error))
    return await _section(request, chambers)


@router.get("/{provider_id}/edit", response_class=HTMLResponse)
async def edit(request: Request, chambers: ChambersDep, provider_id: int) -> HTMLResponse:
    saved = await chambers.get(provider_id)
    if saved is None or saved.is_demo:
        raise HTTPException(status_code=404, detail="That provider cannot be amended.")
    values = {"label": saved.label, "model": saved.model, "base_url": saved.base_url or "",
              "effort": saved.effort or "low"}  # fmt: skip
    context = await _context(request, chambers, preset=saved.preset, values=values, editing=saved)
    return templates.TemplateResponse(request, "provider_form.html", context)


@router.post("/{provider_id}/edit")
async def amend(
    request: Request,
    chambers: ChambersDep,
    provider_id: int,
    label: Annotated[str, Form()] = "",
    model: Annotated[str, Form()] = "",
    base_url: Annotated[str, Form()] = "",
    api_key: Annotated[str, Form()] = "",
    effort: Annotated[str, Form()] = "low",
) -> Response:
    saved = await chambers.get(provider_id)
    if saved is None or saved.is_demo:
        raise HTTPException(status_code=404, detail="That provider cannot be amended.")
    try:
        await chambers.amend(
            provider_id, label=label, model=model, base_url=base_url, api_key=api_key, effort=effort
        )
    except ChambersError as error:
        values = {"label": label, "model": model, "base_url": base_url, "effort": effort}
        context = await _context(
            request, chambers, preset=saved.preset, values=values, editing=saved, error=str(error)
        )
        return templates.TemplateResponse(request, "provider_form.html", context, status_code=422)
    await chambers.check(provider_id)
    return RedirectResponse("/providers", status_code=303)
