# BACKLOG MASTER — CVG RAG Enterprise Premium

---

## P0 — CRÍTICO (Foundation — Execução Imediata)

### ITEM 1
- **título:** Executar Sprint 0.1 — Auth Module Básico
- **descrição:** Session storage, login endpoint, logout endpoint, session validation
- **módulo:** Auth
- **dependência:** Nenhuma
- **fase:** Phase 0
- **risco:** Baixo
- **impacto:** Alto

### ITEM 2
- **título:** Executar Sprint 0.2 — Session Persistence
- **descrição:** Session expiry, refresh, configurable timeout
- **módulo:** Auth
- **dependência:** Sprint 0.1
- **fase:** Phase 0
- **risco:** Baixo
- **impacto:** Alto

### ITEM 3
- **título:** Executar Sprint 0.3 — RBAC Middleware
- **descrição:** Role definitions, RBAC decorator, protected endpoints, audit log
- **módulo:** Auth
- **dependência:** Sprint 0.1
- **fase:** Phase 0
- **risco:** Médio
- **impacto:** Alto

### ITEM 4
- **título:** Executar Sprint 0.4 — Telemetry + Health
- **descrição:** Structured logging, request_id middleware, health endpoint
- **módulo:** Telemetry
- **dependência:** Sprint 0.1
- **fase:** Phase 0
- **risco:** Baixo
- **impacto:** Alto

### ITEM 5
- **título:** Executar Sprint 1.1 — Admin CRUD
- **descrição:** Tenant CRUD, User CRUD, persistence
- **módulo:** Admin
- **dependência:** Sprint 0.3
- **fase:** Phase 1
- **risco:** Médio
- **impacto:** Alto

### ITEM 6
- **título:** Executar Sprint 1.2 — Tenant Isolation
- **descrição:** Workspace filter, bootstrap protection
- **módulo:** Admin
- **dependência:** Sprint 1.1
- **fase:** Phase 1
- **risco:** Alto
- **impacto:** Crítico

### ITEM 7
- **título:** Executar Sprint 1.3 — Non-Leakage Suite
- **descrição:** TKT-010 suite, cross-tenant tests
- **módulo:** Admin
- **dependência:** Sprint 1.2
- **fase:** Phase 1
- **risco:** Alto
- **impacto:** Crítico

### ITEM 8
- **título:** Executar Sprint 2.1 — Retrieval Module
- **descrição:** Hybrid search (dense + sparse + RRF)
- **módulo:** Retrieval
- **dependência:** Sprint 0.4
- **fase:** Phase 2
- **risco:** Médio
- **impacto:** Alto

### ITEM 9
- **título:** Executar Sprint 2.2 — Query/RAG Module
- **descrição:** Context assembly, LLM response, citations, groundedness
- **módulo:** Query/RAG
- **dependência:** Sprint 2.1
- **fase:** Phase 2
- **risco:** Médio
- **impacto:** Alto

### ITEM 10
- **título:** Executar Sprint 2.3 — Evaluation Framework
- **descrição:** Dataset, hit rate calculation, evaluation runner
- **módulo:** Evaluation
- **dependência:** Sprint 2.2
- **fase:** Phase 2
- **risco:** Médio
- **impacto:** Alto

---

## P1 — ALTA PRIORIDADE

### ITEM 1
- **título:** Executar Sprint 3.1 — Advanced Tracing
- **descrição:** request_id propagation, spans, cross-module trace
- **módulo:** Telemetry
- **dependência:** Phase 2 completa
- **fase:** Phase 3
- **risco:** Baixo
- **impacto:** Médio

### ITEM 2
- **título:** Executar Sprint 3.2 — SLI/SLO + Alerts
- **descrição:** SLI definitions, SLO targets, alert rules
- **módulo:** Telemetry
- **dependência:** Sprint 3.1
- **fase:** Phase 3
- **risco:** Baixo
- **impacto:** Médio

### ITEM 3
- **título:** Executar Sprint 3.3 — Dashboard
- **descrição:** Dashboard layout, key metrics widgets, trends, tenant filter
- **módulo:** Telemetry
- **dependência:** Sprint 3.2
- **fase:** Phase 3
- **risco:** Baixo
- **impacto:** Médio

### ITEM 4
- **título:** Executar Sprint 4.3 — Final Audit
- **descrição:** Full code audit, gate F3 validation
- **módulo:** All
- **dependência:** Phase 3 completa
- **fase:** Phase 4
- **risco:** Médio
- **impacto:** Alto

---

## P2 — MÉDIA PRIORIDADE

### ITEM 1
- **título:** Executar Sprint 4.1 — TypeScript Checks
- **descrição:** tsc --noEmit, type annotations, CI integration
- **módulo:** Build
- **dependência:** Código completo
- **fase:** Phase 4
- **risco:** Baixo
- **impacto:** Médio

### ITEM 2
- **título:** Executar Sprint 4.2 — Smoke Tests
- **descrição:** Smoke test suite, critical flows, stable execution
- **módulo:** Build
- **dependência:** Sprint 4.1
- **fase:** Phase 4
- **risco:** Baixo
- **impacto:** Médio

---

## P3 — BAIXA PRIORIDADE (Future Scope)

### ITEM 1
- **título:** Cohere Rerank integration
- **descrição:** Reranking premium se hit_rate < 80%
- **módulo:** Retrieval
- **dependência:** RRF working
- **fase:** Future
- **risco:** Baixo
- **impacto:** Baixo

### ITEM 2
- **título:** Supabase Auth SSO
- **descrição:** Enterprise SSO se necessidade real
- **módulo:** Auth
- **dependência:** Current auth working
- **fase:** Future
- **risco:** Baixo
- **impacto:** Baixo

### ITEM 3
- **título:** MinIO/S3 storage
- **descrição:** Object storage para documentos
- **módulo:** Ingestion
- **dependência:** Multi-service need
- **fase:** Future
- **risco:** Baixo
- **impacto:** Baixo

### ITEM 4
- **título:** LangSmith integration
- **descrição:** Evaluation integration
- **módulo:** Evaluation
- **dependência:** Dataset working
- **fase:** Future
- **risco:** Baixo
- **impacto:** Baixo

---

## 📌 REGRAS DE USO

* Backlog deve ser atualizado continuamente
* Novos itens devem ser adicionados imediatamente
* Itens devem ser priorizados corretamente
* Backlog guia execução futura

---

## DÉPITOS TÉCNICOS REGISTRADOS

| ID | Débitos | Severidade | Phase |
|---|---|---|---|
| D1 | Sistema ainda não implementado | 🟠 Alto | ALL |
| D2 | Não há runtime para auditar | 🟠 Alto | AUDIT |
| D3 | Fallback graceful limitado | 🟡 Médio | F2 |
| D4 | Session storage in-memory | 🟡 Médio | F0 |
| D5 | No CI/CD configurado | 🟡 Médio | F4 |