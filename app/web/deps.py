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
from app.portraits import PortraitStore
from app.providers import Provider
from app.register import Register
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


def get_register(request: Request) -> Register:
    register: Register = request.app.state.register
    return register


def get_portraits(request: Request) -> PortraitStore:
    portraits: PortraitStore = request.app.state.portraits
    return portraits


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
RegisterDep = Annotated[Register, Depends(get_register)]
PortraitsDep = Annotated[PortraitStore, Depends(get_portraits)]
RosterDep = Annotated[tuple[Duck, ...], Depends(get_roster)]


def provider_label(request: Request) -> str:
    """The name of the provider that will hear the next case."""
    pinned_label: str | None = request.app.state.provider_label_override
    return pinned_label or get_chambers(request).current.label


def page_context(request: Request) -> dict[str, Any]:
    """What every full page needs for its footer."""
    return {
        "provider_label": provider_label(request),
        "demo": get_provider(request).name == "demo",
    }


def is_htmx(request: Request) -> bool:
    return request.headers.get("hx-request") == "true"
