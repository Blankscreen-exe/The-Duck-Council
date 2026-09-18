"""Claude Code, already installed and signed in on this PC, as a provider (D31).

The point is cost: `claude -p` runs on the subscription the user is already
signed into, so no API key is involved. Claude Code is a full coding agent, so
every flag below exists to reduce it to a single structured answer.

Measured on this project: about 17s per duck, of which only 4-7s is the model.
The rest is Claude Code starting up, once per call. Running ducks side by side
hides most of it, which is why concurrency here is generous.

The case is passed as an argument, not on stdin. Claude Code gives up on stdin
if nothing arrives within 3 seconds, and several copies starting at once are
slow enough to trip that even when the data is already waiting: two of four
ducks failed that way in testing. There is no shell, so an argument is exactly
one argument whatever the user typed.
"""

import json
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from app.prompts import system_prompt, user_message
from app.providers._subprocess import run_program
from app.providers.base import ConnectionCheck, Effort, ProviderError, Refused
from app.schema import Case, Duck, Verdict

_VERDICT_SCHEMA = json.dumps(Verdict.model_json_schema())

# Flags every call shares, and why:
#   -p <prompt>               the prompt sits directly after -p, where it can never be
#                             swallowed by an option that takes a list (like --tools)
#   --output-format json      one answer, wrapped in a JSON envelope we can check
#   --tools ""                no tools at all: a verdict needs no files, shell or web
#   --restricted              also ignore user/project settings files
#   --no-session-persistence  don't litter the user's session history with verdicts
# Never add --bare. It looks like the tidier choice, but it switches Claude Code
# to API-key-only auth and ignores the subscription login, which is the whole point.
_SHARED_FLAGS = ("--output-format", "json", "--tools", "", "--restricted",
                 "--no-session-persistence")  # fmt: skip


def _parse_envelope(stdout: str) -> dict[str, Any]:
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise ProviderError("Claude Code did not return JSON") from error
    if not isinstance(envelope, dict):
        raise ProviderError("Claude Code returned an unexpected reply")
    return envelope


def _require_success(envelope: dict[str, Any]) -> None:
    # Claude Code reports failures such as "not logged in" in-band with exit code 0,
    # so the envelope must be checked or an error message would pass as an answer.
    if envelope.get("is_error") or envelope.get("subtype") != "success":
        raise ProviderError(str(envelope.get("result") or "Claude Code reported an error"))


class ClaudeCodeProvider:
    name = "claude_code"

    def __init__(
        self,
        *,
        model: str = "default",
        effort: Effort | None = "low",
        executable: Sequence[str] = ("claude",),
        max_concurrency: int = 6,
        timeout: float = 120.0,
    ) -> None:
        self._model = model
        self._effort = effort
        self._executable = tuple(executable)
        self.max_concurrency = max_concurrency
        self.timeout = timeout

    def _argv(self, prompt: str, *extra: str) -> list[str]:
        argv = [*self._executable, "-p", prompt, *_SHARED_FLAGS, *extra]
        if self._model != "default":  # "default" means whatever the user's Claude Code uses
            argv += ["--model", self._model]
        if self._effort is not None:
            argv += ["--effort", self._effort]
        return argv

    async def _run(self, argv: list[str], workdir: Path) -> dict[str, Any]:
        # stdin=None closes Claude Code's input, so it never waits for any.
        return _parse_envelope(await run_program(argv, stdin=None, cwd=workdir))

    async def judge(self, duck: Duck, case: Case) -> Verdict:
        # A fresh, empty working directory for every call. Run from the project folder,
        # Claude Code would read our CLAUDE.md into the duck's context.
        with tempfile.TemporaryDirectory(prefix="duck-council-", ignore_cleanup_errors=True) as tmp:
            workdir = Path(tmp)
            # The persona goes in a file: it is the system prompt, and a user-written
            # duck (D14) can be long enough to crowd a command line.
            persona = workdir / "system.txt"
            persona.write_text(system_prompt(duck), encoding="utf-8")
            argv = self._argv(
                user_message(case),
                "--json-schema",
                _VERDICT_SCHEMA,
                "--system-prompt-file",
                str(persona),
            )
            envelope = await self._run(argv, workdir)

        # Checked before success: a refusal must become an empty chair marked "refused",
        # not a generic failure, whichever way Claude Code chooses to flag it.
        if envelope.get("stop_reason") == "refusal":
            raise Refused()
        _require_success(envelope)
        structured = envelope.get("structured_output")
        if structured is None:
            raise ProviderError("Claude Code returned no structured verdict")
        return Verdict.model_validate(structured)

    async def check_connection(self) -> ConnectionCheck:
        try:
            with tempfile.TemporaryDirectory(
                prefix="duck-council-", ignore_cleanup_errors=True
            ) as tmp:
                envelope = await self._run(self._argv("Reply with exactly: OK"), Path(tmp))
            _require_success(envelope)
            reply = str(envelope.get("result", "")).strip()
        except ProviderError as error:
            return ConnectionCheck(ok=False, message=str(error))
        if not reply:
            return ConnectionCheck(ok=False, message="Claude Code ran but returned nothing.")
        return ConnectionCheck(ok=True, message=f"Claude Code responded: {reply[:60]}")
