from pydantic import BaseModel, Field, model_validator


class RetrievalEvaluationItem(BaseModel):
    question: str = Field(min_length=1)
    expected_document_ids: list[str] = Field(default_factory=list)
    expected_chunk_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] | None = None

    @model_validator(mode="after")
    def require_expected_evidence(self) -> "RetrievalEvaluationItem":
        if not self.expected_document_ids and not self.expected_chunk_ids:
            raise ValueError("expected_document_ids or expected_chunk_ids is required")
        return self


class RetrievalEvaluationRequest(BaseModel):
    items: list[RetrievalEvaluationItem] = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)


class RetrievalEvaluationCaseResult(BaseModel):
    question: str
    found: bool
    first_relevant_rank: int | None
    retrieved_chunk_ids: list[str]
    retrieved_document_ids: list[str]


class RetrievalEvaluationMetrics(BaseModel):
    cases: int
    recall_at_5: float
    recall_at_10: float
    mrr: float
    ndcg_at_10: float


class RetrievalEvaluationResponse(BaseModel):
    metrics: RetrievalEvaluationMetrics
    results: list[RetrievalEvaluationCaseResult]
