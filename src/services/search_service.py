"""
Search Service — orchestrates retrieval + answer generation
"""
import time
import json
from datetime import datetime, timezone

from models.schemas import QueryRequest, QueryResponse, SearchRequest, SearchResponse, Citation, GroundingReport
from services.vector_service import search_hybrid
from services.llm_service import generate_answer, estimate_answer_cost
from services.grounding_service import verify_grounding, enrich_citations_with_filename
from core.config import LOGS_DIR
from services.telemetry_service import get_telemetry
from services.request_context import get_request_id
from core.config import QUERY_EXPANSION_ENABLED


HYDE_SYSTEM_PROMPT = "Você é um assistente que escreve respostas factuais breves para ajudar na busca de documentos."
HYDE_USER_PROMPT_TEMPLATE = "Given the question below, write a brief factual answer (2-3 sentences) that would help retrieve relevant documents. Answer ONLY with facts — do not speculate beyond what is directly implied by the question.\n\nQuestion: {query}\nAnswer:"
LOW_CONFIDENCE_GROUNDING_OVERRIDE_THRESHOLD = 0.8
RETRIEVAL_PROFILE_TO_EXPANSION_MODE = {
    "hybrid": "off",
    "hyde_hybrid": "always",
    "semantic_hybrid": "off",
    "semantic_hyde_hybrid": "always",
}
SEMANTIC_RETRIEVAL_PROFILES = {"semantic_hybrid", "semantic_hyde_hybrid"}

# Adaptive expansion: patterns that suggest a specific lookup (skip expansion)
_SPECIFIC_LOOKUP_PATTERNS = [
    r"\b\d{4,}\b",        # long numbers (years, IDs, phone numbers)
    r"\b\d+/\d+\b",       # dates or ratios
    r"\b[A-Z]{2,}\d+\b",  # uppercase code prefixes followed by digits (e.g. PROJ123)
    r"\b(art\.?|artigo|nº|número|protocolo|ref\.?|processo)\b",  # specific reference terms
]


def _should_expand_adaptive(query: str) -> tuple[bool, str]:
    """
    Adaptive heuristic: decide whether HyDE expansion should run for a given query.

    Returns (should_expand: bool, reason: str).
    The reason string is one of the decision labels below, used for observability.

    Heuristic rules (evaluated in order):
    1. Skip if query looks like a specific identifier/lookup:
       - contains a number ≥ 4 digits, date-like pattern, uppercase code, or reference term
    2. Expand if query is short or ambiguous:
       - fewer than 3 words, or fewer than 12 chars
       - is a natural language question (contains ? or interrogative words)
    3. Default: expand (better recall for open queries)
    """
    import re

    # Rule 1: specific lookup patterns → skip
    for pattern in _SPECIFIC_LOOKUP_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return False, "specific_lookup"

    # Rule 2a: very short query → expand
    words = query.strip().split()
    if len(words) < 3:
        return True, "short_query"

    # Rule 2b: very short char length → expand
    if len(query.strip()) < 12:
        return True, "short_query"

    # Rule 3: natural language question → expand
    question_words = {"o que", "o quê", "quem", "quando", "onde", "como", "por quê",
                      "porque", "qual", "quais", "existe", "existem", "o que é", "quem é",
                      "what", "who", "when", "where", "how", "why", "which", "does",
                      "is there", "are there", "can i", "posso", "pode", "existe"}
    q_lower = query.lower().strip()
    if "?" in q_lower or any(q_lower.startswith(w) or f" {w} " in f" {q_lower} " for w in question_words):
        return True, "natural_language_question"

    # Default: expand for general queries
    return True, "general_query"


def _expand_query(query: str) -> tuple[str, int]:
    """
    HyDE-like query expansion: generate a short hypothetical answer
    and append it to the original query to improve dense retrieval.

    Uses the existing generate_answer infrastructure with a minimal prompt.
    Returns (expanded_query, latency_ms). On any failure returns ("", 0).
    Latency is in milliseconds.
    """
    import time
    from services.llm_service import generate_answer

    hyde_chunks = [{"text": "", "chunk_id": "hyde", "score": 0.0}]
    start = time.time()
    try:
        answer_text, _, _ = generate_answer(
            query=query,
            chunks=hyde_chunks,
            system_prompt=HYDE_SYSTEM_PROMPT,
        )
        latency_ms = int((time.time() - start) * 1000)
        if not answer_text or len(answer_text.strip()) < 10:
            return "", latency_ms
        return f"{query} {answer_text.strip()}", latency_ms
    except Exception:
        return "", 0


def _finalize_low_confidence(
    retrieval_low_confidence: bool,
    has_results: bool,
    grounding_result: GroundingReport | None,
) -> tuple[bool, str]:
    """
    Convert retrieval heuristics into the final user-facing low_confidence signal.

    Retrieval may be conservative. If chunks were found and the generated answer
    ends up grounded with strong citation coverage, the final signal is cleared.
    """
    if not has_results:
        return True, "no_results"
    if not retrieval_low_confidence:
        return False, "retrieval_ok"
    if grounding_result and grounding_result.grounded and not grounding_result.needs_review:
        if grounding_result.citation_coverage >= LOW_CONFIDENCE_GROUNDING_OVERRIDE_THRESHOLD:
            return False, "grounding_override"
    return True, "retrieval_low_confidence"


def _resolve_search_profile(
    retrieval_profile: str | None,
    query_expansion_mode: str | None,
    default_query_expansion_mode: str,
) -> tuple[str | None, str, bool]:
    """Map retrieval profile to concrete retrieval knobs while preserving legacy defaults."""
    if retrieval_profile:
        return (
            retrieval_profile,
            RETRIEVAL_PROFILE_TO_EXPANSION_MODE[retrieval_profile],
            retrieval_profile in SEMANTIC_RETRIEVAL_PROFILES,
        )
    return None, (query_expansion_mode or default_query_expansion_mode), False


def _merge_retrieval_filters(filters: dict | None, semantic_only: bool) -> dict | None:
    merged = dict(filters or {})
    if semantic_only:
        merged["strategy"] = "semantic"
    return merged or None


def execute_search(
    request: SearchRequest,
    *,
    default_query_expansion_mode: str = "off",
) -> SearchResponse:
    """
    Execute retrieval for both /search and /query using the same profile contract.

    `/search` preserves its historical default of expansion disabled.
    `/query` can still opt into adaptive expansion by passing a different default.
    """
    (
        effective_profile,
        expansion_mode,
        semantic_only,
    ) = _resolve_search_profile(
        request.retrieval_profile,
        request.query_expansion_mode,
        default_query_expansion_mode,
    )

    expansion_requested = False
    expansion_decision_reason: str | None = None
    expansion_applied = False
    expansion_fallback = False
    expansion_method: str | None = None
    search_query = request.query

    if expansion_mode == "always":
        expansion_requested = True
        expansion_decision_reason = "always_mode"
        expanded, _ = _expand_query(request.query)
        if expanded:
            search_query = expanded
            expansion_applied = True
            expansion_method = "hyde"
        else:
            expansion_fallback = True
    elif expansion_mode == "adaptive":
        should_expand, heuristic_reason = _should_expand_adaptive(request.query)
        if should_expand:
            expansion_requested = True
            expansion_decision_reason = f"adaptive:{heuristic_reason}"
            expanded, _ = _expand_query(request.query)
            if expanded:
                search_query = expanded
                expansion_applied = True
                expansion_method = "hyde"
            else:
                expansion_fallback = True
        else:
            expansion_decision_reason = f"adaptive:{heuristic_reason}"

    resolved_request = request.model_copy(
        update={
            "query": search_query,
            "filters": _merge_retrieval_filters(request.filters, semantic_only),
        }
    )
    search_resp = search_hybrid(resolved_request)
    search_resp.query_expansion_applied = expansion_applied
    search_resp.query_expansion_method = expansion_method
    search_resp.query_expansion_fallback = expansion_fallback
    search_resp.query_expansion_requested = expansion_requested
    search_resp.query_expansion_mode = expansion_mode
    search_resp.query_expansion_decision_reason = expansion_decision_reason
    search_resp.retrieval_profile = effective_profile
    return search_resp


def search_and_answer(
    request: QueryRequest
) -> QueryResponse:
    """
    Full pipeline:
    1. Hybrid search (dense + sparse + RRF)
    2. If low confidence → return low confidence response
    3. Generate answer using LLM
    4. Verify grounding (citations coverage)
    5. Log query
    6. Return response
    """
    start_total = time.time()

    # ── Step 0/1: Retrieval profile + optional query expansion ─────────────
    if request.query_expansion_mode is not None:
        expansion_mode_override = request.query_expansion_mode
    elif request.query_expansion is not None:
        expansion_mode_override = "always" if request.query_expansion else "off"
    else:
        expansion_mode_override = None

    search_req = SearchRequest(
        query=request.query,
        workspace_id=request.workspace_id,
        top_k=request.top_k,
        threshold=request.threshold,
        retrieval_mode="híbrida",
        reranking=request.reranking,
        reranking_method=request.reranking_method,
        query_expansion_mode=expansion_mode_override,
        retrieval_profile=request.retrieval_profile,
    )
    search_resp = execute_search(
        search_req,
        default_query_expansion_mode="adaptive" if QUERY_EXPANSION_ENABLED else "off",
    )
    expansion_requested = search_resp.query_expansion_requested
    expansion_decision_reason = search_resp.query_expansion_decision_reason
    expansion_applied = search_resp.query_expansion_applied
    expansion_fallback = search_resp.query_expansion_fallback
    expansion_method = search_resp.query_expansion_method
    expansion_mode = search_resp.query_expansion_mode
    effective_profile = search_resp.retrieval_profile

    # ── Step 2: Build answer from chunks ─────────────────────
    chunks_data = []
    for result in search_resp.results:
        chunks_data.append({
            "chunk_id": result.chunk_id,
            "document_id": result.document_id,
            "document_filename": result.document_filename,
            "text": result.text,
            "score": result.score,
            "page_hint": result.page_hint,
            "source": result.source
        })

    retrieval_low_confidence = bool(search_resp.low_confidence)

    # ── Step 3: Generate answer ───────────────────────────────
    if not search_resp.results:
        answer = "Não tenho informações suficientes para responder a esta pergunta de forma precisa."
        confidence = "low"
        grounded = False
        chunks_used = []
        citations = []
        grounding_result = GroundingReport(
            grounded=False,
            citation_coverage=0.0,
            uncited_claims=[],
            needs_review=True,
            reason="No results retrieved or low confidence",
        )
        citation_coverage = 0.0
        final_low_confidence = True
        low_confidence_reason = "no_results"
    else:
        answer_text, chunk_ids, llm_latency = generate_answer(
            query=request.query,
            chunks=chunks_data
        )
        answer = answer_text
        chunks_used = chunk_ids
        # RRF scores are rank-based, not probabilities
        # low_confidence already handles quality gating, so here we just use "high"
        confidence = "high"

        # Build citations with full text (not truncated for internal use)
        citations = []
        for c in chunks_data:
            citations.append(Citation(
                chunk_id=c["chunk_id"],
                document_id=c.get("document_id"),
                document_filename=c.get("document_filename"),
                page=c.get("page_hint"),
                text=c["text"],
                score=c["score"]
            ))

        document_filenames = {
            c["document_id"]: c.get("document_filename")
            for c in chunks_data
            if c.get("document_id") and c.get("document_filename")
        }
        citations = enrich_citations_with_filename(citations, document_filenames)

        # ── Step 4: Verify grounding ─────────────────────────
        grounding_result = GroundingReport(**verify_grounding(answer, citations))
        grounded = grounding_result.grounded
        citation_coverage = grounding_result.citation_coverage
        final_low_confidence, low_confidence_reason = _finalize_low_confidence(
            retrieval_low_confidence=retrieval_low_confidence,
            has_results=bool(search_resp.results),
            grounding_result=grounding_result,
        )
        confidence = "medium" if final_low_confidence else ("medium" if retrieval_low_confidence else "high")

        # Truncate citation text for response (keep first 300 chars)
        citations = [
            Citation(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_filename=c.document_filename,
                page=c.page,
                text=c.text[:300] + "..." if len(c.text) > 300 else c.text,
                score=c.score
            )
            for c in citations
        ]

    total_latency = int((time.time() - start_total) * 1000)

    # ── Step 5: Log query ──────────────────────────────────────
    _log_query({
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "workspace_id": request.workspace_id,
        "query": request.query,
        "answer": answer,
        "confidence": confidence,
        "grounded": grounded,
        "chunks_used": chunks_used,
        "citation_coverage": citation_coverage,
        "low_confidence": final_low_confidence,
        "retrieval_low_confidence": retrieval_low_confidence,
        "retrieval_time_ms": search_resp.retrieval_time_ms,
        "total_latency_ms": total_latency,
        "results_count": len(search_resp.results),
        "top_result_score": search_resp.results[0].score if search_resp.results else None,
        "threshold": request.threshold,
        "grounding_reason": (
            f"{grounding_result.reason}; low_confidence={low_confidence_reason}"
            if grounding_result and grounding_result.reason
            else f"low_confidence={low_confidence_reason}"
        ),
        "uncited_claims_count": len(grounding_result.uncited_claims) if grounding_result else 0,
        "needs_review": grounding_result.needs_review if grounding_result else None,
        "reranking_applied": search_resp.reranking_applied,
        "reranking_method": search_resp.reranking_method,
        "candidate_count": search_resp.total_candidates,
        "query_expansion_applied": expansion_applied,
        "query_expansion_method": expansion_method,
        "query_expansion_fallback": expansion_fallback,
        "query_expansion_requested": expansion_requested,
        "query_expansion_mode": expansion_mode,
        "query_expansion_decision_reason": expansion_decision_reason,
        "retrieval_profile": effective_profile,
    })

    return QueryResponse(
        answer=answer,
        chunks_used=chunks_used,
        citations=citations,
        confidence=confidence,
        grounded=grounded,
        grounding=grounding_result,
        citation_coverage=citation_coverage,
        low_confidence=final_low_confidence,
        retrieval={
            **search_resp.model_dump(),
            "retrieval_low_confidence": retrieval_low_confidence,
            "low_confidence_reason": low_confidence_reason,
        },
        latency_ms=total_latency,
        query_expansion_applied=expansion_applied,
        query_expansion_method=expansion_method,
        query_expansion_fallback=expansion_fallback,
        query_expansion_requested=expansion_requested,
        query_expansion_mode=expansion_mode,
        query_expansion_decision_reason=expansion_decision_reason,
        retrieval_profile=effective_profile,
    )


def _log_query(log_entry: dict):
    """Log query to JSON Lines file."""
    try:
        telemetry = get_telemetry()
        telemetry.log_query(
            query=log_entry.get("query", ""),
            workspace_id=log_entry.get("workspace_id", "default"),
            answer=log_entry.get("answer", ""),
            confidence=log_entry.get("confidence", "low"),
            grounded=log_entry.get("grounded", False),
            chunks_used=log_entry.get("chunks_used", []),
            retrieval_time_ms=log_entry.get("retrieval_time_ms", 0),
            total_latency_ms=log_entry.get("total_latency_ms", 0),
            low_confidence=log_entry.get("low_confidence", False),
            results_count=log_entry.get("results_count", 0),
            citation_coverage=log_entry.get("citation_coverage", 0.0),
            top_result_score=log_entry.get("top_result_score"),
            threshold=log_entry.get("threshold"),
            grounding_reason=log_entry.get("grounding_reason"),
            uncited_claims_count=log_entry.get("uncited_claims_count", 0),
            needs_review=log_entry.get("needs_review"),
            request_id=log_entry.get("request_id") or get_request_id(),
            reranking_applied=log_entry.get("reranking_applied", False),
            reranking_method=log_entry.get("reranking_method"),
            candidate_count=log_entry.get("candidate_count"),
            query_expansion_applied=log_entry.get("query_expansion_applied", False),
            query_expansion_method=log_entry.get("query_expansion_method"),
            query_expansion_fallback=log_entry.get("query_expansion_fallback", False),
            query_expansion_requested=log_entry.get("query_expansion_requested", False),
            expansion_latency_ms=log_entry.get("expansion_latency_ms", 0),
            query_expansion_mode=log_entry.get("query_expansion_mode"),
            query_expansion_decision_reason=log_entry.get("query_expansion_decision_reason"),
        )
    except Exception:
        pass  # Non-critical
