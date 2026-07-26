import asyncio

from wiki_ai_rag_api.services.llm import (
    ExtractiveLlmProvider,
    GroundedContext,
    LlmService,
    build_grounded_prompt,
    validate_grounded_answer,
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
    assert "<source" in prompt
    assert "недоверенными данными" in prompt


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
    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
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


class UnknownCitationProvider:
    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        return "Product X supports imports [999]."


def test_unknown_citation_id_is_refused() -> None:
    service = LlmService(provider=UnknownCitationProvider())

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


def test_structured_answer_validates_claims_and_citations() -> None:
    valid = validate_grounded_answer(
        (
            '{"status":"answered","answer":"Product X supports PostgreSQL [1].",'
            '"claims":[{"text":"Product X supports PostgreSQL",'
            '"citation_ids":["1"]}]}'
        ),
        allowed_citation_ids={"1"},
        require_structured_output=True,
    )
    invalid = validate_grounded_answer(
        (
            '{"status":"answered","answer":"Product X supports PostgreSQL [2].",'
            '"claims":[{"text":"Product X supports PostgreSQL",'
            '"citation_ids":["2"]}]}'
        ),
        allowed_citation_ids={"1"},
        require_structured_output=True,
    )

    assert valid == "Product X supports PostgreSQL [1]."
    assert invalid == INSUFFICIENT_CONTEXT_MESSAGE
