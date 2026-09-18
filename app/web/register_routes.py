"""The Register (/register): every hearing held, newest first (D21, D43).

Striking out one hearing or clearing the book answers htmx with the book
re-rendered; without JavaScript the forms post normally and come back here.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.register import PAGE_SIZE, Register
from app.web.deps import RegisterDep, is_htmx, page_context, templates

router = APIRouter(prefix="/register")


async def _book(register: Register, page: int) -> dict[str, Any]:
    entries, total = await register.page(page)
    pages = max(1, -(-total // PAGE_SIZE))
    if page > pages:  # the last entry on a later page was just struck out
        page = pages
        entries, total = await register.page(page)
    return {"entries": entries, "total": total, "page": page, "pages": pages}


async def _after_change(request: Request, register: Register, page: int) -> Response:
    if not is_htmx(request):
        return RedirectResponse(f"/register?page={page}", status_code=303)
    context = await _book(register, page)
    return templates.TemplateResponse(request, "_register_book.html", context)


@router.get("", response_class=HTMLResponse)
async def register_page(
    request: Request, register: RegisterDep, page: Annotated[int, Query(ge=1)] = 1
) -> HTMLResponse:
    context = {**page_context(request), **await _book(register, page)}
    return templates.TemplateResponse(request, "register.html", context)


@router.post("/clear")
async def clear(request: Request, register: RegisterDep) -> Response:
    await register.clear()
    return await _after_change(request, register, 1)


@router.post("/{hearing_id}/delete")
async def strike_out(
    request: Request,
    register: RegisterDep,
    hearing_id: str,
    page: Annotated[int, Form(ge=1)] = 1,
) -> Response:
    # Already gone (struck out in another tab) is not an error: the book is simply redrawn.
    await register.remove(hearing_id)
    return await _after_change(request, register, page)
