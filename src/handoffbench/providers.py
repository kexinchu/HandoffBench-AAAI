"""Minimal OpenAI-compatible providers; no vendor SDK dependency."""

from __future__ import annotations

import json
import hashlib
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence


class Provider(Protocol):
    def complete(self, messages: Sequence[dict[str, str]], *, model: str, temperature: float,
                 response_schema: dict[str, Any] | None = None,
                 schema_name: str | None = None, seed: int | None = None,
                 max_output_tokens: int | None = None) -> str: ...


@dataclass
class OpenAICompatibleProvider:
    base_url: str = "http://127.0.0.1:8000/v1"
    api_key: str = "EMPTY"
    timeout: float = 120.0
    last_usage: dict[str, int] | None = field(default=None, init=False)

    def complete(self, messages: Sequence[dict[str, str]], *, model: str, temperature: float,
                 response_schema: dict[str, Any] | None = None,
                 schema_name: str | None = None, seed: int | None = None,
                 max_output_tokens: int | None = None) -> str:
        payload: dict[str, Any] = {"model": model, "messages": list(messages),
                                   "temperature": temperature}
        if seed is not None:
            payload["seed"] = seed
        if max_output_tokens is not None:
            payload["max_tokens"] = max_output_tokens
        if response_schema is not None:
            payload["response_format"] = {"type": "json_schema", "json_schema": {
                "name": schema_name or "structured_output", "strict": True,
                "schema": response_schema}}
        body = json.dumps(payload).encode()
        request = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions", data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")
            raise RuntimeError(f"provider HTTP {error.code}: {detail}") from error
        usage = payload.get("usage")
        self.last_usage = dict(usage) if isinstance(usage, dict) else None
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("malformed OpenAI-compatible response") from error


@dataclass
class DeterministicFakeProvider:
    responses: list[str]
    calls: list[dict[str, Any]] = field(default_factory=list)

    def complete(self, messages: Sequence[dict[str, str]], *, model: str, temperature: float,
                 response_schema: dict[str, Any] | None = None,
                 schema_name: str | None = None, seed: int | None = None,
                 max_output_tokens: int | None = None) -> str:
        schema_hash = None
        if response_schema is not None:
            raw = json.dumps(response_schema, sort_keys=True, separators=(",", ":"))
            schema_hash = hashlib.sha256(raw.encode()).hexdigest()
        self.calls.append({"messages": list(messages), "model": model, "temperature": temperature,
                           "schema_name": schema_name, "response_schema_hash": schema_hash,
                           "seed": seed, "max_output_tokens": max_output_tokens})
        index = len(self.calls) - 1
        if index >= len(self.responses):
            raise RuntimeError("fake provider response queue exhausted")
        return self.responses[index]
