from __future__ import annotations

import math

from wiki_ai_rag_api.schemas.evaluation import (
    RetrievalEvaluationCaseResult,
    RetrievalEvaluationItem,
    RetrievalEvaluationMetrics,
    RetrievalEvaluationRequest,
    RetrievalEvaluationResponse,
)
from wiki_ai_rag_api.services.metrics import metrics_registry
from wiki_ai_rag_api.services.retrieval import RetrievedChunk, RetrievalService


class RetrievalEvaluationService:
    def __init__(self, retrieval: RetrievalService | None = None) -> None:
        self.retrieval = retrieval or RetrievalService()

    async def run(self, request: RetrievalEvaluationRequest) -> RetrievalEvaluationResponse:
        case_results: list[RetrievalEvaluationCaseResult] = []
        recall_at_5_values: list[float] = []
        recall_at_10_values: list[float] = []
        reciprocal_ranks: list[float] = []
        ndcg_at_10_values: list[float] = []

        search_top_k = max(request.top_k, 10)
        for item in request.items:
            chunks = await self.retrieval.search(
                query=item.question,
                top_k=search_top_k,
                source_ids=item.source_ids,
            )
            first_rank = _first_relevant_rank(item, chunks)
            case_results.append(
                RetrievalEvaluationCaseResult(
                    question=item.question,
                    found=first_rank is not None,
                    first_relevant_rank=first_rank,
                    retrieved_chunk_ids=[chunk.chunk_id for chunk in chunks[: request.top_k]],
                    retrieved_document_ids=[chunk.document_id for chunk in chunks[: request.top_k]],
                )
            )
            recall_at_5_values.append(_recall_at_k(item, chunks, 5))
            recall_at_10_values.append(_recall_at_k(item, chunks, 10))
            reciprocal_ranks.append(0.0 if first_rank is None else 1.0 / first_rank)
            ndcg_at_10_values.append(_ndcg_at_k(item, chunks, 10))

        metrics_registry.increment("evaluation.retrieval_runs")
        metrics_registry.increment("evaluation.retrieval_cases", len(request.items))

        return RetrievalEvaluationResponse(
            metrics=RetrievalEvaluationMetrics(
                cases=len(request.items),
                recall_at_5=_average(recall_at_5_values),
                recall_at_10=_average(recall_at_10_values),
                mrr=_average(reciprocal_ranks),
                ndcg_at_10=_average(ndcg_at_10_values),
            ),
            results=case_results,
        )


def _first_relevant_rank(
    item: RetrievalEvaluationItem,
    chunks: list[RetrievedChunk],
) -> int | None:
    for index, chunk in enumerate(chunks, start=1):
        if _is_relevant(item, chunk):
            return index
    return None


def _recall_at_k(
    item: RetrievalEvaluationItem,
    chunks: list[RetrievedChunk],
    k: int,
) -> float:
    expected = _expected_evidence_keys(item)
    if not expected:
        return 0.0
    found = {
        key
        for chunk in chunks[:k]
        for key in _matching_evidence_keys(item, chunk)
    }
    return round(len(found) / len(expected), 6)


def _ndcg_at_k(
    item: RetrievalEvaluationItem,
    chunks: list[RetrievedChunk],
    k: int,
) -> float:
    seen: set[tuple[str, str]] = set()
    relevances: list[float] = []
    for chunk in chunks[:k]:
        new_matches = _matching_evidence_keys(item, chunk) - seen
        relevances.append(1.0 if new_matches else 0.0)
        seen.update(new_matches)
    dcg = sum(relevance / math.log2(index + 2) for index, relevance in enumerate(relevances))
    ideal_relevant_count = min(_expected_evidence_count(item), k)
    if ideal_relevant_count == 0:
        return 0.0
    idcg = sum(1.0 / math.log2(index + 2) for index in range(ideal_relevant_count))
    return round(dcg / idcg, 6)


def _is_relevant(item: RetrievalEvaluationItem, chunk: RetrievedChunk) -> bool:
    return bool(_matching_evidence_keys(item, chunk))


def _expected_evidence_count(item: RetrievalEvaluationItem) -> int:
    return len(_expected_evidence_keys(item))


def _expected_evidence_keys(item: RetrievalEvaluationItem) -> set[tuple[str, str]]:
    return {
        *(("chunk", chunk_id) for chunk_id in item.expected_chunk_ids),
        *(("document", document_id) for document_id in item.expected_document_ids),
    }


def _matching_evidence_keys(
    item: RetrievalEvaluationItem,
    chunk: RetrievedChunk,
) -> set[tuple[str, str]]:
    matches: set[tuple[str, str]] = set()
    if chunk.chunk_id in item.expected_chunk_ids:
        matches.add(("chunk", chunk.chunk_id))
    if chunk.document_id in item.expected_document_ids:
        matches.add(("document", chunk.document_id))
    return matches


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)
