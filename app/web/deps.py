"""What routes receive rather than build (D13): the provider, the stores, the roster.

Everything here reads from `app.state`, which `create_app` fills. The provider is
normally the default chosen in Chambers; tests may pin a scripted one instead.
"""

from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates

from app.bench import Bench
from app.chambers import Chambers
from app.providers import Provider
from app.schema import Duck
from app.web.runs import RunStore
from app.web.view import TEMPLATE_GLOBALS

templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")
templates.env.globals.update(TEMPLATE_GLOBALS)


def get_chambers(request: Request) -> Chambers:
    chambers: Chambers = request.app.state.chambers
    return chambers


def get_provider(request: Request) -> Provider:
    """The provider hearings use: Chambers' default, unless a test has pinned one."""
    pinned: Provider | None = request.app.state.provider_override
    return pinned or get_chambers(request).provider


def get_runs(request: Request) -> RunStore:
    runs: RunStore = request.app.state.runs
    return runs


def get_bench(request: Request) -> Bench:
    bench: Bench = request.app.state.bench
    return bench


async def get_roster(bench: Annotated[Bench, Depends(get_bench)]) -> tuple[Duck, ...]:
    """The ducks sitting today, as chosen on the Bench."""
    return await bench.roster()


ProviderDep = Annotated[Provider, Depends(get_provider)]
ChambersDep = Annotated[Chambers, Depends(get_chambers)]
RunsDep = Annotated[RunStore, Depends(get_runs)]
BenchDep = Annotated[Bench, Depends(get_bench)]
RosterDep = Annotated[tuple[Duck, ...], Depends(get_roster)]


def page_context(request: Request) -> dict[str, Any]:
    """What every full page needs for its footer."""
    pinned_label: str | None = request.app.state.provider_label_override
    return {
        "provider_label": pinned_label or get_chambers(request).current.label,
        "demo": get_provider(request).name == "demo",
    }


def is_htmx(request: Request) -> bool:
    return request.headers.get("hx-request") == "true"
