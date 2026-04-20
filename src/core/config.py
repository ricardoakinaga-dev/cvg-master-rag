import os
from pathlib import Path

# Base paths — src/ is the project root
BASE_DIR = Path(__file__).parent.parent  # = .../cvg-master-rag/src
DATA_DIR = BASE_DIR / "data"
# ── Corpus paths ──────────────────────────────────────────────────────────────
# CANONICAL corpus (ingestão/consulta ativa): src/data/documents/default/
# LEGACY (arquivado): src/data/documents-ARCHIVED/default/
# `src/data/default` contém os arquivos de suporte operacional da fase (dataset, markdown)
DOCUMENTS_DIR = DATA_DIR / "documents"
CHUNKS_DIR = DATA_DIR / "chunks"
LOGS_DIR = BASE_DIR / "logs"
DATASETS_DIR = DATA_DIR / "datasets"

# Ensure directories exist
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Qdrant config
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "rag_phase0")
QDRANT_CHECK_COMPATIBILITY = os.getenv("QDRANT_CHECK_COMPATIBILITY", "false").lower() in {"1", "true", "yes", "on"}

# OpenAI config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = 1536
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Session config
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "8"))

# Chunking config
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Retrieval config
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))
DEFAULT_THRESHOLD = float(os.getenv("DEFAULT_THRESHOLD", "0.70"))

# RRF k parameter
RRF_K = 60

# Reranking config
RERANKING_ENABLED = os.getenv("RERANKING_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
RERANKING_METHOD = os.getenv("RERANKING_METHOD", "bm25f")  # "bm25f", "neural", or "none"

# Query expansion config (HyDE-like)
QUERY_EXPANSION_ENABLED = os.getenv("QUERY_EXPANSION_ENABLED", "false").lower() in {"1", "true", "yes", "on"}

# Supported formats
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}
SUPPORTED_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown",
    ".txt": "text/plain",
}
