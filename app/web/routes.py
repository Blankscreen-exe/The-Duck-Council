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
from app.web.deps import ProviderDep, RosterDep, RunsDep, is_htmx, page_context, templates
from app.web.runs import Run, RunStore, hold_hearing, new_run_id
from app.web.view import sse_event

router = APIRouter()


def _run_or_404(runs: RunStore, run_id: str) -> Run:
    run = runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="No such hearing.")
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

    run = Run(id=new_run_id(), case=case, roster=roster, tone=tone_for(ruling), ruling=ruling)
    runs.add(run)
    # asyncio keeps only a weak reference to tasks: without this set, a hearing
    # could be garbage-collected halfway through.
    hearings: set[asyncio.Task[None]] = request.app.state.hearings
    task = asyncio.create_task(hold_hearing(run, provider))
    hearings.add(task)
    task.add_done_callback(hearings.discard)

    if not is_htmx(request):
        # Without JavaScript the form posts normally; send the browser to the hearing page.
        return RedirectResponse(f"/council/{run.id}", status_code=303)
    context = _hearing_context(run, live=True)
    return templates.TemplateResponse(request, "_hearing.html", context)


@router.get("/council/{run_id}", response_class=HTMLResponse)
async def hearing_page(request: Request, runs: RunsDep, run_id: str) -> HTMLResponse:
    """A hearing on its own page. Finished hearings render still: no stamps, no sound (D25)."""
    run = _run_or_404(runs, run_id)
    context = {**page_context(request), **_hearing_context(run, live=not run.done)}
    return templates.TemplateResponse(request, "council.html", context)


@router.get("/council/{run_id}/amend", response_class=HTMLResponse)
async def amend(request: Request, runs: RunsDep, roster: RosterDep, run_id: str) -> HTMLResponse:
    run = _run_or_404(runs, run_id)
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
                yield sse_event("finding", finding.render(run=run, live=True))
                yield sse_event("done", "")
                return

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )
