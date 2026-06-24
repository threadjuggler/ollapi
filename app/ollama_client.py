"""Thin async client around the Ollama HTTP API."""

import json
from typing import AsyncGenerator

import httpx

from .config import settings


class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]

    async def has_model(self, model: str) -> bool:
        try:
            models = await self.list_models()
        except Exception:  # noqa: BLE001
            return False
        # Ollama reports tags like "gemma4:e2b"; treat a bare name as ":latest".
        wanted = model if ":" in model else f"{model}:latest"
        return wanted in models or model in models

    async def chat_stream(
        self, model: str, messages: list[dict], options: dict
    ) -> AsyncGenerator[dict, None]:
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": options,
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{self.base_url}/api/chat", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.strip():
                        yield json.loads(line)

    async def pull_stream(self, model: str) -> AsyncGenerator[dict, None]:
        payload = {"model": model, "stream": True}
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{self.base_url}/api/pull", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.strip():
                        yield json.loads(line)


ollama = OllamaClient(settings.ollama_base_url)
