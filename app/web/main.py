"""Build the web app, and run it.

    uv run duck-council-web                          demo, no AI needed
    uv run duck-council-web --provider claude-code   Claude Code on this PC

API keys come from the DUCK_COUNCIL_API_KEY environment variable, as in the CLI.
"""

import argparse
import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.providers import PRESETS_BY_ID, DemoProvider, Provider, ProviderConfig, build_provider
from app.providers.factory import API_KEY_ENV
from app.web.routes import router
from app.web.runs import InMemoryRunStore, RunStore
from app.web.security import LOCAL_HOSTS, SameOriginMiddleware, SecurityHeadersMiddleware

STATIC = Path(__file__).parent.parent / "static"


def create_app(
    provider: Provider | None = None,
    *,
    provider_label: str | None = None,
    runs: RunStore | None = None,
) -> FastAPI:
    """Everything the app depends on is passed in here, which is what makes it testable."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        # Stop hearings still running when the server stops, and let them record that.
        hearings: set[asyncio.Task[None]] = app.state.hearings
        for task in hearings:
            task.cancel()
        await asyncio.gather(*hearings, return_exceptions=True)

    # No interactive API docs: this app serves pages, not a public API.
    app = FastAPI(
        title="The Duck Council",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.provider = provider or DemoProvider()
    app.state.provider_label = provider_label or PRESETS_BY_ID["demo"].label
    app.state.runs = runs or InMemoryRunStore()
    app.state.hearings = set()

    # Added innermost first: requests pass the host check, then the origin check.
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(SameOriginMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=LOCAL_HOSTS)

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    app.include_router(router)
    return app


def serve(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="duck-council-web", description=__doc__.splitlines()[0])
    parser.add_argument("--provider", default="demo", choices=list(PRESETS_BY_ID))
    parser.add_argument("--model", help="model id, overriding the provider's default")
    parser.add_argument("--base-url", help="endpoint, for OpenAI-compatible providers")
    parser.add_argument(
        "--effort", default="low", choices=["low", "medium", "high", "xhigh", "max"]
    )
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    config = ProviderConfig.from_preset(
        args.provider,
        model=args.model,
        base_url=args.base_url,
        api_key=os.environ.get(API_KEY_ENV),
        effort=args.effort,
    )
    try:
        provider = build_provider(config)
    except ValueError as error:
        parser.error(str(error))

    app = create_app(provider, provider_label=PRESETS_BY_ID[args.provider].label)
    print(f"The Duck Council is sitting at http://127.0.0.1:{args.port}")
    # 127.0.0.1 only, never 0.0.0.0: this server holds provider access (D12).
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    serve()
