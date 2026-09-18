"""The Anthropic API, with a key, as a provider.

Kept separate from the OpenAI-compatible adapter rather than routed through a
gateway, because schema-validated output (`messages.parse` against our models)
and effort control are only reachable on the native API.

Effort defaults to "low": each duck gives a one-line judgement, which does not
repay deep reasoning, and thirteen of them run per hearing. The clerk's
joke-or-serious question goes to Haiku, the fastest model (D41), which does not
take an effort setting.

Refusals are not retried on another model. The API offers that, but D8 decided
a refusal should show as an empty chair, so the user sees that it happened.
"""

import anthropic
import httpx2
from pydantic import BaseModel

from app.prompts import CLERK_PROMPT, system_prompt, user_message
from app.providers.base import ConnectionCheck, Effort, ProviderError, Refused
from app.schema import Case, Duck, Ruling, Tone, Verdict

DEFAULT_MODEL = "claude-opus-5"
CLERK_MODEL = "claude-haiku-4-5"


def describe_error(error: anthropic.APIError) -> str:
    """A sentence a person can act on. Typed classes, never string-matching messages."""
    if isinstance(error, anthropic.AuthenticationError):
        return "Invalid API key."
    if isinstance(error, anthropic.PermissionDeniedError):
        return "This key is not allowed to use that model."
    if isinstance(error, anthropic.NotFoundError):
        return "Model not found. Check the model id."
    if isinstance(error, anthropic.RateLimitError):
        return "Rate limited. Try again shortly."
    if isinstance(error, anthropic.BadRequestError):
        return f"Rejected: {error.message}"
    if isinstance(error, anthropic.APIConnectionError):
        return "Could not reach the Anthropic API."
    if isinstance(error, anthropic.APIStatusError):
        return f"API error {error.status_code}: {error.message}"
    return str(error)


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        base_url: str | None = None,
        effort: Effort | None = "low",
        clerk_model: str = CLERK_MODEL,
        max_concurrency: int = 8,
        timeout: float = 90.0,
        http_client: httpx2.AsyncClient | None = None,
    ) -> None:
        # With no key given, the SDK looks for ANTHROPIC_API_KEY and its own login profile.
        # `http_client` is how tests substitute a fake network while keeping the real SDK.
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key, base_url=base_url, http_client=http_client
        )
        self._model = model
        self._effort = effort
        self._clerk_model = clerk_model
        self.max_concurrency = max_concurrency
        self.timeout = timeout

    async def _ask[T: BaseModel](
        self, system: str, user: str, schema: type[T], *, model: str, effort: Effort | None
    ) -> T:
        response = await self._client.messages.parse(
            model=model,
            max_tokens=16_000,  # thinking counts against this; a tight cap starves the answer
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=schema,
            output_config={"effort": effort} if effort else anthropic.omit,
        )
        if response.stop_reason == "refusal":
            raise Refused()
        if response.parsed_output is None:
            raise ProviderError(f"no answer returned (stop reason: {response.stop_reason})")
        return response.parsed_output

    async def judge(self, duck: Duck, case: Case, tone: Tone = "cautious") -> Verdict:
        return await self._ask(
            system_prompt(duck, tone),
            user_message(case),
            Verdict,
            model=self._model,
            effort=self._effort,
        )

    async def classify(self, case: Case) -> Ruling:
        return await self._ask(
            CLERK_PROMPT, user_message(case), Ruling, model=self._clerk_model, effort=None
        )

    async def check_connection(self) -> ConnectionCheck:
        try:
            await self._client.messages.create(
                model=self._model,
                max_tokens=32,
                messages=[{"role": "user", "content": "Reply with OK."}],
            )
        except anthropic.APIError as error:
            return ConnectionCheck(ok=False, message=describe_error(error))
        return ConnectionCheck(ok=True, message=f"Connected to {self._model}")
