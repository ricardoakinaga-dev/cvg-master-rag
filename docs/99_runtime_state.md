# 99_runtime_state.md

# RUNTIME STATE — CVG RAG Enterprise Premium

## CONTEXTO
- project: cvg-master-rag
- current_engine: AUDIT
- completion_status: ✅ RETRIEVAL OPERACIONAL REVALIDADO, RUNTIME LOCAL CORRIGIDO, SCORE DE RANKING NORMALIZADO E QUERIES COM SIGLAS CLÍNICAS DESCONTAMINADAS DE BIBLIOGRAFIA/CHUNKS FORA DE ESCOPO

## POSIÇÃO ATUAL
- current_phase: AUDIT — RAG ANSWER QUALITY
- current_task: confirmar por evidência real o comportamento do retrieval no Qdrant, corrigir descarte indevido de documentos operacionais, alinhar a qualidade/sinalização das respostas, eliminar saturação artificial do ranking híbrido e tratar queries clínicas com siglas ambíguas

## STATUS
- status: READY_FOR_NEXT_STEP
- maturity: 95%
- score_target: 96/100

## PROGRESSO
- last_completed_action: queries clínicas com siglas passaram a ser expandidas antes da busca em `src/services/search_service.py` (ex.: `DRC` → `doença renal crônica`) e o retry neural automático foi bloqueado para queries dominadas por sigla, evitando contaminação por bibliografia/referências. Em paralelo, `src/services/vector_service.py` e `src/services/search_service.py` passaram a exigir suporte lexical de conteúdo, não apenas overlap genérico como `sintomas`/`gatos`. Testes de regressão foram adicionados em `src/tests/test_sprint5.py`. Validação final na API: a query `qual os sintomas de DRC em gatos` deixou de retornar chunks de bibliografia e gastro; o top 5 passou a ser composto por chunks renais/urinários (`1286`, `1265`, `1288`, `1283`, `1264`) e a resposta final permaneceu corretamente abstida por falta de suporte específico no corpus
- next_action: revisar se vale reindexar ou segmentar melhor o capítulo urinário/renal do PDF veterinário, porque o retrieval já está limpo, mas o corpus ainda não traz um chunk explicitamente listando os sintomas específicos que a pergunta pede

## BLOQUEIOS
- blockers: nenhum bloqueio crítico no runtime local; permanece apenas gap de conteúdo/segmentação no corpus veterinário para perguntas específicas sobre sintomas de DRC

## DECISÃO HUMANA
- human_decision_required: no
- decision_description: a rodada atual atacou a causa estrutural da baixa qualidade no corpus Markdown sem instalar dependências nem alterar a arquitetura base do RAG

## TIMESTAMP
- last_update: 2026-04-22T23:18:00-03:00

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
| 2026-04-22 | AUDIT | COMPLETED | P4_FINAL_REAUDIT | Rodada final com gates verdes e score 95/100 | READY_FOR_NEXT_STEP |
| 2026-04-22 | BUILD_FIX | COMPLETED | AUTH_RUNTIME | Correção do login do dashboard com sessão por cookie e limpeza dos conflitos de merge do runtime | COMPLETED |
| 2026-04-22 | AUDIT | COMPLETED | LOCAL_RUNTIME | Runtime local revalidado com backend em 8000 e frontend reciclado na mesma 3010 sem reinstalação | READY_FOR_NEXT_STEP |
| 2026-04-22 | AUDIT | COMPLETED | AUTH_DEBUG | Login local revalidado após restauração da credencial demo do admin e correção do endpoint base do frontend | READY_FOR_NEXT_STEP |
| 2026-04-22 | AUDIT | COMPLETED | AUTH_UI_DEBUG | Login via UI validado em localhost e IP após ajuste de CORS e cookie HTTP do backend local | READY_FOR_NEXT_STEP |
| 2026-04-22 | AUDIT | COMPLETED | QUERY_GUARDRAILS | Query/chat endurecidos contra falso positivo do Qdrant com overlap numérico incidental e abstenção fora de escopo | READY_FOR_NEXT_STEP |
| 2026-04-22 | AUDIT | COMPLETED | ANSWER_QUALITY | Parse/chunking Markdown corrigidos e corpus canônico principal reindexado para melhorar especificidade das respostas | READY_FOR_NEXT_STEP |
| 2026-04-22 | AUDIT | COMPLETED | RETRIEVAL_RUNTIME_DEBUG | Filtro implícito de `catalog_scope` removido, backend local reiniciado com `.env` e sinalização de abstenção alinhada ao payload do chat | READY_FOR_NEXT_STEP |
| 2026-04-22 | AUDIT | COMPLETED | RANKING_SCORE_NORMALIZATION | Normalização do score híbrido eliminou empates artificiais em `1.0` e devolveu gradação útil aos resultados do retrieval | READY_FOR_NEXT_STEP |
| 2026-04-22 | AUDIT | COMPLETED | CLINICAL_ACRONYM_RETRIEVAL | Expansão de siglas clínicas e bloqueio do retry neural removeram chunks de bibliografia/fora de escopo em queries veterinárias abreviadas | READY_FOR_NEXT_STEP |

---

## GATES

| Gate | Arquivo | Status |
|---|---|---|
| DISCOVERY | 0090_discovery_validation.md | APROVADO |
| PRD | 0090_prd_validation.md | APROVADO |
| SPEC | 0190_spec_validation.md | APROVADO |
| BUILD | 0390_build_gate.md | APROVADO |
| AUDIT | docs/04_audit/2026-04-22-reaudit-p4-final.md | 95/100 |

---

## SCORE GERAL

### Score Atual
- current_score: 95/100
- target_score: 96/100

### Gaps Críticos Abertos
- Nenhum gap crítico aberto no fluxo de login/sessão

### Próximas Ações
1. Rerodar gates completos se quiser reconsolidar o score após a correção local de login
2. Publicar próximo fechamento formal de auditoria
