# RAG Database Builder — Fase 3 Foundation
# =======================================

## Visão Geral

Implementação ativa da fundação **Fase 3** do plano RAG Enterprise (documentado em `/docs/rag-enterprise/`).

- **Arquitetura:** Modular Monolith (FastAPI + Qdrant + Filesystem)
- **Escopo atual:** retrieval híbrido, resposta com grounding, avaliação, sessão enterprise e multitenancy local
- **Validado:** backend `170 passed, 17 skipped` e smoke frontend da Fase 2 `5/5`

---

## Stack

| Componente | Tecnologia |
|---|---|
| Backend | FastAPI (Python 3.12+) |
| Vector DB | Qdrant (local ou cloud) |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM | GPT-4o-mini |
| Storage | Filesystem local (JSON) |
| Chunking | Recursive + Semantic |

---

## Estrutura do Projeto

```
src/
├── api/
│   └── main.py              # FastAPI app, endpoints
├── core/
│   └── config.py            # Configurações e constantes
├── models/
│   └── schemas.py           # Pydantic models (Document, Chunk, Search, Query)
├── services/
│   ├── document_parser.py   # PDF, DOCX, MD, TXT parsing
│   ├── chunker.py           # Recursive + semantic chunking
│   ├── embedding_service.py  # OpenAI embeddings
│   ├── vector_service.py    # Qdrant indexing + hybrid search (RRF)
│   ├── ingestion_service.py # Pipeline completo: parse → chunk → index
│   ├── enterprise_service.py # Sessão enterprise, tenants e autenticação local
│   ├── admin_service.py     # CRUD de tenants/usuários e RBAC local
│   ├── llm_service.py       # GPT-4o-mini answer generation
│   └── search_service.py    # Search + answer pipeline
├── tests/
│   └── test_phase0.py       # Testes básicos
├── requirements.txt
└── README.md
```

### Convenção operacional de dados

- corpus ativo: `src/data/documents/{workspace_id}/`
- corpus arquivado: `src/data/documents-ARCHIVED/{workspace_id}/`
- dataset operacional: `src/data/{workspace_id}/dataset.json`

No corpus ativo, cada documento deve existir como:

- `{document_id}_raw.json`
- `{document_id}_chunks.json`

O `raw.json` pode carregar `metadata.ingestion_status = "partial"` quando o parse/chunking conclui mas o indexador externo não está disponível. Nesse caso, o documento continua auditável e reprocessável sem perder o material canônico.

---

## Instalação

```bash
cd src

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env  # editar com suas chaves

# Editar .env:
# OPENAI_API_KEY=sk-...
# QDRANT_HOST=localhost
# QDRANT_PORT=6333
```

---

## Qdrant Setup

```bash
# Usando Docker (local)
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  qdrant/qdrant

# Ou usar Qdrant Cloud (melhor para produção)
# Configurar QDRANT_HOST e QDRANT_PORT no .env
```

---

## Executar

```bash
cd src
source venv/bin/activate

# Rodar API
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Acessar Swagger UI
# http://localhost:8000/docs
```

---

## Rebuild e Reindex

### Fonte de verdade operacional

- corpus ativo: `src/data/documents/{workspace_id}/`
- dataset operacional: `src/data/{workspace_id}/dataset.json`
- cada documento ativo deve existir como:
  - `{document_id}_raw.json`
  - `{document_id}_chunks.json`

### Regenerar apenas os chunks em disco

```bash
cd src
python3 scripts/reindex_corpus.py default --local-only
```

### Reindex completo no Qdrant

```bash
cd src
source .env
python3 scripts/reindex_corpus.py default
```

### Reindex sem recriar a collection

```bash
cd src
source .env
python3 scripts/reindex_corpus.py default --skip-recreate
```

Use reindex quando precisar restaurar `Qdrant = disco` ou reconstruir o corpus a partir dos `*_raw.json`.

Os scripts de apoio seguem a mesma convenção:

- `scripts/benchmark_controlado.py`
- `scripts/tune_chunking.py`
- `scripts/reindex_corpus.py`
- `scripts/generate_qdrant_repair_script.py`

`scripts/ingest_script.py` e `scripts/pipeline_script.py` preferem o corpus canônico já persistido; o `.md` de bootstrap só é usado se o `raw.json` ainda não existir.

Runbook operacional completo:

- `docs/rag-enterprise/0024-operacao-de-corpus-e-reindex.md`

---

## Endpoints

### `POST /documents/upload`
Upload de documento (PDF, DOCX, MD, TXT).

```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -F "file=@documento.pdf" \
  -F "workspace_id=default"
```

Resposta:
```json
{
  "document_id": "uuid",
  "status": "parsed",
  "chunk_count": 12,
  "pages": 5
}
```

---

### `POST /search`
Busca híbrida no knowledge base.

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Qual o prazo para reembolso?",
    "workspace_id": "default",
    "top_k": 5,
    "threshold": 0.70
  }'
```

---

### `POST /query`
Busca + resposta do agente.

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Qual o prazo para reembolso?",
    "workspace_id": "default",
    "top_k": 5,
    "threshold": 0.70
  }'
```

Resposta:
```json
{
  "answer": "O prazo para reembolso é de 30 dias corridos...",
  "chunks_used": ["chunk_xxx_0000", "chunk_xxx_0001"],
  "confidence": "high",
  "grounded": true,
  "low_confidence": false,
  "retrieval": {...},
  "latency_ms": 1890
}
```

---

### `GET /health`
Health check.

---

### `GET /evaluation/run`
Roda avaliação no dataset. Retorna hit rate top-1, top-5.

---

## Dataset de Validação

O sistema precisa de um dataset real para validar (Gate F0). Formato:

```json
{
  "dataset_id": "phase0_validation",
  "questions": [
    {
      "id": 1,
      "pergunta": "Qual o prazo para reembolso?",
      "document_id": "doc-001",
      "trecho_esperado": "O prazo para solicitação de reembolso é de 30 dias...",
      "resposta_esperada": "30 dias corridos após a purchase",
      "dificuldade": "easy",
      "categoria": "procedimento"
    }
  ]
}
```

Upload do dataset:
```bash
curl -X POST "http://localhost:8000/evaluation/dataset?workspace_id=default" \
  -H "Content-Type: application/json" \
  -d @dataset.json
```

---

## Gate F0 — Critérios de Validação

| Critério | Target |
|---|---|
| Hit Rate top-5 | >= 60% (12/20 perguntas) |
| Latência média | < 5s por query |
| Upload funcional | PDF, DOCX, MD, TXT |
| Busca híbrida | dense + sparse + RRF |
| Logs | Queries logadas com scores |

---

## Variáveis de Ambiente

| Variável | Default | Descrição |
|---|---|---|
| `OPENAI_API_KEY` | (vazio) | Chave da API OpenAI |
| `QDRANT_HOST` | localhost | Host do Qdrant |
| `QDRANT_PORT` | 6333 | Porta do Qdrant |
| `QDRANT_COLLECTION` | rag_phase0 | Nome da collection |
| `CHUNK_SIZE` | 1200 | Tamanho do chunk |
| `CHUNK_OVERLAP` | 240 | Overlap entre chunks |
| `DEFAULT_TOP_K` | 5 | Número de resultados |
| `DEFAULT_THRESHOLD` | 0.70 | Threshold mínimo de score |
| `LLM_MODEL` | gpt-4o-mini | Modelo para respostas |

---

## Documentação de Referência

- Plano completo: `/docs/rag-enterprise/`
- Guia completo de uso: `/docs/guia-completo-de-uso-do-programa.md`
- Fase 0 detalhada: `/docs/rag-enterprise/0004-fase-0-foundation-rag.md`
- Contratos: `/docs/rag-enterprise/0009-contratos-de-ingestao.md` e `0010-contratos-de-retrieval.md`
- Gates: `/docs/rag-enterprise/0013-quality-gates.md`
- Frontend canônico: `/frontend/README.md`
