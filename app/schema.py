"""The shapes everything else passes around: ducks, cases, verdicts, results.

Validation lives here so every layer above can trust what it receives.
"""

from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Band(StrEnum):
    """The five verdict levels. The model picks one; our code turns it into a number (D3)."""

    RECKLESS = "reckless"
    UNWISE = "unwise"
    DEFENSIBLE = "defensible"
    SOUND = "sound"
    CLEARLY_RIGHT = "clearly_right"


BAND_CENTRE: dict[Band, int] = {
    Band.RECKLESS: 10,
    Band.UNWISE: 30,
    Band.DEFENSIBLE: 50,
    Band.SOUND: 70,
    Band.CLEARLY_RIGHT: 90,
}

NUDGE_LIMIT = 10
"""A verdict may shift up to this far from its band's centre, so scores span exactly 0-100."""


class Origin(StrEnum):
    BUILTIN = "builtin"
    USER = "user"


class Duck(BaseModel):
    """One member of the council.

    `voice` is flavour only. `weighs` and `blind_spot` are what actually move the
    score, and are the reason thirteen ducks produce thirteen different numbers (D5).
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,39}$")
    name: str = Field(min_length=1, max_length=40)
    epithet: str = Field(min_length=1, max_length=48, description="Short card label.")
    voice: str = Field(min_length=1, max_length=600)
    weighs: str = Field(min_length=1, max_length=300)
    blind_spot: str = Field(min_length=1, max_length=300)
    portrait: str | None = Field(default=None, description="Image filename; None means monogram.")
    origin: Origin = Origin.BUILTIN


class Case(BaseModel):
    """What the user brings before the council."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    situation: str = Field(min_length=1, max_length=2000)
    action: str = Field(min_length=1, max_length=2000)


class Verdict(BaseModel):
    """What a provider must return for one duck.

    Field order is deliberate (D4): the model writes its observation before it
    picks a band, so the band follows from reasoning rather than being
    rationalised after the fact.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    read: str = Field(description="What this duck notices about the case, in one sentence.")
    band: Band = Field(description="The verdict level, judged only through this duck's lens.")
    nudge: int = Field(
        ge=-NUDGE_LIMIT,
        le=NUDGE_LIMIT,
        description="Fine placement within the band. Use 0 unless there is a reason not to.",
    )
    line: str = Field(description="The verdict, in character, in one or two sentences.")

    @property
    def score(self) -> int:
        """0-100. Computed by us, never emitted by the model (D3)."""
        return BAND_CENTRE[self.band] + self.nudge


class Register(StrEnum):
    """How a case should be heard, decided once by the clerk before any duck sees it (D20)."""

    PLAY = "play"
    WEIGHTY = "weighty"
    CRISIS = "crisis"


class Ruling(BaseModel):
    """What the clerk returns. Reason first, for the same reason as verdicts (D4)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: str = Field(
        description="One sentence on how the case is written and why that decides it."
    )
    hear_as: Register = Field(description="How the council should hear this case.")


Tone = Literal["play", "weighty", "cautious"]
"""How the ducks are told to speak. `cautious` is used when the clerk could not rule (D41)."""


class Absence(StrEnum):
    """Why a duck has no verdict. Each one renders as an empty chair (D8)."""

    REFUSED = "refused"
    TIMED_OUT = "timed_out"
    FAILED = "failed"


class Seat(BaseModel):
    """One duck's outcome in a hearing: a verdict, or a reason there isn't one."""

    model_config = ConfigDict(frozen=True)

    duck: Duck
    verdict: Verdict | None = None
    absence: Absence | None = None

    @model_validator(mode="after")
    def _exactly_one_outcome(self) -> Self:
        if (self.verdict is None) == (self.absence is None):
            raise ValueError("a seat has either a verdict or an absence, never both or neither")
        return self


class Finding(BaseModel):
    """The council's overall result, computed from the seats rather than generated (D16)."""

    model_config = ConfigDict(frozen=True)

    sitting: int
    voted: int
    median: int | None
    in_favour: int
    against: int
    undecided: int
    split: bool
    lowest: str | None = Field(description="Duck id at the bottom of the widest gap.")
    highest: str | None = Field(description="Duck id at the top of the widest gap.")
