"""Running a local program as an AI provider, safely.

SECURITY: prompts carry text the user typed and, for user-created ducks (D14),
text the user wrote as a persona. Programs are started from an argument list
with no shell, so there is nothing to inject into: each argument arrives as
exactly one argument, whatever it contains. Never build a command string here,
however convenient it looks.
"""

import asyncio
from collections.abc import Sequence
from pathlib import Path

from app.providers.base import ProviderError


async def run_program(argv: Sequence[str], *, stdin: str | None, cwd: Path) -> str:
    """Run `argv` with `stdin` as input and return what it printed.

    `stdin=None` closes the program's input outright, so a program that would wait
    for input it is never going to get can tell at once.

    If the caller is cancelled (the council timed this duck out, or the listener
    left), the program is killed. Cancelling only the Python side would leave it
    running, still working and still using the user's subscription or GPU.
    """
    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=cwd,
            stdin=asyncio.subprocess.DEVNULL if stdin is None else asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as error:
        raise ProviderError(f'"{argv[0]}" was not found. Is it installed and on PATH?') from error
    except PermissionError as error:
        raise ProviderError(f'"{argv[0]}" is not executable.') from error

    try:
        payload = None if stdin is None else stdin.encode("utf-8")
        stdout, stderr = await process.communicate(payload)
    except BaseException:
        if process.returncode is None:
            process.kill()
        raise

    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="replace").strip()
        raise ProviderError(detail or f'"{argv[0]}" exited with code {process.returncode}')
    return stdout.decode("utf-8", errors="replace")
