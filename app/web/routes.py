"""The Filing Desk, hearings, and the event stream.

Routes never build their collaborators. The provider, the hearing store and the
roster arrive through FastAPI dependencies (D13), so tests hand in a scripted
provider and the app hands in whichever real one it was started with.
"""

import asyncio
from collections.abc import AsyncIterator
from functools import partial
from typing import Annotated, Any

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from pydantic import ValidationError

from app.clerk import is_crisis, rule, tone_for
from app.schema import Case, Duck
from app.web import share_card
from app.web.deps import (
    PortraitsDep,
    ProviderDep,
    RegisterDep,
    RosterDep,
    RunsDep,
    is_htmx,
    page_context,
    provider_label,
    templates,
)
from app.web.runs import Run, RunStore, hold_hearing, new_run_id, run_from_register
from app.web.view import sse_event

router = APIRouter()


def _run_or_404(runs: RunStore, run_id: str) -> Run:
    """A hearing still in memory: the only kind that can be streamed."""
    run = runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="No such hearing.")
    return run


async def _any_run_or_404(runs: RunStore, register: RegisterDep, run_id: str) -> Run:
    """A hearing in memory, or else one from the Register: links survive a restart."""
    run = runs.get(run_id)
    if run is None:
        stored = await register.get(run_id)
        if stored is None:
            raise HTTPException(status_code=404, detail="No such hearing.")
        run = run_from_register(stored)
    return run


_FIELD_PROMPTS = {
    "situation": "Describe the situation.",
    "action": "Say what you intend to do.",
}


def _explain(error: ValidationError) -> str:
    messages = []
    for problem in error.errors():
        field = str(problem["loc"][0])
        if problem["type"] == "string_too_long":
            messages.append(f"The {field} is too long (2,000 characters at most).")
        else:
            messages.append(_FIELD_PROMPTS.get(field, "Check the filing."))
    return " ".join(messages)


def _desk(
    request: Request,
    roster: tuple[Duck, ...],
    *,
    situation: str = "",
    action: str = "",
    error: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    context = {
        **page_context(request),
        "roster": roster,
        "situation": situation,
        "action": action,
        "error": error,
    }
    name = "_desk.html" if is_htmx(request) else "desk.html"
    return templates.TemplateResponse(request, name, context, status_code=status_code)


def _hearing_context(run: Run, *, live: bool) -> dict[str, Any]:
    return {
        "run": run,
        "live": live,
        "seats": {seat.duck.id: seat for seat in run.seats},
    }


@router.get("/", response_class=HTMLResponse)
async def filing_desk(request: Request, roster: RosterDep) -> HTMLResponse:
    return _desk(request, roster)


@router.post("/council")
async def file_case(
    request: Request,
    provider: ProviderDep,
    runs: RunsDep,
    register: RegisterDep,
    roster: RosterDep,
    situation: Annotated[str, Form()] = "",
    action: Annotated[str, Form()] = "",
) -> Response:
    try:
        case = Case(situation=situation, action=action)
    except ValidationError as error:
        return _desk(
            request,
            roster,
            situation=situation,
            action=action,
            error=_explain(error),
            status_code=422,
        )

    # The clerk rules first, and nothing of the council is rendered until it has (D22):
    # a person in real distress must never see ducks "deliberating" on their words.
    ruling = await rule(case, provider)
    if is_crisis(ruling):
        name = "_crisis.html" if is_htmx(request) else "crisis.html"
        return templates.TemplateResponse(request, name, page_context(request))

    run = Run(
        id=new_run_id(),
        case=case,
        roster=roster,
        tone=tone_for(ruling),
        ruling=ruling,
        heard_by=provider_label(request),
    )
    runs.add(run)
    # asyncio keeps only a weak reference to tasks: without this set, a hearing
    # could be garbage-collected halfway through.
    hearings: set[asyncio.Task[None]] = request.app.state.hearings
    task = asyncio.create_task(hold_hearing(run, provider, register))
    hearings.add(task)
    task.add_done_callback(hearings.discard)

    if not is_htmx(request):
        # Without JavaScript the form posts normally; send the browser to the hearing page.
        return RedirectResponse(f"/council/{run.id}", status_code=303)
    context = _hearing_context(run, live=True)
    return templates.TemplateResponse(request, "_hearing.html", context)


@router.get("/council/{run_id}", response_class=HTMLResponse)
async def hearing_page(
    request: Request, runs: RunsDep, register: RegisterDep, run_id: str
) -> HTMLResponse:
    """A hearing on its own page. Finished hearings render still: no stamps, no sound (D25)."""
    run = await _any_run_or_404(runs, register, run_id)
    context = {**page_context(request), **_hearing_context(run, live=not run.done)}
    return templates.TemplateResponse(request, "council.html", context)


@router.get("/council/{run_id}/card.png")
async def share_image(
    runs: RunsDep, register: RegisterDep, portraits: PortraitsDep, run_id: str
) -> Response:
    """The finished hearing as one image to post anywhere (D45)."""
    run = await _any_run_or_404(runs, register, run_id)
    if not run.done or run.finding is None:
        raise HTTPException(status_code=409, detail="The council is still deliberating.")
    seats = [s for duck in run.roster if (s := run.seat_for(duck.id)) is not None]
    png = await asyncio.to_thread(  # drawing takes a moment; hearings keep streaming meanwhile
        share_card.render,
        case=run.case,
        seats=seats,
        finding=run.finding,
        heard_by=run.heard_by,
        portraits=partial(share_card.portrait_file, uploaded=portraits.path),
    )
    name = f"duck-council-{run.number:03d}.png" if run.number else "duck-council-hearing.png"
    return Response(
        png,
        media_type="image/png",
        headers={"content-disposition": f'attachment; filename="{name}"'},
    )


@router.get("/council/{run_id}/amend", response_class=HTMLResponse)
async def amend(
    request: Request, runs: RunsDep, register: RegisterDep, roster: RosterDep, run_id: str
) -> HTMLResponse:
    run = await _any_run_or_404(runs, register, run_id)
    return _desk(request, roster, situation=run.case.situation, action=run.case.action)


def _news_since(run: Run, already: int) -> bool:
    """True once more than `already` seats have landed, or the hearing is over."""
    return len(run.seats) > already or run.done


@router.get("/council/{run_id}/stream")
async def hearing_stream(runs: RunsDep, run_id: str) -> StreamingResponse:
    """Each verdict as it lands, then the finding, then `done` so the browser stops listening.

    Safe to reconnect: a new connection replays what has landed, it never re-hears.
    """
    run = _run_or_404(runs, run_id)
    notice = templates.get_template("_notice.html")
    finding = templates.get_template("_finding.html")
    after = templates.get_template("_after.html")

    async def events() -> AsyncIterator[str]:
        sent = 0
        while True:
            async with run.changed:
                await run.changed.wait_for(partial(_news_since, run, sent))
                fresh, finished = run.seats[sent:], run.done
            for seat in fresh:
                html = notice.render(duck=seat.duck, seat=seat, live=True)
                yield sse_event(f"seat-{seat.duck.id}", html)
                sent += 1
            if finished and sent == len(run.seats):
                ended = finding.render(run=run, live=True) + after.render(run=run, oob=True)
                yield sse_event("finding", ended)
                yield sse_event("done", "")
                return

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )
