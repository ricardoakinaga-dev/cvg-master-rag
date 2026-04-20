# 99_runtime_state.md

# RUNTIME STATE — CVG RAG Enterprise Premium

## CONTEXTO
- project: cvg-master-rag
- current_engine: BUILD_INCREMENTAL
- completion_status: ✅ QUERY CLÍNICA DE "PROTOCOLO" RESPONDE COM GROUNDING E CITAÇÕES

## POSIÇÃO ATUAL
- current_phase: LOCAL_RUNTIME — CLINICAL QUERY ANSWERING HARDENED
- current_task: `/query` combina retry crosslingual em baixa confiança com um segundo passe extractivo estrito quando a primeira resposta clínica ainda extrapola as citações

## STATUS
- status: IN_PROGRESS
- maturity: 96%
- score_target: 96/100

## PROGRESSO
- last_completed_action: `search_service` passou a fazer um segundo passe extractivo estrito quando a busca clínica está boa, mas a primeira resposta ainda fica pouco ancorada; após o retry crosslingual e o reanswer estrito, a query real `me dê um protocolo para convulsão em cão` retornou `grounded=true`, `citation_coverage=1.0`, `low_confidence=false` e `needs_review=false`
- next_action: consolidar/publicar o conjunto local de correções de retrieval + grounding quando desejado e monitorar se outras formulações clínicas precisam do mesmo padrão de reanswer estrito

## BLOQUEIOS
- blockers: none

## DECISÃO HUMANA
- human_decision_required: no
- decision_description: O reanswer estrito entra apenas quando o retrieval já está saudável e a primeira resposta ainda extrapola o contexto; isso melhora grounding sem mudar a semântica do contrato de retrieval nem forçar custo extra em queries já boas

## TIMESTAMP
- last_update: 2026-04-20T03:45:00-03:00

---

## REGRAS DE USO

O agente DEVE:
1. Ler este arquivo antes de qualquer ação
2. Atualizar este arquivo após cada ação executada
3. Nunca encerrar sem atualizar estado

---

## HISTÓRICO DE EXECUÇÃO

| Timestamp | Engine | Phase | Sprint | Action | Status |
|---|---|---|---|---|---|
| 2026-04-19 | SYSTEM | INIT | NONE | Setup inicial | READY_FOR_NEXT_STEP |
| 2026-04-19 | DISCOVERY | COMPLETED | — | Discovery completo | COMPLETED |
| 2026-04-19 | PRD | COMPLETED | — | PRD completo | COMPLETED |
| 2026-04-19 | SPEC | COMPLETED | — | SPEC completa | COMPLETED |
| 2026-04-19 | BUILD | COMPLETED | PHASE 0-4 | Build consolidado | COMPLETED |
| 2026-04-19 | AUDIT | COMPLETED | — | Auditoria formal com fonte normativa 00/01/02 | COMPLETED |
| 2026-04-19 | BUILD_CLOSEOUT | COMPLETED | P0 | Fechamento TKT-010 + F3 + governança + trilha normativa | COMPLETED |
| 2026-04-19 | BUILD_INCREMENTAL | COMPLETED | P1 | Retrieval profile oficial em backend/frontend sem regressão | COMPLETED |
| 2026-04-19 | REPOSITORY_GOVERNANCE | COMPLETED | NONE | Initial git publish para GitHub com `.gitignore` e remoto oficial | COMPLETED |
| 2026-04-19 | REPOSITORY_GOVERNANCE | COMPLETED | NONE | Remoção de `BRIEFING/` e `transcricao-yt/` do git remoto | COMPLETED |
| 2026-04-19 | LOCAL_RUNTIME | IN_PROGRESS | NONE | Dependências validadas e stack local iniciada em localhost | IN_PROGRESS |
| 2026-04-19 | BUILD_INCREMENTAL | COMPLETED | NONE | Correção de batching para embeddings OpenAI e upserts Qdrant em documentos grandes | COMPLETED |
| 2026-04-19 | REPOSITORY_GOVERNANCE | COMPLETED | NONE | Publicação da correção de ingestão grande em `origin/main` | COMPLETED |
| 2026-04-19 | BUILD_INCREMENTAL | COMPLETED | NONE | Dashboard e shell alinhados com inventário operacional do workspace | COMPLETED |
| 2026-04-19 | BUILD_INCREMENTAL | COMPLETED | NONE | Chunking padrão elevado para `1200/240` com reindexação do PDF médico e diagnóstico do retrieval heterogêneo | COMPLETED |
| 2026-04-19 | BUILD_INCREMENTAL | COMPLETED | NONE | Ranking híbrido endurecido contra chunks repetitivos irrelevantes no topo do `/search` | COMPLETED |
| 2026-04-19 | BUILD_INCREMENTAL | COMPLETED | NONE | `/query` endurecido com retry automático via neural reranking para perguntas clínicas em baixa confiança | COMPLETED |
| 2026-04-20 | BUILD_INCREMENTAL | COMPLETED | NONE | Grounding multilíngue endurecido com unidades menores, similaridade semântica e cognatos | COMPLETED |
| 2026-04-20 | BUILD_INCREMENTAL | COMPLETED | NONE | Recovery crosslingual adicionado ao `/query` para formulações clínicas com `protocolo` em português | COMPLETED |
| 2026-04-20 | BUILD_INCREMENTAL | COMPLETED | NONE | Reanswer extractivo estrito adicionado para elevar grounding em respostas clínicas | COMPLETED |

---

## GATES

| Gate | Arquivo | Status |
|---|---|---|
| DISCOVERY | 0090_discovery_validation.md | APROVADO |
| PRD | 0090_prd_validation.md | APROVADO |
| SPEC | 0190_spec_validation.md | APROVADO |
| BUILD | 0390_build_gate.md | APROVADO |
| AUDIT | 0490_audit_report.md | 96/100 |

---

## SCORE GERAL

### Score Atual
- current_score: 96/100
- target_score: 96/100

### Gaps Críticos Abertos
- Nenhum gap crítico aberto para o score 96/100

### Próximas Ações
1. Expandir retrieval profile para evaluation/admin se necessário
2. Validar impacto do profile nos datasets por workspace
3. Manter P1/P2 sem reabrir o núcleo aprovado
