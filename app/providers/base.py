"""The one interface every AI provider implements (D10).

The council depends on this Protocol, never on a concrete provider or vendor
SDK. That is what lets the demo, Claude Code, the Anthropic API, every
OpenAI-compatible vendor and the test fakes all plug in without the council
knowing or caring which one it has. Adding a vendor is a new adapter file and
a preset row; nothing above this layer moves.
"""

from dataclasses import dataclass
from typing import Literal, Protocol

from app.schema import Case, Duck, Verdict

Effort = Literal["low", "medium", "high", "xhigh", "max"]
"""How hard a model thinks before answering. Lower is faster and cheaper."""


class Refused(Exception):
    """The provider's own safety layer declined to judge this case.

    Distinct from ordinary failures so the UI can show an empty chair with the
    right explanation rather than a generic error.
    """


class ProviderError(Exception):
    """A failure whose message is fit to show a person: bad key, missing program, and so on."""


@dataclass(frozen=True)
class ConnectionCheck:
    ok: bool
    message: str


class Provider(Protocol):
    name: str
    max_concurrency: int
    """How many ducks may be judged at once. Rate limits and local machines differ."""
    timeout: float
    """Seconds one duck may take. Claude Code needs far longer than an HTTP API."""

    async def judge(self, duck: Duck, case: Case) -> Verdict:
        """Return this duck's verdict, or raise `Refused`. Any other exception is a failure."""
        ...

    async def check_connection(self) -> ConnectionCheck:
        """A deliberately tiny request, so a bad key or missing program fails in seconds."""
        ...
