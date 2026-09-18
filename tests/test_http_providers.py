"""The Anthropic and OpenAI-compatible adapters, using the real SDKs over a fake network.

Swapping the transport rather than the SDK means these tests exercise the SDKs'
own request building and response parsing, which is what could actually break.
"""

import asyncio
import json
from collections.abc import Callable
from typing import Any

import httpx2
import openai
import pytest

from app.ducks import DUCKS_BY_ID
from app.prompts import system_prompt, user_message
from app.providers import Refused
from app.providers.anthropic_api import AnthropicProvider
from app.providers.openai_compatible import OpenAICompatibleProvider, describe_error
from app.schema import Case

DUCK = DUCKS_BY_ID["lawyer"]
CASE = Case(situation="My flatmate eats my food.", action="Hide a ghost pepper in it.")
VERDICT = {"read": "Premeditated.", "band": "unwise", "nudge": -2, "line": "Objection."}

Handler = Callable[[httpx2.Request], httpx2.Response]


def fake_network(handler: Handler) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(transport=httpx2.MockTransport(handler))


# --- Anthropic ------------------------------------------------------------------------


def anthropic_message(text: str, stop_reason: str = "end_turn") -> dict[str, Any]:
    content = [{"type": "text", "text": text}] if text else []
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5",
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }


def anthropic(handler: Handler, **kwargs: Any) -> AnthropicProvider:
    return AnthropicProvider(api_key="test-key", http_client=fake_network(handler), **kwargs)


def test_anthropic_returns_a_validated_verdict() -> None:
    reply = anthropic_message(json.dumps(VERDICT))
    verdict = asyncio.run(anthropic(lambda _: httpx2.Response(200, json=reply)).judge(DUCK, CASE))
    assert (verdict.band, verdict.score) == ("unwise", 28)


def test_anthropic_request_carries_persona_case_schema_and_effort() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.update(json.loads(request.content))
        return httpx2.Response(200, json=anthropic_message(json.dumps(VERDICT)))

    asyncio.run(anthropic(handler).judge(DUCK, CASE))
    assert seen["system"] == system_prompt(DUCK)
    assert seen["messages"] == [{"role": "user", "content": user_message(CASE)}]
    assert seen["output_config"]["effort"] == "low"
    assert seen["output_config"]["format"]["type"] == "json_schema"


def test_anthropic_without_effort_leaves_it_to_the_model() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.update(json.loads(request.content))
        return httpx2.Response(200, json=anthropic_message(json.dumps(VERDICT)))

    asyncio.run(anthropic(handler, effort=None).judge(DUCK, CASE))
    assert "effort" not in seen.get("output_config", {})


def test_anthropic_refusal_is_an_empty_chair() -> None:
    reply = anthropic_message("", stop_reason="refusal")
    with pytest.raises(Refused):
        asyncio.run(anthropic(lambda _: httpx2.Response(200, json=reply)).judge(DUCK, CASE))


def test_anthropic_bad_key_is_explained() -> None:
    error = {"type": "error", "error": {"type": "authentication_error", "message": "invalid"}}
    check = asyncio.run(anthropic(lambda _: httpx2.Response(401, json=error)).check_connection())
    assert not check.ok and check.message == "Invalid API key."


# --- OpenAI-compatible ----------------------------------------------------------------


def completion(content: str | None, finish: str = "stop", refusal: str | None = None) -> Any:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "finish_reason": finish,
                "message": {"role": "assistant", "content": content, "refusal": refusal},
            }
        ],
    }


def compatible(handler: Handler) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        model="test-model", base_url="http://local.test/v1", http_client=fake_network(handler)
    )


def test_compatible_asks_for_schema_constrained_output() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.update(json.loads(request.content))
        return httpx2.Response(200, json=completion(json.dumps(VERDICT)))

    verdict = asyncio.run(compatible(handler).judge(DUCK, CASE))
    assert verdict.score == 28
    assert seen["response_format"]["type"] == "json_schema"


def test_compatible_falls_back_to_words_when_schemas_are_unsupported() -> None:
    requests: list[dict[str, Any]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        body = json.loads(request.content)
        requests.append(body)
        if "response_format" in body:
            return httpx2.Response(400, json={"error": {"message": "response_format unsupported"}})
        prose = f"Certainly. Here is my verdict: {json.dumps(VERDICT)} Hope that helps!"
        return httpx2.Response(200, json=completion(prose))

    verdict = asyncio.run(compatible(handler).judge(DUCK, CASE))
    assert verdict.score == 28
    assert len(requests) == 2
    assert "Reply with only a JSON object" in requests[1]["messages"][0]["content"]


@pytest.mark.parametrize(
    "reply", [completion(None, refusal="I can't help with that."), completion("", "content_filter")]
)
def test_compatible_refusal_is_an_empty_chair(reply: Any) -> None:
    with pytest.raises(Refused):
        asyncio.run(compatible(lambda _: httpx2.Response(200, json=reply)).judge(DUCK, CASE))


def test_unreachable_local_server_is_explained() -> None:
    error = openai.APIConnectionError(request=httpx2.Request("POST", "http://localhost:11434"))
    assert "server is running" in describe_error(error)
