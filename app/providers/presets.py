"""Known providers, as data (D31).

Most vendors differ only by base URL and model id, so they are rows here rather
than code. Base URLs and model ids drift: treat each row as a starting point
the user can override, and verify it before relying on it.
"""

from dataclasses import dataclass
from typing import Literal

ProviderKind = Literal["demo", "claude_code", "anthropic", "openai_compatible", "command"]


@dataclass(frozen=True)
class Preset:
    id: str
    label: str
    kind: ProviderKind
    default_model: str
    base_url: str | None = None
    requires_key: bool = False
    help_url: str | None = None
    note: str | None = None


PRESETS: tuple[Preset, ...] = (
    Preset(
        id="demo",
        label="Demo (no AI)",
        kind="demo",
        default_model="demo",
        note="Works with nothing installed. Verdicts are scripted, and say so.",
    ),
    Preset(
        id="claude-code",
        label="Claude Code (installed on this PC)",
        kind="claude_code",
        default_model="default",
        help_url="https://claude.com/claude-code",
        note="No API key: uses the Claude subscription you are signed into. About 15-20s "
        "per hearing, mostly Claude Code starting up.",
    ),
    Preset(
        id="anthropic",
        label="Anthropic API (Claude)",
        kind="anthropic",
        default_model="claude-opus-5",
        requires_key=True,
        help_url="https://console.anthropic.com/settings/keys",
        note="Schema-checked verdicts and effort control. A few seconds per hearing.",
    ),
    Preset(
        id="openai",
        label="OpenAI",
        kind="openai_compatible",
        default_model="gpt-5",
        base_url="https://api.openai.com/v1",
        requires_key=True,
        help_url="https://platform.openai.com/api-keys",
    ),
    Preset(
        id="openrouter",
        label="OpenRouter",
        kind="openai_compatible",
        default_model="anthropic/claude-opus-4.1",
        base_url="https://openrouter.ai/api/v1",
        requires_key=True,
        help_url="https://openrouter.ai/keys",
        note="One key reaches most vendors.",
    ),
    Preset(
        id="google",
        label="Google (Gemini)",
        kind="openai_compatible",
        default_model="gemini-2.5-pro",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        requires_key=True,
        help_url="https://aistudio.google.com/apikey",
        note="Has a free tier.",
    ),
    Preset(
        id="deepseek",
        label="DeepSeek",
        kind="openai_compatible",
        default_model="deepseek-chat",
        base_url="https://api.deepseek.com/v1",
        requires_key=True,
        help_url="https://platform.deepseek.com/api_keys",
    ),
    Preset(
        id="groq",
        label="Groq",
        kind="openai_compatible",
        default_model="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        requires_key=True,
        help_url="https://console.groq.com/keys",
    ),
    Preset(
        id="ollama",
        label="Ollama (local)",
        kind="openai_compatible",
        default_model="llama3.3",
        base_url="http://localhost:11434/v1",
        note="Free and fully offline. The five-band verdict (D3) is simple enough for "
        "small models.",
    ),
    Preset(
        id="lmstudio",
        label="LM Studio (local)",
        kind="openai_compatible",
        default_model="local-model",
        base_url="http://localhost:1234/v1",
    ),
    Preset(
        id="custom",
        label="Custom (OpenAI-compatible)",
        kind="openai_compatible",
        default_model="",
        base_url="",
        requires_key=True,
        note="Any endpoint exposing /chat/completions.",
    ),
    Preset(
        id="command",
        label="Custom command line",
        kind="command",
        default_model="default",
        note="Any program that reads a prompt on stdin and prints a JSON verdict.",
    ),
)

PRESETS_BY_ID: dict[str, Preset] = {preset.id: preset for preset in PRESETS}
