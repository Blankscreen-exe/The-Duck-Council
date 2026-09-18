"""Command-line council. Useful before the web app exists, and for tuning prompts later.

duck-council "situation" "action"             hear the full council
duck-council "situation" "action" --ducks doctor,rich
duck-council --list                           show the built-in ducks
duck-council --prompt doctor                  print one duck's system prompt
duck-council --providers                      show the AI providers you can use
duck-council "s" "a" --provider claude-code   use Claude Code on this PC
duck-council --provider anthropic --check     test a provider connection

API keys are read from the DUCK_COUNCIL_API_KEY environment variable, never from
a flag: command-line flags are saved in shell history, and a key would stay there.
"""

import argparse
import asyncio
import io
import os
import shlex
import sys
import textwrap
import time

from pydantic import ValidationError

from app.clerk import CRISIS_MESSAGE, is_crisis, rule, tone_for
from app.council import convene
from app.ducks import BUILTIN_DUCKS, DUCKS_BY_ID
from app.prompts import system_prompt
from app.providers import (
    PRESETS,
    PRESETS_BY_ID,
    DemoProvider,
    Provider,
    ProviderConfig,
    build_provider,
)
from app.providers.factory import API_KEY_ENV
from app.schema import Case, Duck, Seat
from app.tally import tally

WIDTH = 78
INDENT = " " * 22


def _parse_roster(raw: str | None) -> list[Duck]:
    if raw is None:
        return list(BUILTIN_DUCKS)
    ids = [part.strip() for part in raw.split(",") if part.strip()]
    unknown = [duck_id for duck_id in ids if duck_id not in DUCKS_BY_ID]
    if unknown:
        known = ", ".join(DUCKS_BY_ID)
        raise SystemExit(f"unknown duck(s): {', '.join(unknown)}\nknown: {known}")
    return [DUCKS_BY_ID[duck_id] for duck_id in dict.fromkeys(ids)]


def _print_seat(seat: Seat, elapsed: float) -> None:
    if seat.verdict is None:
        label = f"[ -- {seat.absence} ]"
        body = "Empty chair."
    else:
        label = f"[{seat.verdict.score:>3} {seat.verdict.band.replace('_', ' ')}]"
        body = seat.verdict.line
    print(f"  {label:<20}{seat.duck.name}   ({elapsed:.1f}s)")
    for row in textwrap.wrap(body, WIDTH - len(INDENT)):
        print(f"{INDENT}{row}")


def _print_finding(seats: list[Seat]) -> None:
    finding = tally(seats)
    print("-" * WIDTH)
    if finding.median is None:
        print("  THE COUNCIL FINDS NOTHING. Every chair is empty.")
        return

    verdict = "split decision" if finding.split else "the council agrees"
    print(f"  THE COUNCIL FINDS   {finding.median} / 100   {verdict}")
    counts = f"{finding.in_favour} in favour, {finding.against} against"
    if finding.undecided:
        counts += f", {finding.undecided} undecided"
    absent = finding.sitting - finding.voted
    if absent:
        counts += f", {absent} empty chair{'s' if absent > 1 else ''}"
    print(f"{INDENT}{counts}")

    if finding.lowest and finding.highest:
        scores = {s.duck.id: s.verdict.score for s in seats if s.verdict is not None}
        low, high = DUCKS_BY_ID.get(finding.lowest), DUCKS_BY_ID.get(finding.highest)
        low_name = low.name if low else finding.lowest
        high_name = high.name if high else finding.highest
        print(
            f"{INDENT}widest gap: {low_name} ({scores[finding.lowest]}) "
            f"vs {high_name} ({scores[finding.highest]})"
        )


def _build_provider(args: argparse.Namespace) -> Provider:
    if args.provider == "demo":
        return DemoProvider(latency=(0.0, 0.0)) if args.fast else DemoProvider()
    config = ProviderConfig.from_preset(
        args.provider,
        model=args.model,
        base_url=args.base_url,
        api_key=os.environ.get(API_KEY_ENV),
        command=tuple(shlex.split(args.command)) if args.command else (),
        effort=args.effort,
    )
    return build_provider(config)


async def _hear(ducks: list[Duck], case: Case, provider: Provider) -> None:
    print(f"THE DUCK COUNCIL  -  {len(ducks)} sitting  -  provider: {provider.name}")
    print("-" * WIDTH)
    print(textwrap.fill(case.situation, WIDTH, initial_indent="  I.  ", subsequent_indent="      "))
    print(textwrap.fill(case.action, WIDTH, initial_indent="  II. ", subsequent_indent="      "))
    print("-" * WIDTH)

    ruling = await rule(case, provider)
    if is_crisis(ruling):
        print(textwrap.fill(CRISIS_MESSAGE, WIDTH, initial_indent="  ", subsequent_indent="  "))
        return
    if ruling is None:
        print("  THE CLERK could not rule, so the case is heard cautiously.")
    else:
        print(f"  THE CLERK RULES: {ruling.hear_as}. {ruling.reason}")
    print("-" * WIDTH)

    started = time.perf_counter()
    by_id: dict[str, Seat] = {}
    tone = tone_for(ruling)
    async for seat in convene(ducks, case, provider, tone=tone):  # in the order they finish
        _print_seat(seat, time.perf_counter() - started)
        by_id[seat.duck.id] = seat

    _print_finding([by_id[duck.id] for duck in ducks])


def main(argv: list[str] | None = None) -> None:
    # Duck names include accented letters (Plumière). Speak UTF-8 so they render,
    # and replace rather than crash if a legacy console still cannot show them.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="duck-council", description="Bring a case before the Duck Council."
    )
    parser.add_argument("situation", nargs="?", help="what is going on")
    parser.add_argument("action", nargs="?", help="what you intend to do about it")
    parser.add_argument("--ducks", help="comma-separated duck ids (default: all)")
    parser.add_argument(
        "--provider",
        default="demo",
        choices=list(PRESETS_BY_ID),
        help="AI provider (default: demo)",
    )
    parser.add_argument("--model", help="model id, overriding the provider's default")
    parser.add_argument("--base-url", help="endpoint, for OpenAI-compatible providers")
    parser.add_argument(
        "--effort",
        default="low",
        choices=["low", "medium", "high", "xhigh", "max"],
        help="thinking effort, where supported (default: low)",
    )
    parser.add_argument("--command", help='program to run, for --provider command ("prog args")')
    parser.add_argument("--providers", action="store_true", help="list the AI providers")
    parser.add_argument("--check", action="store_true", help="test the provider and exit")
    parser.add_argument("--fast", action="store_true", help="skip the demo's simulated latency")
    parser.add_argument("--list", action="store_true", help="list the built-in ducks")
    parser.add_argument("--prompt", metavar="DUCK", help="print one duck's system prompt")
    args = parser.parse_args(argv)

    if args.providers:
        for preset in PRESETS:
            key = "needs API key" if preset.requires_key else "no key"
            print(f"  {preset.id:<14}{preset.label:<38}{key}")
        return

    try:
        provider = _build_provider(args)
    except ValueError as error:
        parser.error(str(error))

    if args.check:
        result = asyncio.run(provider.check_connection())
        print(f"{'OK' if result.ok else 'FAILED'}: {result.message}")
        raise SystemExit(0 if result.ok else 1)

    if args.list:
        for duck in BUILTIN_DUCKS:
            print(f"  {duck.id:<18}{duck.name:<28}{duck.epithet}")
        return

    if args.prompt:
        roster = _parse_roster(args.prompt)
        if len(roster) != 1:
            parser.error("--prompt takes exactly one duck id")
        print(system_prompt(roster[0]))
        return

    if not (args.situation and args.action):
        parser.error("give both a situation and an action, or use --list / --prompt")

    try:
        case = Case(situation=args.situation, action=args.action)
    except ValidationError as error:
        parser.error(f"invalid case: {error.errors()[0]['msg']}")
    asyncio.run(_hear(_parse_roster(args.ducks), case, provider))


if __name__ == "__main__":
    main()
