"""Reading a structured answer out of plain text, for providers that cannot enforce a schema.

Claude Code and the Anthropic API return answers already checked against our
schema (D7). Some OpenAI-compatible vendors and custom commands can only return
text, so this finds a JSON object in it. The result is still validated in full:
anything malformed becomes an empty chair (or a cautious hearing), never a guess.
"""

import json

from pydantic import BaseModel, ValidationError

from app.providers.base import ProviderError


def parse_reply[T: BaseModel](text: str, schema: type[T]) -> T:
    """Return the first JSON object in `text` that is a valid `schema`."""
    decoder = json.JSONDecoder()
    start = text.find("{")
    while start != -1:
        try:
            candidate, _ = decoder.raw_decode(text, start)
            return schema.model_validate(candidate)
        except (json.JSONDecodeError, ValidationError):
            start = text.find("{", start + 1)
    raise ProviderError(f"the reply did not contain a valid {schema.__name__.lower()}")
