"""What routes receive rather than build (D13): the provider, the stores, the roster.

Everything here reads from `app.state`, which `create_app` fills. Tests fill it
with a scripted provider and a database in a temporary folder; the real app fills
it with whatever provider it was started with.
"""

from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates

from app.bench import Bench
from app.providers import Provider
from app.schema import Duck
from app.web.runs import RunStore
from app.web.view import TEMPLATE_GLOBALS

templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")
templates.env.globals.update(TEMPLATE_GLOBALS)


def get_provider(request: Request) -> Provider:
    provider: Provider = request.app.state.provider
    return provider


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
RunsDep = Annotated[RunStore, Depends(get_runs)]
BenchDep = Annotated[Bench, Depends(get_bench)]
RosterDep = Annotated[tuple[Duck, ...], Depends(get_roster)]


def page_context(request: Request) -> dict[str, Any]:
    """What every full page needs for its footer."""
    return {
        "provider_label": request.app.state.provider_label,
        "demo": request.app.state.provider.name == "demo",
    }


def is_htmx(request: Request) -> bool:
    return request.headers.get("hx-request") == "true"
