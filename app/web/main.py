"""Build the web app, and run it.

    uv run duck-council-web

The AI provider is chosen in the browser, in Chambers (/providers). Settings and
the bench are kept in SQLite in the user's data folder (or DUCK_COUNCIL_DATA if
set); API keys are kept in the operating system's credential store.
"""

import argparse
import asyncio
import os
import shutil
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import platformdirs
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.bench import Bench
from app.chambers import Builder, Chambers
from app.keystore import KeyStore, OsKeyStore
from app.providers import Provider, build_provider
from app.register import Register
from app.storage import open_database
from app.web.bench_routes import router as bench_router
from app.web.chambers_routes import router as chambers_router
from app.web.register_routes import router as register_router
from app.web.routes import router
from app.web.runs import InMemoryRunStore, RunStore
from app.web.security import LOCAL_HOSTS, SameOriginMiddleware, SecurityHeadersMiddleware

STATIC = Path(__file__).parent.parent / "static"
DATA_ENV = "DUCK_COUNCIL_DATA"


def default_data_dir() -> Path:
    """Where the bench lives: the user's app-data folder (under %LOCALAPPDATA% on Windows)."""
    override = os.environ.get(DATA_ENV)
    if override:
        return Path(override)
    return platformdirs.user_data_path("duck-council", appauthor=False)


def create_app(
    provider: Provider | None = None,
    *,
    database: Path,
    keystore: KeyStore,
    provider_label: str | None = None,
    runs: RunStore | None = None,
    build: Builder = build_provider,
    find_program: Callable[[str], str | None] = shutil.which,
) -> FastAPI:
    """Everything the app depends on is passed in here, which is what makes it testable.

    `database` and `keystore` have no defaults on purpose: a test that forgot them
    would otherwise write into the owner's real bench or credential store. A test
    may pin `provider`; the real app always uses the default chosen in Chambers.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db = await open_database(database)
        app.state.bench = Bench(db)
        await app.state.bench.sync()
        app.state.chambers = Chambers(db, keystore, build)
        await app.state.chambers.sync()
        app.state.register = Register(db)
        try:
            yield
        finally:
            # Stop hearings still running when the server stops, and let them record that.
            hearings: set[asyncio.Task[None]] = app.state.hearings
            for task in hearings:
                task.cancel()
            await asyncio.gather(*hearings, return_exceptions=True)
            await db.close()

    # No interactive API docs: this app serves pages, not a public API.
    app = FastAPI(
        title="The Duck Council",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.provider_override = provider
    app.state.provider_label_override = provider_label
    app.state.find_program = find_program
    app.state.runs = runs or InMemoryRunStore()
    app.state.hearings = set()

    # Added innermost first: requests pass the host check, then the origin check.
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(SameOriginMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=LOCAL_HOSTS)

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    app.include_router(router)
    app.include_router(bench_router)
    app.include_router(chambers_router)
    app.include_router(register_router)
    return app


def serve(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="duck-council-web", description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=default_data_dir(),
        help="where settings and the bench are kept (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    database = args.data_dir / "council.db"
    app = create_app(database=database, keystore=OsKeyStore())
    print(f"The Duck Council is sitting at http://127.0.0.1:{args.port}")
    print(f"Settings and the bench are kept in {database}")
    # 127.0.0.1 only, never 0.0.0.0: this server holds provider access (D12).
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    serve()
