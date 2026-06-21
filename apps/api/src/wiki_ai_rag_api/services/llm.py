from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

import httpx

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.services.policy import INSUFFICIENT_CONTEXT_MESSAGE


@dataclass(frozen=True)
class GroundedContext:
    citation_id: str
    title: str
    quote: str
    source_id: str
    url: str | None = None


class LlmProvider(Protocol):
    async def complete(self, prompt: str) -> str:
        raise NotImplementedError


class ExtractiveLlmProvider:
    async def complete(self, prompt: str) -> str:
        quotes = re.findall(r"\[(\d+)]\s+(.+)", prompt)
        if not quotes:
            return INSUFFICIENT_CONTEXT_MESSAGE

        lines = ["По найденным источникам:"]
        for citation_id, quote in quotes[:5]:
            lines.append(f"[{citation_id}] {quote}")
        return "\n\n".join(lines)


class OllamaLlmProvider:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            payload = response.json()
            return payload.get("message", {}).get("content", "").strip()


class OpenAiCompatibleLlmProvider:
    def __init__(self, base_url: str, model: str, api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    async def complete(self, prompt: str) -> str:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "temperature": 0,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            payload = response.json()
            return payload["choices"][0]["message"]["content"].strip()


class LlmService:
    def __init__(self, provider: LlmProvider | None = None) -> None:
        self.provider = provider or build_llm_provider()

    async def answer_with_context(self, question: str, context: list[GroundedContext]) -> str:
        if not context:
            return INSUFFICIENT_CONTEXT_MESSAGE

        prompt = build_grounded_prompt(question=question, context=context)
        answer = await self.provider.complete(prompt)
        if not has_citation_marker(answer):
            return INSUFFICIENT_CONTEXT_MESSAGE
        return answer


def build_llm_provider() -> LlmProvider:
    settings = get_settings()
    if settings.llm_provider in {"extractive", "stub"}:
        return ExtractiveLlmProvider()
    if settings.llm_provider == "ollama":
        return OllamaLlmProvider(base_url=settings.llm_base_url, model=settings.llm_model)
    if settings.llm_provider == "openai_compatible":
        return OpenAiCompatibleLlmProvider(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
        )
    raise ValueError(f"LLM provider '{settings.llm_provider}' is not implemented yet")


def build_grounded_prompt(question: str, context: list[GroundedContext]) -> str:
    context_lines = [
        f"[{item.citation_id}] {item.quote}\n"
        f"source_id: {item.source_id}\n"
        f"title: {item.title}\n"
        f"url: {item.url or ''}"
        for item in context
    ]
    context_block = "\n\n".join(context_lines)
    return (
        "Ты отвечаешь на вопрос пользователя только по контексту ниже.\n"
        "Не используй внешние знания.\n"
        f'Если контекста недостаточно, ответь: "{INSUFFICIENT_CONTEXT_MESSAGE}"\n'
        "Каждое существенное утверждение сопровождай ссылкой на источник в формате [n].\n\n"
        f"Вопрос:\n{question}\n\n"
        f"Контекст:\n{context_block}"
    )


def has_citation_marker(answer: str) -> bool:
    return bool(re.search(r"\[\d+]", answer))
