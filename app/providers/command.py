"""Any local program that reads a prompt on stdin and prints a verdict, as a provider.

The escape hatch for tools we have no adapter for. Such a program cannot be
handed a schema, so the verdict format is described in the prompt and the reply
is read with `verdict_from_text`, which still validates it in full.
"""

import tempfile
from collections.abc import Sequence
from pathlib import Path

from app.prompts import schema_instructions, system_prompt, user_message
from app.providers._subprocess import run_program
from app.providers._text import verdict_from_text
from app.providers.base import ConnectionCheck, ProviderError
from app.schema import Case, Duck, Verdict


class CommandProvider:
    name = "command"

    def __init__(
        self, argv: Sequence[str], *, max_concurrency: int = 4, timeout: float = 120.0
    ) -> None:
        if not argv:
            raise ValueError("a command provider needs a program to run")
        self._argv = tuple(argv)
        self.max_concurrency = max_concurrency
        self.timeout = timeout

    async def _run(self, prompt: str) -> str:
        with tempfile.TemporaryDirectory(prefix="duck-council-", ignore_cleanup_errors=True) as tmp:
            return await run_program(self._argv, stdin=prompt, cwd=Path(tmp))

    async def judge(self, duck: Duck, case: Case) -> Verdict:
        # A program reading stdin has no separate system slot, so the parts are joined.
        prompt = f"{system_prompt(duck)}\n\n{schema_instructions()}\n\n{user_message(case)}"
        return verdict_from_text(await self._run(prompt))

    async def check_connection(self) -> ConnectionCheck:
        try:
            reply = (await self._run("Reply with exactly: OK")).strip()
        except ProviderError as error:
            return ConnectionCheck(ok=False, message=str(error))
        if not reply:
            return ConnectionCheck(ok=False, message=f"{self._argv[0]} ran but printed nothing.")
        return ConnectionCheck(ok=True, message=f"{self._argv[0]} responded: {reply[:60]}")
