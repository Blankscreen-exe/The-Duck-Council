"""A provider that needs no API key, so the app runs out of the box (D17).

Verdicts are deterministic: the same duck and case always produce the same
answer, so a reviewer who reloads sees a stable council rather than dice.
Each duck also leans in its own direction, so the demo shows a believable
split instead of uniform noise.

Nothing here reads the case's content. Demo lines are written to fit any
situation, and every verdict says plainly that no model was consulted.
"""

import asyncio
import hashlib
from typing import Literal

from app.providers.base import ConnectionCheck
from app.schema import NUDGE_LIMIT, Band, Case, Duck, Verdict

Stance = Literal["against", "middling", "for"]

_BANDS = tuple(Band)

# How far each duck tilts from neutral, in fifths of the scale.
# The doctor is cautious by nature; the serial killer duck is not.
_LEAN: dict[str, int] = {
    "doctor": -2,
    "lawyer": -1,
    "detective": -1,
    "gamer": 1,
    "rich": 1,
    "rebel": 1,
    "serial_killer": 2,
}

_LINES: dict[str, dict[Stance, str]] = {
    "lawyer": {
        "against": "I would not defend this, and I would not want to explain it to a judge.",
        "middling": "Arguable either way. Keep receipts, and write nothing you would not read "
        "aloud in court.",
        "for": "Procedurally sound. I find no liability worth billing for, which frankly "
        "disappoints me.",
    },
    "doctor": {
        "against": "Absolutely not. I can already see the waiting room, and you are in it.",
        "middling": "Survivable, probably. Drink some water first, and do not do it tired.",
        "for": "Clinically speaking, this is good for you. I rarely get to say that. Enjoy it.",
    },
    "witch": {
        "against": "The moon turns her face from this. What you send out will knock on your "
        "door at night.",
        "middling": "The cards fall sideways. Walk it slowly and watch which birds follow you.",
        "for": "The threshold is open and the candle leans your way. Step through.",
    },
    "serial_killer": {
        "against": "Oh, that's a bit tame, isn't it? Sweet, though! You could be SO much more "
        "decisive.",
        "middling": "Hmm! A little timid, but every great story starts somewhere quiet.",
        "for": "Ooh, I love this! So bold. So final. You'll be fine. Probably! Hee.",
    },
    "gangsta": {
        "against": "Nah. That ain't how we move. You handle it face to face or you don't "
        "handle it.",
        "middling": "I hear you. Could go either way. Just make sure they know it was you.",
        "for": "That's respect. Keep your word, hold your ground. I'd ride with that.",
    },
    "gamer": {
        "against": "Throwing. That play has no payoff and hands them the round.",
        "middling": "Mid strat. Not griefing, not carrying. You'll probably trade even.",
        "for": "Huge play. Low effort, high payoff, zero counterplay. GG.",
    },
    "rich": {
        "against": "Where's the upside? I see everything as a return, and I don't see one here.",
        "middling": "Modest position. Not how fortunes are made, but not how they're lost either.",
        "for": "Love it. Fortune favours the feathered. Go big and invoice the universe.",
    },
    "diplomat": {
        "against": "I fear this closes more doors than it opens. Perhaps a conversation first?",
        "middling": "There is a path here, if everyone can save face. Tread gently and offer "
        "a gesture.",
        "for": "An elegant solution. Everyone leaves with their dignity intact. Well negotiated.",
    },
    "techno": {
        "against": "Error. This introduces more bugs than it patches. Rollback recommended.",
        "middling": "Acceptable latency. Suboptimal, but it will compile.",
        "for": "Efficient. Root cause patched, zero wasted cycles. Deploy.",
    },
    "king": {
        "against": "This is beneath you, and beneath the realm. The sages would not approve.",
        "middling": "There is honour on both sides of this. Weigh it once more, then act "
        "without regret.",
        "for": "Nobly done. The realm is fairer for it. Proceed with our blessing.",
    },
    "spiritual_medium": {
        "against": "Mala omina. The voices are unanimous, and they are screaming. Do not.",
        "middling": "The spirits are divided. One says yes. One wants to talk about 1843.",
        "for": "Fiat! The ancestors nod. Even the demon approves, and he approves of nothing.",
    },
    "detective": {
        "against": "The evidence does not support it. You have assumed three things you have "
        "not checked.",
        "middling": "Plausible, but unproven. Gather one more fact before you commit.",
        "for": "The facts line up. Probability of success: high. Elementary, really.",
    },
    "rebel": {
        "against": "That's not freedom, that's giving up quietly. You deserve better than this.",
        "middling": "Could be brave, could be reckless. Do it only if it's really you.",
        "for": "YES. Stop asking permission. Do it loud and don't apologise.",
    },
}

# User-created ducks (D14) have no scripted lines, so they share these.
_GENERIC: dict[Stance, str] = {
    "against": "No. By everything I care about, this is a mistake.",
    "middling": "It could go either way. I would think it over once more.",
    "for": "Yes. By everything I care about, this is the right call.",
}

DEMO_READ = "Demo mode: no model was consulted."


def _digest(duck: Duck, case: Case) -> bytes:
    # sha256 rather than Python's hash(): hash() is salted per process for strings,
    # so it would give a different council after every restart.
    key = "\x1f".join((duck.id, case.situation, case.action))
    return hashlib.sha256(key.encode("utf-8")).digest()


def _stance(band: Band) -> Stance:
    if band in (Band.RECKLESS, Band.UNWISE):
        return "against"
    if band is Band.DEFENSIBLE:
        return "middling"
    return "for"


class DemoProvider:
    name = "demo"

    def __init__(
        self,
        *,
        latency: tuple[float, float] = (0.2, 1.6),
        max_concurrency: int = 64,
    ) -> None:
        low, high = latency
        if not 0 <= low <= high:
            raise ValueError("latency must be (low, high) with 0 <= low <= high")
        self._latency = latency
        self.max_concurrency = max_concurrency
        self.timeout = 30.0

    async def judge(self, duck: Duck, case: Case) -> Verdict:
        digest = _digest(duck, case)

        # Simulated thinking time, so streaming behaves as it will with a real model.
        low, high = self._latency
        await asyncio.sleep(low + (high - low) * digest[4] / 255)

        position = int.from_bytes(digest[:2], "big") / 0xFFFF  # 0.0 to 1.0
        position += _LEAN.get(duck.id, 0) / len(_BANDS)
        index = min(len(_BANDS) - 1, max(0, int(position * len(_BANDS))))
        band = _BANDS[index]

        nudge = digest[2] % (2 * NUDGE_LIMIT + 1) - NUDGE_LIMIT
        line = _LINES.get(duck.id, _GENERIC)[_stance(band)]
        return Verdict(read=DEMO_READ, band=band, nudge=nudge, line=line)

    async def check_connection(self) -> ConnectionCheck:
        return ConnectionCheck(ok=True, message="The demo needs no connection.")
