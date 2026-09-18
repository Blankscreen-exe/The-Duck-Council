"""The clerk: reads a case once, before any duck sees it, and rules how it is heard.

Joke, real decision, or someone in genuine trouble (D20). Asking once, centrally,
is what lets the ducks commit to their characters on a joke instead of each one
nervously hedging on its own. The ruling comes before any duck is asked, never
alongside (D22), so a case in crisis never reaches the council at all.

If the clerk cannot rule (an error, a timeout, a refusal), the case is heard
cautiously: the ducks behave exactly as they did before the clerk existed (D41).
"""

import asyncio
import logging

from app.providers.base import Provider, Refused
from app.schema import Case, Register, Ruling, Tone

log = logging.getLogger(__name__)


async def rule(case: Case, provider: Provider) -> Ruling | None:
    """The clerk's ruling, or None when none could be had. Never raises."""
    try:
        async with asyncio.timeout(provider.timeout):
            return await provider.classify(case)
    except Refused:
        log.info("the clerk declined to rule on a case; hearing it cautiously")
    except Exception:
        log.exception("the clerk could not rule (provider %r); hearing cautiously", provider.name)
    return None


def is_crisis(ruling: Ruling | None) -> bool:
    return ruling is not None and ruling.hear_as is Register.CRISIS


def tone_for(ruling: Ruling | None) -> Tone:
    """How the ducks are told to speak. A crisis is never heard, so it has no tone."""
    if ruling is None:
        return "cautious"
    if ruling.hear_as is Register.CRISIS:
        raise ValueError("a case in crisis is not heard by the council")
    return "play" if ruling.hear_as is Register.PLAY else "weighty"


CRISIS_MESSAGE = (
    "The council won't sit for this one. What you've written sounds like it may be more "
    "than a joke, and it deserves a real person rather than a panel of ducks. If you're "
    "going through something hard, free and confidential support lines for your country "
    "are listed at https://findahelpline.com. If you, someone else or an animal is in "
    "danger right now, contact your local emergency services."
)
"""Plain-text version, for the command line. The page has its own, with a link."""
