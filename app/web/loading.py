"""Lines for the loading card shown while the ducks deliberate (D42).

A joke gets fun lines, including a couple about each duck actually sitting. A real
decision, or a case the clerk could not rule on, gets calm ones: nobody facing a
genuine choice should be told that Quack the Ripper is sharpening something.

Edit freely: this is copy, not logic.
"""

from collections.abc import Sequence

from app.schema import Duck, Tone

PLAYFUL: tuple[str, ...] = (
    "Ruffling feathers…",
    "Consulting the pond…",
    "Polishing the gavel…",
    "Counting breadcrumbs for evidence…",
    "Summoning the council from the reeds…",
    "Adjusting tiny judicial wigs…",
    "Waddling to the bench…",
    "Quacking in hushed tones…",
    "Checking the rulebook for loopholes…",
    "Drying off before the verdict…",
    "Sharpening quills…",
    "Arguing about the seating plan…",
)

GENTLE: tuple[str, ...] = (
    "The council is weighing this carefully…",
    "Taking this seriously…",
    "Considering every side…",
    "Listening closely…",
    "Thinking it through…",
    "Looking at what matters here…",
    "Giving this the time it deserves…",
)

DUCK_LINES: dict[str, tuple[str, ...]] = {
    "lawyer": (
        "Mallard Esquire III is citing a treaty that doesn't exist…",
        "Mallard Esquire III is billing you for this wait…",
    ),
    "doctor": (
        "Dr. Quackson is checking your pulse from afar…",
        "Dr. Quackson insists you drink some water first…",
    ),
    "witch": (
        "Obscura is reading the tea leaves. They look worried…",
        "Obscura is asking the moon for a second opinion…",
    ),
    "serial_killer": (
        "Quack the Ripper is sharpening… a pencil. Just a pencil.",
        "Quack the Ripper is humming something cheerful…",
    ),
    "gangsta": (
        "Lil Waddle is making a few calls…",
        "Lil Waddle is asking around about you…",
    ),
    "gamer": (
        "Duckthulu42 is theorycrafting your build…",
        "Duckthulu42 is reading the patch notes…",
    ),
    "rich": (
        "Sir Bill is running the numbers from his yacht…",
        "Sir Bill is asking what's in it for him…",
    ),
    "diplomat": (
        "Ambassador Plumière is drafting a compromise…",
        "Ambassador Plumière is translating into seventeen dialects…",
    ),
    "techno": (
        "011QuackX is compiling your life choices…",
        "011QuackX is rebooting its empathy module…",
    ),
    "king": (
        "Regalduke Feathersworth is consulting the ancient sages…",
        "The king is stroking his royal beak thoughtfully…",
    ),
    "spiritual_medium": (
        "Quackramentum is channelling a very chatty ghost…",
        "Quackramentum's demon has entered the chat…",
    ),
    "detective": (
        "Beaklock Holmes is dusting your case for fingerprints…",
        "Beaklock Holmes has found a clue. It's a breadcrumb.",
    ),
    "rebel": (
        "Flare is painting a protest sign about this…",
        "Flare is refusing to be rushed…",
    ),
}


def loading_lines(roster: Sequence[Duck], tone: Tone) -> list[str]:
    """Every line the card may show for this hearing. The page shuffles them."""
    if tone != "play":
        return [*GENTLE, *(f"{duck.name} is considering it carefully…" for duck in roster)]
    about_the_ducks = [
        line
        for duck in roster
        for line in DUCK_LINES.get(duck.id, (f"{duck.name} is thinking it over…",))
    ]
    return [*PLAYFUL, *about_the_ducks]
