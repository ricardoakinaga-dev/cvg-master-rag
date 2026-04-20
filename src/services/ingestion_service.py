"""
Ingestion Service — orchestrates upload → parse → chunk → index
"""
import os
import json
import uuid
import time as time_module
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional

from models.schemas import (
    DocumentUploadResponse, DocumentMetadata,
    NormalizedDocument, Chunk, SearchRequest
)
from services.document_parser import parse_document, save_raw_json, ParseError, UnsupportedFormatError
from services.chunker import recursive_chunk, semantic_chunk
from services.embedding_service import get_embeddings_batch
from services.vector_service import index_chunks, delete_document_chunks
from core.config import DOCUMENTS_DIR, CHUNKS_DIR, CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_DIM
from scripts.corpus_utils import canonical_document_ids
from services.admin_service import get_tenant_by_workspace


class IngestionError(Exception):
    pass


VALID_CHUNKING_STRATEGIES = {"recursive", "semantic"}


def _is_operational_upload(file_path: Path) -> bool:
    """Uploads staged via the API live under a workspace uploads/ directory."""
    return "/uploads/" in str(file_path).replace("\\", "/")


def _tenant_retention_policy(workspace_id: str) -> tuple[str, int]:
    """Return the operational upload retention policy for a workspace."""
    tenant = get_tenant_by_workspace(workspace_id) or {}
    mode = tenant.get("operational_retention_mode", "keep_latest")
    if mode not in {"keep_latest", "keep_all"}:
        mode = "keep_latest"
    try:
        hours = int(tenant.get("operational_retention_hours", 24) or 24)
    except Exception:
        hours = 24
    return mode, max(1, hours)


def _prune_previous_operational_uploads(workspace_id: str, filename: str, keep_document_id: str) -> int:
    """Keep only the newest operational upload revision for a given filename/workspace."""
    doc_dir = DOCUMENTS_DIR / workspace_id
    if not doc_dir.exists():
        return 0

    try:
        canonical_ids = canonical_document_ids(workspace_id)
    except Exception:
        canonical_ids = set()
    retention_mode, retention_hours = _tenant_retention_policy(workspace_id)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)

    removed = 0
    candidates: list[tuple[str, Path, Path, str]] = []
    for raw_file in sorted(doc_dir.glob("*_raw.json")):
        document_id = raw_file.stem.removesuffix("_raw")
        if document_id == keep_document_id:
            continue
        if document_id in canonical_ids:
            continue
        try:
            payload = json.loads(raw_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        raw_json_path = str(payload.get("raw_json_path", "") or "").replace("\\", "/")
        if "/uploads/" not in raw_json_path:
            continue
        created_at = str(payload.get("created_at", "") or "")
        should_prune = False
        if retention_mode == "keep_latest" and payload.get("filename") == filename:
            should_prune = True
        else:
            try:
                created_at_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                should_prune = created_at_dt < cutoff
            except Exception:
                should_prune = False
        if should_prune:
            candidates.append((document_id, raw_file, doc_dir / f"{document_id}_chunks.json", created_at))

    candidates.sort(key=lambda item: item[3], reverse=True)
    for document_id, raw_file, chunks_file, _created_at in candidates:
        try:
            delete_document_chunks(document_id)
        except Exception:
            pass
        try:
            raw_file.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            chunks_file.unlink(missing_ok=True)
        except Exception:
            pass
        removed += 1
    return removed


def _embedding_is_valid(emb: object) -> bool:
    """Return True if emb is a list of the correct embedding dimension."""
    return (
        isinstance(emb, list)
        and len(emb) == EMBEDDING_DIM
        and all(isinstance(x, (int, float)) for x in emb)
    )


def _restore_embeddings_if_needed(chunks: list[dict]) -> tuple[list[dict], bool]:
    """
    Validate embeddings per-chunk; recover from Qdrant or regenerate if missing/invalid.

    Recovery priority:
      1. Already valid embeddings in chunk dicts → return as-is ("original")
      2. Embeddings in Qdrant (read by chunk_id) → use directly (no API call, "original")
      3. get_embeddings_batch via API → if succeeds ("regenerated"), if fails → zeros

    Per-chunk validation: each chunk must have a valid embedding field (list of
    EMBEDDING_DIM floats). If ANY chunk is invalid or missing, ALL chunks are
    recovered or regenerated.

    Count mismatch protection: if get_embeddings_batch returns a different count
    than the number of chunks, raise RuntimeError — no silent truncation or padding.

    Returns (updated_chunks, were_regenerated):
      - updated_chunks: chunks with valid embeddings (Qdrant or regenerated)
      - were_regenerated: True if embeddings were regenerated via API
                           False if they came from Qdrant or were already valid
    """
    if not chunks:
        return chunks, False

    # Per-chunk validation
    all_valid = all(_embedding_is_valid(c.get("embedding")) for c in chunks)
    if all_valid:
        return chunks, False  # nothing to do

    # At least one chunk is invalid or missing — try Qdrant first (no API needed)
    chunk_ids = [c.get("chunk_id") for c in chunks]
    workspace_id = chunks[0].get("workspace_id", "default")

    qdrant_embeddings: dict[str, list[float]] = {}
    try:
        qdrant_embeddings = _get_embeddings_from_qdrant(chunk_ids, workspace_id)
    except Exception:
        # Qdrant read failed — will fall through to API regeneration
        qdrant_embeddings = {}

    # Classify each chunk: has_valid_qdrant_emb | needs_api | already_valid
    chunk_indices_from_qdrant: list[int] = []   # indices whose Qdrant embedding is valid
    chunk_indices_needed: list[tuple[int, dict]] = []  # (index, chunk) that need API

    for i, c in enumerate(chunks):
        qdrant_emb = qdrant_embeddings.get(c.get("chunk_id"))
        if qdrant_emb is not None and _embedding_is_valid(qdrant_emb):
            chunk_indices_from_qdrant.append(i)
        else:
            chunk_indices_needed.append((i, c))

    if not chunk_indices_needed:
        # All embeddings found in Qdrant and all are valid — use them directly
        updated_chunks = []
        for i, c in enumerate(chunks):
            c_copy = dict(c)
            c_copy["embedding"] = qdrant_embeddings[c["chunk_id"]]
            updated_chunks.append(c_copy)
        return updated_chunks, False  # not regenerated, came from valid Qdrant embeddings

    # Some chunks are missing or have invalid embeddings — try API for those
    # Valid Qdrant embeddings are preserved; invalid/missing ones go to API

    # Regenerate only the missing embeddings via API
    regenerated: dict[int, list[float]] = {}
    if chunk_indices_needed:
        texts_for_api = [c.get("text", "")[:8000] for _, c in chunk_indices_needed]
        try:
            api_embeddings = get_embeddings_batch(texts_for_api)
        except Exception:
            # API also failed — return chunks as-is so the caller indexes zeros
            return chunks, False

        if len(api_embeddings) != len(chunk_indices_needed):
            raise RuntimeError(
                f"Embedding count mismatch: got {len(api_embeddings)} embeddings "
                f"for {len(chunk_indices_needed)} missing chunks. Refusing to index with truncated data."
            )

        for (i, _), emb in zip(chunk_indices_needed, api_embeddings):
            if not _embedding_is_valid(emb):
                raise RuntimeError(
                    f"Regenerated embedding for chunk {chunks[i].get('chunk_id')} is invalid "
                    f"(length {len(emb) if isinstance(emb, list) else type(emb)}). "
                    f"Expected {EMBEDDING_DIM}-dim float list."
                )
            regenerated[i] = emb

    # Build final chunks: valid Qdrant embeddings + regenerated embeddings
    valid_qdrant_indices = set(chunk_indices_from_qdrant)
    updated_chunks = []
    any_regenerated = bool(regenerated)
    for i, c in enumerate(chunks):
        c_copy = dict(c)
        if i in regenerated:
            c_copy["embedding"] = regenerated[i]
        elif i in valid_qdrant_indices:
            c_copy["embedding"] = qdrant_embeddings[c["chunk_id"]]
        updated_chunks.append(c_copy)

    return updated_chunks, any_regenerated


def _get_embeddings_from_qdrant(chunk_ids: list[str], workspace_id: str) -> dict[str, list[float]]:
    """
    Read dense embeddings directly from Qdrant for the given chunk_ids.

    Uses the same point ID scheme as index_chunks:
      point_id = abs(hash(chunk_id)) % (2**63)

    Returns a dict mapping chunk_id -> embedding vector.
    Raises Exception if Qdrant is unavailable.
    """
    if not chunk_ids:
        return {}

    from services.vector_service import get_client, QDRANT_COLLECTION

    client = get_client()

    # Compute point IDs using the same formula as index_chunks
    point_ids = [abs(hash(cid)) % (2**63) for cid in chunk_ids]

    # Retrieve with vectors
    records = client.retrieve(
        collection_name=QDRANT_COLLECTION,
        ids=point_ids,
        with_vectors=True,
    )

    # Build chunk_id -> embedding map
    result: dict[str, list[float]] = {}
    for record in records:
        # The payload contains chunk_id
        payload = record.payload or {}
        chunk_id = payload.get("chunk_id")
        if chunk_id and record.vector and "dense" in record.vector:
            result[chunk_id] = record.vector["dense"]

    return result


def _chunk_document(normalized_doc, workspace_id: str, strategy: str = "recursive"):
    """Dispatch to the appropriate chunker based on strategy."""
    if strategy not in VALID_CHUNKING_STRATEGIES:
        raise ValueError(
            f"Invalid chunking_strategy '{strategy}'. "
            f"Must be one of: {', '.join(sorted(VALID_CHUNKING_STRATEGIES))}"
        )
    if strategy == "semantic":
        return semantic_chunk(
            normalized_doc,
            chunk_size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP,
            workspace_id=workspace_id,
        )
    return recursive_chunk(
        normalized_doc,
        chunk_size=CHUNK_SIZE,
        overlap=CHUNK_OVERLAP,
        workspace_id=workspace_id,
    )


def ingest_document(
    file_path: Path,
    workspace_id: str = "default",
    original_filename: Optional[str] = None,
    chunking_strategy: str = "recursive",
) -> DocumentUploadResponse:
    """
    Full ingestion pipeline:
    1. Parse document
    2. Save raw JSON
    3. Chunk text (recursive or semantic based on chunking_strategy)
    4. Generate embeddings
    5. Index in Qdrant

    Returns DocumentUploadResponse with document_id and metadata.
    """
    start_time = time_module.time()

    # Validate workspace directory
    doc_dir = DOCUMENTS_DIR / workspace_id
    doc_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Parse ─────────────────────────────────────────
    try:
        normalized, metadata = parse_document(file_path, workspace_id)
    except UnsupportedFormatError as e:
        raise IngestionError(str(e))
    except ParseError as e:
        raise IngestionError(f"Erro no parse: {e}")
    except Exception as e:
        raise IngestionError(f"Erro inesperado no parse: {e}")

    doc_id = metadata.document_id
    catalog_scope = "operational" if _is_operational_upload(file_path) else "canonical"
    normalized.metadata["catalog_scope"] = catalog_scope

    # ── Step 2: Save raw JSON ───────────────────────────────────
    try:
        raw_json_path = save_raw_json(normalized, doc_dir)
        metadata.status = "parsed"
    except Exception as e:
        metadata.status = "partial"
        # Continue even if save fails

    # ── Step 3: Chunk ───────────────────────────────────────────
    try:
        chunks = _chunk_document(normalized, workspace_id, chunking_strategy)
    except Exception as e:
        raise IngestionError(f"Erro no chunking: {e}")

    if not chunks:
        raise IngestionError("Chunking não gerou nenhum chunk.")

    # ── Step 4: Generate embeddings ────────────────────────────
    try:
        texts = [chunk.text for chunk in chunks]
        embeddings = get_embeddings_batch(texts)
    except Exception as e:
        raise IngestionError(f"Erro ao gerar embeddings: {e}")

    if len(embeddings) != len(chunks):
        raise IngestionError(
            f"Mismatch: {len(chunks)} chunks mas {len(embeddings)} embeddings"
        )

    response_status = "parsed"
    response_chunk_count = len(chunks)
    telemetry_status = "success"
    telemetry_error = None

    # ── Step 5: Index in Qdrant ───────────────────────────────
    try:
        index_chunks(chunks, embeddings, workspace_id)
    except Exception as e:
        metadata.status = "partial"
        response_status = "partial"
        telemetry_status = "partial"
        telemetry_error = f"Erro ao indexar no Qdrant: {e}"

    # Persist the ingestion status into the canonical raw JSON so the registry
    # can distinguish partial ingestion from a fully indexed document.
    try:
        normalized.metadata["ingestion_status"] = response_status
        normalized.metadata["chunk_count"] = len(chunks)
        save_raw_json(normalized, doc_dir)
    except Exception:
        pass  # Non-critical

    # ── Save chunk metadata ───────────────────────────────────
    try:
        chunks_file = doc_dir / f"{doc_id}_chunks.json"
        with open(chunks_file, "w", encoding="utf-8") as f:
            json.dump([c.model_dump() for c in chunks], f, ensure_ascii=False)
    except Exception:
        pass  # Non-critical

    pruned_upload_revisions = 0
    if catalog_scope == "operational":
        try:
            pruned_upload_revisions = _prune_previous_operational_uploads(
                workspace_id=workspace_id,
                filename=original_filename or file_path.name,
                keep_document_id=doc_id,
            )
        except Exception:
            pruned_upload_revisions = 0

    # ── Step 4: Log ingestion event ────────────────────────
    elapsed_ms = int((time_module.time() - start_time) * 1000)
    try:
        from services.telemetry_service import get_telemetry
        tel = get_telemetry()
        tel.log_ingestion(
            document_id=doc_id,
            workspace_id=workspace_id,
            source_type=normalized.source_type,
            filename=original_filename or file_path.name,
            status=telemetry_status,
            chunk_count=response_chunk_count,
            processing_time_ms=elapsed_ms,
            error=telemetry_error,
            embedding_status="regenerated",
        )
    except Exception:
        pass  # Non-critical

    return DocumentUploadResponse(
        document_id=doc_id,
        status=response_status,
        catalog_scope=catalog_scope,
        source_type=metadata.source_type,
        filename=metadata.filename,
        page_count=metadata.page_count,
        char_count=metadata.char_count,
        chunk_count=response_chunk_count,
        created_at=metadata.created_at,
        chunking_strategy=chunking_strategy,
    )


def reindex_document(
    document_id: str,
    workspace_id: str = "default",
    chunking_strategy: str = "recursive",
    chunks: list[dict] | None = None,
) -> tuple[int, str, int]:
    """
    Returns tuple of (chunk_count, embedding_status, processing_time_ms).
    """
    """
    Re-chunk and re-index a document (useful after changing chunking strategy).

    If `chunks` is provided (list of chunk dicts, e.g. from a backup file), those
    exact chunks are used — no re-chunking. This is used for faithful restoration
    of the original state.

    Returns a tuple of (chunk_count, embedding_status):
      - embedding_status in {"original", "regenerated", "degraded_zero_fallback"}
        "original" — chunks had valid embeddings (backup was good)
        "regenerated" — embeddings were regenerated from chunk text
        "degraded_zero_fallback" — backup had no valid embeddings and
                                   get_embeddings_batch also failed; zeros indexed

    Parameters:
        chunks: optional pre-serialized chunks (e.g. from *_chunks_backup.json).
                If provided, chunking_strategy is ignored and these chunks are
                indexed directly into Qdrant and written to the chunks file.
    """
    start_time = time_module.time()
    doc_dir = DOCUMENTS_DIR / workspace_id
    raw_path = doc_dir / f"{document_id}_raw.json"

    def _persist_raw_ingestion_status(status: str) -> None:
        try:
            with open(raw_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            payload.setdefault("metadata", {})
            payload["metadata"]["ingestion_status"] = status
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    if chunks is None:
        # Normal path: load raw, re-chunk, generate embeddings
        if not raw_path.exists():
            raise IngestionError(f"Raw JSON não encontrado: {raw_path}")

        with open(raw_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        normalized = NormalizedDocument(**data)

        qdrant_synced = True
        try:
            delete_document_chunks(document_id)
        except Exception:
            qdrant_synced = False

        # Re-chunk and re-index
        chunk_objs = _chunk_document(normalized, workspace_id, chunking_strategy)

        texts = [chunk.text for chunk in chunk_objs]
        embeddings = get_embeddings_batch(texts)

        try:
            index_chunks(chunk_objs, embeddings, workspace_id)
        except Exception:
            qdrant_synced = False

        # Save updated chunks to disk (so document_registry reflects new strategy)
        try:
            chunks_file = doc_dir / f"{document_id}_chunks.json"
            with open(chunks_file, "w", encoding="utf-8") as f:
                json.dump([c.model_dump() for c in chunk_objs], f, ensure_ascii=False)
        except Exception:
            pass  # Non-critical

        _persist_raw_ingestion_status("parsed" if qdrant_synced else "partial")

        elapsed_ms = int((time_module.time() - start_time) * 1000)
        return len(chunk_objs), "regenerated", elapsed_ms

    else:
        # Restoration path: use pre-computed chunks (from backup)
        updated_chunks, were_regenerated = _restore_embeddings_if_needed(chunks)

        # Reconstruct Chunk objects from (possibly updated) dicts
        chunk_objs = [Chunk(**c) for c in updated_chunks]

        # Extract embeddings
        embeddings = [c.get("embedding", [0.0] * EMBEDDING_DIM) for c in updated_chunks]
        embeddings = [
            e if isinstance(e, list) and len(e) == EMBEDDING_DIM
            else [0.0] * EMBEDDING_DIM
            for e in embeddings
        ]

        # Determine embedding status for the return value:
        #   were_regenerated=True  → "regenerated" (API call succeeded)
        #   were_regenerated=False  → check if chunks now have valid embeddings
        #                              if yes: "original" (backup was already good)
        #                              if no:  "degraded_zero_fallback" (API also failed)
        if were_regenerated:
            embedding_status = "regenerated"
        else:
            # No regeneration was needed OR API failed — check current state
            all_have = all(_embedding_is_valid(c.get("embedding")) for c in updated_chunks)
            embedding_status = "original" if all_have else "degraded_zero_fallback"

        qdrant_synced = True
        try:
            delete_document_chunks(document_id)
        except Exception:
            qdrant_synced = False

        # Index restored chunks with (possibly regenerated) embeddings
        try:
            index_chunks(chunk_objs, embeddings, workspace_id)
        except Exception:
            qdrant_synced = False

        # Write (updated) chunks to disk — this now includes valid embeddings
        # so the file is self-contained and consistent with Qdrant
        try:
            chunks_file = doc_dir / f"{document_id}_chunks.json"
            with open(chunks_file, "w", encoding="utf-8") as f:
                json.dump(updated_chunks, f, ensure_ascii=False)
        except Exception:
            pass  # Non-critical

        _persist_raw_ingestion_status("parsed" if qdrant_synced else "partial")

        elapsed_ms = int((time_module.time() - start_time) * 1000)
        return len(chunk_objs), embedding_status, elapsed_ms
