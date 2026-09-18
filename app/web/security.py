"""Protections for a local server that the browser can reach from any page (D12).

Binding to 127.0.0.1 keeps other machines out, but not other websites: any page
open in the same browser can send requests to localhost. So:

- the Host header must name this machine, which defeats DNS rebinding
  (Starlette's TrustedHostMiddleware, wired up in `main.py`);
- anything that changes state must come from one of this app's own pages,
  checked by the Origin header below;
- responses carry a Content-Security-Policy, so even if text from a model or a
  user ever slipped past escaping, the browser would refuse to run it.
"""

from urllib.parse import urlsplit

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

LOCAL_HOSTS = ["127.0.0.1", "localhost"]

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

_SECURITY_HEADERS = {
    # Inline style attributes are allowed (the board positions dots with them);
    # inline scripts are not, and nothing loads from anywhere but this server.
    "content-security-policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; media-src 'self'; connect-src 'self'; "
        "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    ),
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
}


class SameOriginMiddleware:
    """Refuse state-changing requests that did not come from this app's own pages."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] not in _SAFE_METHODS:
            headers = Headers(scope=scope)
            if not _same_origin(headers.get("origin"), headers.get("host")):
                response = PlainTextResponse(
                    "Refused: this request did not come from the app.", 403
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def _same_origin(origin: str | None, host: str | None) -> bool:
    # Browsers always send Origin on POST. A missing one means a non-browser client,
    # which has no business changing this app's state through its pages.
    if not origin or not host:
        return False
    parsed = urlsplit(origin)
    return parsed.scheme == "http" and parsed.netloc == host


class SecurityHeadersMiddleware:
    """Add the headers above to every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in _SECURITY_HEADERS.items():
                    headers.setdefault(name, value)
            await send(message)

        await self.app(scope, receive, with_headers)
