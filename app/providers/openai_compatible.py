"""One adapter for every vendor that speaks OpenAI's chat-completions protocol.

OpenAI, OpenRouter, Gemini's compatibility endpoint, DeepSeek, Groq, Ollama and
LM Studio differ only by base URL and model id, which is why they live in
`presets.py` as data rather than as code here.

Not all of them support schema-constrained output. We ask for it first; a vendor
that rejects the request gets the format described in words instead. Either way
the reply is validated before it counts. These vendors have no model we can name
as reliably fastest, so the clerk uses the same model as the ducks.
"""

import httpx2
import openai
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from app.prompts import CLERK_PROMPT, format_instructions, system_prompt, user_message
from app.providers._text import parse_reply
from app.providers.base import ConnectionCheck, ProviderError, Refused
from app.schema import Case, Duck, Ruling, Tone, Verdict


def describe_error(error: openai.APIError) -> str:
    if isinstance(error, openai.AuthenticationError):
        return "Invalid API key."
    if isinstance(error, openai.NotFoundError):
        return "Model not found. Check the model id."
    if isinstance(error, openai.RateLimitError):
        return "Rate limited, or out of quota."
    if isinstance(error, openai.BadRequestError):
        return f"Rejected: {error.message}"
    if isinstance(error, openai.APIConnectionError):
        # Overwhelmingly the local-runtime case: nothing is listening on that port.
        return "Could not reach the endpoint. Check the base URL, and that the server is running."
    if isinstance(error, openai.APIStatusError):
        return f"API error {error.status_code}: {error.message}"
    return str(error)


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(
        self,
        *,
        model: str,
        base_url: str | None,
        api_key: str | None = None,
        max_concurrency: int = 8,
        timeout: float = 90.0,
        http_client: httpx2.AsyncClient | None = None,
    ) -> None:
        self._client = openai.AsyncOpenAI(
            # Local runtimes ignore the key, but the client insists on a non-empty one.
            api_key=api_key or "not-needed",
            base_url=base_url,
            http_client=http_client,
        )
        self._model = model
        self.max_concurrency = max_concurrency
        self.timeout = timeout

    async def _ask[T: BaseModel](self, system: str, user: str, schema: type[T]) -> T:
        question: ChatCompletionMessageParam = {"role": "user", "content": user}
        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "system", "content": system}, question],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema.__name__.lower(),
                        "schema": schema.model_json_schema(),
                    },
                },
            )
        except openai.BadRequestError:
            # Most likely this vendor does not support schema-constrained output.
            # If the request was bad for another reason, this retry fails the same way.
            described = f"{system}\n\n{format_instructions(schema)}"
            completion = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "system", "content": described}, question],
            )
        if not completion.choices:
            raise ProviderError("the provider returned no answer")
        choice = completion.choices[0]
        if choice.finish_reason == "content_filter" or choice.message.refusal:
            raise Refused()
        return parse_reply(choice.message.content or "", schema)

    async def judge(self, duck: Duck, case: Case, tone: Tone = "cautious") -> Verdict:
        return await self._ask(system_prompt(duck, tone), user_message(case), Verdict)

    async def classify(self, case: Case) -> Ruling:
        return await self._ask(CLERK_PROMPT, user_message(case), Ruling)

    async def check_connection(self) -> ConnectionCheck:
        try:
            await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "Reply with OK."}],
            )
        except openai.APIError as error:
            return ConnectionCheck(ok=False, message=describe_error(error))
        return ConnectionCheck(ok=True, message=f"Connected to {self._model}")
