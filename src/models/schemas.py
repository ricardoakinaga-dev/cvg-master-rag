from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import uuid4


# ─── Document ───────────────────────────────────────────────


class DocumentUploadResponse(BaseModel):
    document_id: str
    status: Literal["parsed", "failed", "partial"]
    catalog_scope: Literal["canonical", "operational"] = "canonical"
    source_type: str
    filename: str
    page_count: Optional[int] = None
    char_count: int
    chunk_count: int
    created_at: str
    chunking_strategy: str = "recursive"


class DocumentMetadata(BaseModel):
    document_id: str
    workspace_id: str
    catalog_scope: Literal["canonical", "operational"] = "canonical"
    source_type: str
    filename: str
    page_count: Optional[int] = None
    char_count: int
    chunk_count: int
    status: Literal["parsed", "failed", "partial"]
    created_at: str
    chunking_strategy: str = "recursive"
    tags: list[str] = Field(default_factory=list)
    embeddings_model: Optional[str] = None
    indexed_at: Optional[str] = None


class DocumentListItem(DocumentMetadata):
    file_path: Optional[str] = None


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
    workspace_id: str


# ─── Enterprise Session ─────────────────────────────────────


class EnterpriseTenant(BaseModel):
    tenant_id: str
    name: str
    workspace_id: str
    plan: Literal["starter", "business", "enterprise"] = "enterprise"
    status: Literal["active", "suspended"] = "active"
    document_count: int = 0
    operational_retention_mode: Literal["keep_latest", "keep_all"] = "keep_latest"
    operational_retention_hours: int = 24


class EnterpriseUser(BaseModel):
    user_id: str
    name: str
    email: str
    role: Literal["admin", "operator", "viewer"]
    permissions: list[str] = Field(default_factory=list)


class EnterpriseSession(BaseModel):
    authenticated: bool = True
    session_state: Literal["active", "expired", "anonymous"] = "active"
    expires_at: Optional[str] = None
    session_token: Optional[str] = None
    user: EnterpriseUser
    active_tenant: EnterpriseTenant
    available_tenants: list[EnterpriseTenant] = Field(default_factory=list)
    message: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str
    tenant_id: str = "default"


class RecoveryRequest(BaseModel):
    email: str
    tenant_id: Optional[str] = None
    reason: Optional[str] = None


class RecoveryResponse(BaseModel):
    status: Literal["queued"] = "queued"
    message: str


class LogoutResponse(BaseModel):
    status: Literal["signed_out"] = "signed_out"


class TenantSwitchRequest(BaseModel):
    tenant_id: str


class AdminEvent(BaseModel):
    timestamp: str
    type: Literal["admin_event"] = "admin_event"
    actor_user_id: str
    actor_email: str
    actor_role: str
    action: str
    target_type: str
    target_id: str
    tenant_id: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class AdminEventListResponse(BaseModel):
    items: list[AdminEvent] = Field(default_factory=list)
    total: int
    limit: int
    offset: int


class AdminTenantRuntimeSummary(BaseModel):
    tenant_id: str
    name: str
    workspace_id: str
    plan: Literal["starter", "business", "enterprise"] = "enterprise"
    status: Literal["active", "suspended"] = "active"
    document_count: int = 0
    chunk_count: int = 0
    parsed_documents: int = 0
    partial_documents: int = 0
    operational_documents: int = 0
    operational_chunks: int = 0
    operational_retention_mode: Literal["keep_latest", "keep_all"] = "keep_latest"
    operational_retention_hours: int = 24
    operational_cleanup_eligible_documents: int = 0
    operational_cleanup_eligible_chunks: int = 0
    operational_cleanup_oldest_created_at: Optional[str] = None
    qdrant_status: Literal["ok", "error"] = "error"
    qdrant_points: Optional[int] = None
    qdrant_canonical_points: int = 0
    qdrant_noncanonical_points: int = 0
    qdrant_noncanonical_documents: int = 0
    alerts_active: int = 0
    critical_alerts: int = 0
    audit_events_30d: int = 0
    repair_events_30d: int = 0
    readiness_score: int = 0
    readiness_status: Literal["ready", "stable", "at_risk", "critical"] = "critical"
    readiness_reasons: list[str] = Field(default_factory=list)
    groundedness_rate: float = 0.0
    no_context_rate: float = 0.0
    evaluation_hit_rate_top5: float = 0.0
    p95_latency_ms: float = 0.0
    latest_query_at: Optional[str] = None
    latest_ingestion_at: Optional[str] = None
    latest_evaluation_at: Optional[str] = None


class AdminRuntimeResponse(BaseModel):
    items: list[AdminTenantRuntimeSummary] = Field(default_factory=list)
    total: int
    qdrant_collection: str
    generated_at: str


class AdminQdrantPruneResponse(BaseModel):
    workspace_id: str
    deleted_points: int = 0
    deleted_documents: int = 0
    deleted_document_ids: list[str] = Field(default_factory=list)
    canonical_points_remaining: int = 0
    total_points_remaining: int = 0
    generated_at: str


class AdminOperationalCleanupResponse(BaseModel):
    workspace_id: str
    retention_mode: Literal["keep_latest", "keep_all"] = "keep_latest"
    retention_hours: int = 24
    deleted_documents: int = 0
    deleted_chunks: int = 0
    deleted_document_ids: list[str] = Field(default_factory=list)
    remaining_operational_documents: int = 0
    remaining_operational_chunks: int = 0
    generated_at: str


class ObservabilityAlert(BaseModel):
    name: str
    severity: Literal["critical", "high", "medium"]
    status: Literal["ok", "firing"]
    message: str
    window: str
    value: Optional[float | int | str] = None
    threshold: Optional[float | int | str] = None


class ObservabilityAlertsResponse(BaseModel):
    items: list[ObservabilityAlert] = Field(default_factory=list)
    total_active: int = 0
    workspace_id: Optional[str] = None
    period_days: int = 1
    generated_at: str


class ObservabilitySLOItem(BaseModel):
    name: str
    description: str
    category: Literal["availability", "latency", "quality", "reliability"]
    unit: str
    window: str
    current_value: float
    target_value: float
    alert_threshold: Optional[float] = None
    comparator: Literal["at_most", "at_least"]
    healthy: bool
    status: Literal["ok", "breach"]
    message: str


class ObservabilitySLOResponse(BaseModel):
    items: list[ObservabilitySLOItem] = Field(default_factory=list)
    total_breaches: int = 0
    workspace_id: Optional[str] = None
    generated_at: str


class TraceSpanEvent(BaseModel):
    name: str
    attributes: dict = Field(default_factory=dict)


class TraceSpanRecord(BaseModel):
    name: str
    trace_id: str
    span_id: str
    parent_id: Optional[str] = None
    kind: str
    status: str
    workspace_id: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_ms: Optional[float] = None
    attributes: dict = Field(default_factory=dict)
    events: list[TraceSpanEvent] = Field(default_factory=list)


class ObservabilityTraceResponse(BaseModel):
    items: list[TraceSpanRecord] = Field(default_factory=list)
    total: int = 0
    workspace_id: Optional[str] = None
    generated_at: str


class AuditLogEvent(BaseModel):
    timestamp: str
    type: Literal["audit"] = "audit"
    request_id: Optional[str] = None
    workspace_id: str
    total_documents: int = 0
    total_with_issues: int = 0
    total_ok: int = 0
    by_issue_type: dict[str, int] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)


class AuditLogListResponse(BaseModel):
    items: list[AuditLogEvent] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
    workspace_id: Optional[str] = None


class RepairLogEvent(BaseModel):
    timestamp: str
    type: Literal["repair"] = "repair"
    request_id: Optional[str] = None
    document_id: str
    workspace_id: str
    success: bool
    chunks_reindexed: int = 0
    embeddings_valid: bool = False
    qdrant_restored: bool = False
    message: str = ""


class RepairLogListResponse(BaseModel):
    items: list[RepairLogEvent] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
    workspace_id: Optional[str] = None


class EnterpriseTenantCreate(BaseModel):
    tenant_id: str
    name: str
    workspace_id: str
    plan: Literal["starter", "business", "enterprise"] = "starter"
    status: Literal["active", "suspended"] = "active"
    operational_retention_mode: Literal["keep_latest", "keep_all"] = "keep_latest"
    operational_retention_hours: int = 24


class EnterpriseTenantUpdate(BaseModel):
    name: Optional[str] = None
    workspace_id: Optional[str] = None
    plan: Optional[Literal["starter", "business", "enterprise"]] = None
    status: Optional[Literal["active", "suspended"]] = None
    operational_retention_mode: Optional[Literal["keep_latest", "keep_all"]] = None
    operational_retention_hours: Optional[int] = None


class EnterpriseUserRecord(BaseModel):
    user_id: str
    name: str
    email: str
    role: Literal["admin", "operator", "viewer"]
    tenant_id: str
    status: Literal["active", "invited", "disabled"] = "active"


class EnterpriseUserCreate(BaseModel):
    user_id: str
    name: str
    email: str
    password: str
    role: Literal["admin", "operator", "viewer"] = "viewer"
    tenant_id: str = "default"
    status: Literal["active", "invited", "disabled"] = "invited"


class EnterpriseUserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[Literal["admin", "operator", "viewer"]] = None
    tenant_id: Optional[str] = None
    status: Optional[Literal["active", "invited", "disabled"]] = None
    approve_sensitive_change: Optional[bool] = None
    approval_ticket: Optional[str] = None


class NormalizedDocument(BaseModel):
    """Internal JSON representation of a parsed document."""

    document_id: str
    source_type: str
    filename: str
    workspace_id: str
    created_at: str
    pages: list[dict] = Field(default_factory=list)
    sections: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    raw_json_path: str = ""


# ─── Chunk ───────────────────────────────────────────────────


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    workspace_id: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    page_hint: Optional[int] = None
    strategy: str = "recursive"
    chunk_size_chars: int = 0
    created_at: str


# ─── Retrieval ───────────────────────────────────────────────


RetrievalProfile = Literal[
    "hybrid",
    "hyde_hybrid",
    "semantic_hybrid",
    "semantic_hyde_hybrid",
]


class SearchRequest(BaseModel):
    query: str
    workspace_id: str = "default"
    top_k: int = 5
    threshold: float = 0.70
    retrieval_mode: str = "híbrida"
    filters: Optional[dict] = None
    include_raw_scores: bool = False
    # Optional: None = use global RERANKING_ENABLED config, True = force on, False = force off
    reranking: Optional[bool] = None
    # Optional: override global RERANKING_METHOD ("bm25f", "neural", "none")
    reranking_method: Optional[str] = None
    # Query expansion mode: "off" = never, "always" = always when enabled, "adaptive" = use heuristic
    # None = use global QUERY_EXPANSION_ENABLED config
    query_expansion_mode: Optional[Literal["off", "always", "adaptive"]] = None
    retrieval_profile: Optional[RetrievalProfile] = None


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    score: float
    page_hint: Optional[int] = None
    source: str
    document_filename: Optional[str] = None
    workspace_id: Optional[str] = None
    source_type: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    workspace_id: str
    results: list[SearchResultItem]
    total_candidates: int
    low_confidence: bool
    retrieval_time_ms: int
    method: str = "híbrida"
    scores_breakdown: Optional[dict] = None
    reranking_applied: bool = False
    reranking_method: Optional[str] = None
    query_expansion_applied: bool = False
    query_expansion_method: Optional[str] = None
    query_expansion_fallback: bool = False
    query_expansion_requested: bool = False
    query_expansion_mode: Optional[Literal["off", "always", "adaptive"]] = None
    query_expansion_decision_reason: Optional[str] = None
    retrieval_profile: Optional[RetrievalProfile] = None


# ─── Query / Answer ─────────────────────────────────────────


class QueryRequest(BaseModel):
    query: str
    workspace_id: str = "default"
    top_k: int = 5
    threshold: float = 0.70
    stream: bool = False
    model: Optional[str] = None
    reranking: Optional[bool] = None  # None = use global config, True/False override
    reranking_method: Optional[str] = None  # None = use global RERANKING_METHOD, or "bm25f"/"neural"/"none"
    # "off" = never, "always" = always when enabled, "adaptive" = use heuristic
    # None = use global config
    # Deprecated: query_expansion=True/False still works as before (maps to always/off)
    query_expansion_mode: Optional[Literal["off", "always", "adaptive"]] = None
    query_expansion: Optional[bool] = None  # Deprecated: use query_expansion_mode instead
    retrieval_profile: Optional[RetrievalProfile] = None


class GroundingReport(BaseModel):
    grounded: bool
    citation_coverage: float = 0.0
    uncited_claims: list[str] = Field(default_factory=list)
    needs_review: bool = False
    reason: Optional[str] = None


class Citation(BaseModel):
    chunk_id: str
    document_id: Optional[str] = None
    document_filename: Optional[str] = None
    page: Optional[int] = None
    text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    chunks_used: list[str]
    citations: list[Citation] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]
    grounded: bool
    grounding: Optional[GroundingReport] = None  # Grounding verification details
    citation_coverage: float = 0.0  # 0.0-1.0
    low_confidence: bool
    retrieval: dict
    latency_ms: int
    query_expansion_applied: bool = False
    query_expansion_method: Optional[str] = None
    query_expansion_fallback: bool = False
    query_expansion_requested: bool = False
    query_expansion_mode: Optional[Literal["off", "always", "adaptive"]] = None
    query_expansion_decision_reason: Optional[str] = None
    retrieval_profile: Optional[RetrievalProfile] = None


# ─── Evaluation ──────────────────────────────────────────────


class EvaluationQuestion(BaseModel):
    id: int
    pergunta: str
    document_id: str
    document_filename: Optional[str] = None
    trecho_esperado: str
    resposta_esperada: str
    dificuldade: Literal["easy", "medium", "hard"] = "medium"
    categoria: Literal["fato", "procedimento", "política", "detalhes"] = "procedimento"
    workspace_id: str = "default"
    query_expansion: Optional[bool] = None  # override global expansion for this question


class Dataset(BaseModel):
    dataset_id: str
    version: str = "1.0"
    questions: list[EvaluationQuestion]


class EvaluationResult(BaseModel):
    question_id: str
    pergunta: str
    hit_top_1: bool
    hit_top_3: bool
    hit_top_5: bool
    retrieved_documents: list[str]
    correct_document_id: Optional[str] = None
    best_score: Optional[float] = None
    best_score_rank: Optional[int] = None
    judge_score: Optional[float] = None
    grounded: bool = False
    citation_coverage: float = 0.0
    low_confidence: bool = False
    retrieval_low_confidence: bool = False
    judge_groundedness: Optional[str] = None
    needs_review: bool = False
    reranking_applied: bool = False
    reranking_method: Optional[str] = None


class EvaluationResponse(BaseModel):
    evaluation_id: str
    workspace_id: str
    total_questions: int
    hit_rate_top_1: float
    hit_rate_top_3: float
    hit_rate_top_5: float
    avg_latency_ms: float
    avg_score: float = 0.0
    low_confidence_rate: float
    retrieval_low_confidence_rate: float = 0.0
    groundedness_rate: float
    observed_groundedness_rate: float = 0.0
    judge_score: Optional[float] = None
    judged_questions: int = 0
    judge_groundedness_rate: Optional[float] = None
    judge_needs_review_rate: Optional[float] = None
    flagged_for_review_count: int
    duration_seconds: float
    by_difficulty: dict = Field(default_factory=dict)
    by_category: dict = Field(default_factory=dict)
    question_results: list[EvaluationResult] = Field(default_factory=list)
    reranking_applied: bool = False
    reranking_method: Optional[str] = None


class VariantResult(BaseModel):
    """Metrics for a single A/B variant."""
    variant_name: str
    reranking_applied: bool
    reranking_method: Optional[str] = None
    query_expansion_applied: bool = False
    query_expansion_method: Optional[str] = None
    total_questions: int
    hit_rate_top_1: float
    hit_rate_top_3: float
    hit_rate_top_5: float
    avg_latency_ms: float
    avg_score: float = 0.0
    low_confidence_rate: float
    judge_score: Optional[float] = None
    duration_seconds: float


class ABEvaluationResponse(BaseModel):
    """Structured A/B comparison result."""
    evaluation_id: str
    workspace_id: str
    baseline: VariantResult
    variant: VariantResult
    delta_hit_at_1: float = 0.0
    delta_hit_at_3: float = 0.0
    delta_hit_at_5: float = 0.0
    delta_avg_latency_ms: float = 0.0
    delta_avg_score: float = 0.0
    delta_low_confidence_rate: float = 0.0
    winner: Optional[Literal["baseline", "variant", "tie"]] = None


class ChunkingVariantResult(BaseModel):
    """Metrics for a single chunking strategy in a chunking A/B comparison."""
    strategy: Literal["recursive", "semantic"]
    chunk_count: int
    hit_rate_top_1: float
    hit_rate_top_3: float
    hit_rate_top_5: float
    avg_latency_ms: float
    avg_score: float = 0.0
    low_confidence_rate: float
    judge_score: Optional[float] = None
    duration_seconds: float


class ChunkingABResponse(BaseModel):
    """Structured A/B comparison result for chunking strategies."""
    evaluation_id: str
    workspace_id: str
    document_id: str
    baseline: ChunkingVariantResult
    variant: ChunkingVariantResult
    delta_hit_at_1: float = 0.0
    delta_hit_at_3: float = 0.0
    delta_hit_at_5: float = 0.0
    delta_avg_latency_ms: float = 0.0
    delta_avg_score: float = 0.0
    delta_low_confidence_rate: float = 0.0
    winner: Optional[Literal["baseline", "variant", "tie"]] = None
    corpus_restored: bool = True
    # Embedding restore quality:
    #   "original" — backup had valid embeddings and they were used as-is
    #   "regenerated" — backup had no/invalid embeddings; were regenerated from text
    #   "degraded_zero_fallback" — backup had no/invalid embeddings AND regeneration API
    #                              also failed; Qdrant indexed with zero vectors
    embedding_status: Literal["original", "regenerated", "degraded_zero_fallback"] = "original"


class QueryLogItem(BaseModel):
    timestamp: str
    type: str = "query"
    request_id: Optional[str] = None
    workspace_id: str
    query: str
    answer: str
    confidence: Literal["high", "medium", "low"]
    grounded: bool
    low_confidence: bool
    chunks_used_count: int
    chunk_ids: list[str] = Field(default_factory=list)
    retrieval_time_ms: int
    total_latency_ms: int
    results_count: int
    citation_coverage: float = 0.0
    top_result_score: Optional[float] = None
    threshold: Optional[float] = None
    hit: Optional[bool] = None
    grounding_reason: Optional[str] = None
    uncited_claims_count: int = 0
    needs_review: Optional[bool] = None
    reranking_applied: bool = False
    reranking_method: Optional[str] = None
    candidate_count: Optional[int] = None
    query_expansion_applied: bool = False
    query_expansion_method: Optional[str] = None
    query_expansion_fallback: bool = False
    query_expansion_requested: bool = False
    query_expansion_mode: Optional[Literal["off", "always", "adaptive"]] = None
    query_expansion_decision_reason: Optional[str] = None
    expansion_latency_ms: int = 0


class QueryExpansionVariantResult(BaseModel):
    """Metrics for a single query expansion variant."""
    variant_name: str
    query_expansion_applied: bool
    query_expansion_method: Optional[str] = None
    total_questions: int
    hit_rate_top_1: float
    hit_rate_top_3: float
    hit_rate_top_5: float
    avg_latency_ms: float
    avg_score: float = 0.0
    low_confidence_rate: float
    judge_score: Optional[float] = None
    duration_seconds: float


class QueryExpansionABResponse(BaseModel):
    """Structured A/B comparison for query expansion (baseline vs variant with expansion)."""
    evaluation_id: str
    workspace_id: str
    baseline: QueryExpansionVariantResult
    variant: QueryExpansionVariantResult
    delta_hit_at_1: float = 0.0
    delta_hit_at_3: float = 0.0
    delta_hit_at_5: float = 0.0
    delta_avg_latency_ms: float = 0.0
    delta_avg_score: float = 0.0
    delta_low_confidence_rate: float = 0.0
    winner: Optional[Literal["baseline", "variant", "tie"]] = None


class QueryLogResponse(BaseModel):
    items: list[QueryLogItem] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
    workspace_id: str
