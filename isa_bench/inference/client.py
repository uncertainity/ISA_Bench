"""OpenAI-compatible LLM client for ISA_bench.

Works with OpenAI API, Ollama, and other OpenAI-compatible endpoints.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json
import urllib.request
import urllib.error


@dataclass
class Message:
    """Chat message."""

    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class CompletionResponse:
    """Response from LLM completion."""

    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)


THINKING_MODEL_PREFIXES = ("qwen3:", "deepseek-r1", "gemma4", "gemma3")
NON_THINKING_MODELS = ("qwen3-coder", "granite4")


class LLMClient:
    """OpenAI-compatible LLM client with Ollama native API support for thinking models.

    Works with:
    - OpenAI API: base_url="https://api.openai.com/v1"
    - Ollama: base_url="http://localhost:11434/v1"
    - Any OpenAI-compatible endpoint

    For thinking models on Ollama, auto-switches to the native /api/chat endpoint
    which properly returns thinking traces instead of stripping them.

    Example:
        client = LLMClient(
            base_url="http://localhost:11434/v1",
            model="qwen3:8b",  # auto-detects thinking model, uses native API
        )
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        api_key: Optional[str] = None,
        model: str = "qwen2.5-coder:7b",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 120,
        use_native_api: Optional[bool] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        self._ollama_host = (
            self.base_url.rsplit("/v1", 1)[0]
            if "/v1" in self.base_url
            else self.base_url
        )

        if use_native_api is None:
            self.use_native_api = (
                "localhost" in self.base_url
                and any(self.model.startswith(p) for p in THINKING_MODEL_PREFIXES)
                and not any(self.model.startswith(p) for p in NON_THINKING_MODELS)
            )
        else:
            self.use_native_api = use_native_api

    def _chat_native(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> CompletionResponse:
        """Chat via Ollama native /api/chat with thinking support."""
        url = f"{self._ollama_host}/api/chat"

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "think": True,
            "options": {
                "temperature": (
                    temperature if temperature is not None else self.temperature
                ),
                "num_predict": (
                    max_tokens if max_tokens is not None else self.max_tokens
                ),
            },
        }

        headers = {"Content-Type": "application/json"}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"API error {e.code}: {error_body}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Connection error: {e.reason}") from e

        msg = result.get("message", {})
        thinking = msg.get("thinking", "")
        content = msg.get("content", "")

        if thinking:
            combined = f"<think>{thinking}</think>\n{content}"
        else:
            combined = content

        usage = {}
        if "prompt_eval_count" in result:
            usage["prompt_tokens"] = result["prompt_eval_count"]
        if "eval_count" in result:
            usage["completion_tokens"] = result["eval_count"]
        if usage:
            usage["total_tokens"] = usage.get("prompt_tokens", 0) + usage.get(
                "completion_tokens", 0
            )

        return CompletionResponse(
            content=combined,
            model=result.get("model", self.model),
            usage=usage,
            raw=result,
        )

    def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
    ) -> CompletionResponse:
        if self.use_native_api:
            return self._chat_native(messages, temperature, max_tokens)

        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }

        if stop:
            payload["stop"] = stop

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"API error {e.code}: {error_body}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Connection error: {e.reason}") from e

        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})

        return CompletionResponse(
            content=content,
            model=result.get("model", self.model),
            usage=usage,
            raw=result,
        )

    def list_models(self) -> List[str]:
        """List available models."""
        url = f"{self.base_url}/models"

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(url, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"API error {e.code}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Connection error: {e.reason}") from e

        return [m["id"] for m in result.get("data", [])]

    def is_available(self) -> bool:
        """Check if the API endpoint is available."""
        try:
            self.list_models()
            return True
        except Exception:
            return False
