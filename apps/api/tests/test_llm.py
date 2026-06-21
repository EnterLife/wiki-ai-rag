import asyncio

from wiki_ai_rag_api.services.llm import (
    ExtractiveLlmProvider,
    GroundedContext,
    LlmService,
    build_grounded_prompt,
)
from wiki_ai_rag_api.services.policy import INSUFFICIENT_CONTEXT_MESSAGE


def test_build_grounded_prompt_contains_question_context_and_policy() -> None:
    prompt = build_grounded_prompt(
        question="Что поддерживает Product X?",
        context=[
            GroundedContext(
                citation_id="1",
                title="Product X",
                quote="Product X supports PostgreSQL imports.",
                source_id="src_1",
                url="/wiki/product.md",
            )
        ],
    )

    assert "Не используй внешние знания" in prompt
    assert "Что поддерживает Product X?" in prompt
    assert "[1] Product X supports PostgreSQL imports." in prompt
    assert "src_1" in prompt


def test_extractive_provider_returns_cited_answer() -> None:
    service = LlmService(provider=ExtractiveLlmProvider())

    answer = asyncio.run(
        service.answer_with_context(
            question="Что поддерживает Product X?",
            context=[
                GroundedContext(
                    citation_id="1",
                    title="Product X",
                    quote="Product X supports PostgreSQL imports.",
                    source_id="src_1",
                )
            ],
        )
    )

    assert "PostgreSQL" in answer
    assert "[1]" in answer


class UncitedProvider:
    async def complete(self, prompt: str) -> str:
        return "Product X supports imports."


def test_uncited_llm_answer_is_refused() -> None:
    service = LlmService(provider=UncitedProvider())

    answer = asyncio.run(
        service.answer_with_context(
            question="Что поддерживает Product X?",
            context=[
                GroundedContext(
                    citation_id="1",
                    title="Product X",
                    quote="Product X supports PostgreSQL imports.",
                    source_id="src_1",
                )
            ],
        )
    )

    assert answer == INSUFFICIENT_CONTEXT_MESSAGE
