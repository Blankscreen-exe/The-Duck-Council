"""The only place that turns a provider configuration into a concrete adapter.

Callers ask for a provider and get the `Provider` interface back. Adding an
adapter is one more `case` below; the type checker refuses to pass until a new
`ProviderKind` is handled, so a kind can never silently fall through.
"""

from typing import assert_never

from pydantic import BaseModel, ConfigDict, SecretStr

from app.providers.anthropic_api import AnthropicProvider
from app.providers.base import Effort, Provider
from app.providers.claude_code import ClaudeCodeProvider
from app.providers.command import CommandProvider
from app.providers.demo import DemoProvider
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.presets import PRESETS_BY_ID, ProviderKind

API_KEY_ENV = "DUCK_COUNCIL_API_KEY"
"""Where the CLI and the web app read an API key from. Never a flag: flags land in
shell history (D33)."""


class ProviderConfig(BaseModel):
    """Everything needed to build one provider."""

    model_config = ConfigDict(frozen=True)

    kind: ProviderKind
    model: str
    base_url: str | None = None
    # SecretStr keeps the key out of logs, tracebacks and reprs (D12).
    api_key: SecretStr | None = None
    command: tuple[str, ...] = ()
    effort: Effort | None = "low"

    @classmethod
    def from_preset(
        cls,
        preset_id: str,
        *,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        command: tuple[str, ...] = (),
        effort: Effort | None = "low",
    ) -> "ProviderConfig":
        try:
            preset = PRESETS_BY_ID[preset_id]
        except KeyError:
            raise ValueError(f"unknown provider {preset_id!r}") from None
        return cls(
            kind=preset.kind,
            model=model or preset.default_model,
            base_url=base_url if base_url is not None else preset.base_url,
            api_key=SecretStr(api_key) if api_key else None,
            command=command,
            effort=effort,
        )


def build_provider(config: ProviderConfig) -> Provider:
    key = config.api_key.get_secret_value() if config.api_key else None
    match config.kind:
        case "demo":
            return DemoProvider()
        case "claude_code":
            return ClaudeCodeProvider(model=config.model, effort=config.effort)
        case "anthropic":
            return AnthropicProvider(
                model=config.model, api_key=key, base_url=config.base_url, effort=config.effort
            )
        case "openai_compatible":
            if not config.base_url:
                raise ValueError("an OpenAI-compatible provider needs a base URL")
            return OpenAICompatibleProvider(
                model=config.model, base_url=config.base_url, api_key=key
            )
        case "command":
            return CommandProvider(config.command)
        case _:
            assert_never(config.kind)
