"""Reading a verdict out of plain text, for providers that cannot enforce a schema.

Claude Code and the Anthropic API return verdicts already checked against our
schema (D7). Some OpenAI-compatible vendors and custom commands can only return
text, so this finds a JSON object in it. The result is still validated against
`Verdict` in full: anything malformed becomes an empty chair, never a guess.
"""

import json

from pydantic import ValidationError

from app.providers.base import ProviderError
from app.schema import Verdict


def verdict_from_text(text: str) -> Verdict:
    """Return the first JSON object in `text` that is a valid verdict."""
    decoder = json.JSONDecoder()
    start = text.find("{")
    while start != -1:
        try:
            candidate, _ = decoder.raw_decode(text, start)
            return Verdict.model_validate(candidate)
        except (json.JSONDecodeError, ValidationError):
            start = text.find("{", start + 1)
    raise ProviderError("the reply did not contain a valid verdict")
