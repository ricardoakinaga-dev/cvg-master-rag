# MASTER EXECUTION LOG — CVG RAG Enterprise Premium

---

## ENTRY TEMPLATE

### TIMESTAMP
YYYY-MM-DD HH:MM

### ENGINE
DISCOVERY | PRD | SPEC | BUILD | AUDIT

### PHASE
<phase>

### SPRINT
<sprint>

### TASK
<task>

### ACTION
Auditoria formal do estado atual do projeto usando apenas docs/00_discovery, docs/01_prd e docs/02_spec como fonte normativa

### RESULT
Relatório 0490 atualizado com score 89/100, evidência de runtime e backlog corretivo P0-P2 para atingir 96/100

### DECISIONS
Notas e backlog passam a ser ancorados exclusivamente nas trilhas 00, 01 e 02; docs fora desse conjunto não definem score

### STATUS
COMPLETED

---

## ENTRY: STRICT EXTRACTIVE REANSWER FOR CLINICAL GROUNDING

### TIMESTAMP
2026-04-20 03:45

### ENGINE
BUILD_INCREMENTAL

### PHASE
LOCAL_RUNTIME

### SPRINT
NONE

### TASK
Fazer a resposta clínica deixar de sair longa/sem grounding mesmo após o retrieval correto

### ACTION
Adicionar em `src/services/search_service.py` um segundo passe de geração com prompt mais estrito e extractivo quando o retrieval já estiver saudável, mas a primeira resposta clínica ainda vier com baixa cobertura de citação; cobrir o comportamento em `src/tests/test_sprint5.py` e validar com a query real `me dê um protocolo para convulsão em cão`

### RESULT
- a query real `me dê um protocolo para convulsão em cão` agora retorna um protocolo curto em bullets com grounding completo
- runtime real validado com:
  - `grounded: true`
  - `citation_coverage: 1.0`
  - `low_confidence: false`
  - `needs_review: false`
- chunks usados no topo da resposta: `1015`, `1014`, `1085`, `1027`, `1039`
- testes focados verdes: `4 passed`

### DECISIONS
O reanswer estrito só entra para queries clínicas/prescritivas quando a primeira resposta ainda extrapola o contexto; assim o sistema preserva respostas completas em casos já saudáveis e endurece apenas o que estava quebrando a experiência de grounding

### STATUS
COMPLETED

---

## ENTRY: CROSSLINGUAL QUERY RECOVERY FOR CLINICAL PROTOCOL QUESTIONS

### TIMESTAMP
2026-04-20 00:58

### ENGINE
BUILD_INCREMENTAL

### PHASE
LOCAL_RUNTIME

### SPRINT
NONE

### TASK
Corrigir perguntas clínicas em português com formulação de "protocolo" que ainda caíam em `Não sei.`

### ACTION
Ajustar `src/services/search_service.py` para duas frentes: `protocolo` genérico deixa de ser tratado como lookup específico no modo adaptativo, e `/query` ganha um retry crosslingual controlado com hints clínicos em inglês quando a busca inicial continua em baixa confiança; cobrir ambos os comportamentos em `src/tests/test_sprint5.py`

### RESULT
- queries como `me dê um protocolo para convulsão em cão` agora geram uma segunda busca com bridge lexical para o corpus médico em inglês
- o retry novo sobe chunks do capítulo `status epilepticus` e traz trechos terapêuticos (`1014`, `1015`, `1010`) para o topo em vez de ficar preso a contexto genérico
- o modo adaptativo continua ignorando `protocolo 12345` como lookup específico, mas deixa de bloquear perguntas abertas com `protocolo`
- testes focados verdes: `3 passed`

### DECISIONS
O recovery crosslingual fica restrito ao caminho `/query`, só entra após baixa confiança persistente e preserva o comportamento explícito de requests que já configuram reranking/query-expansion manualmente

### STATUS
COMPLETED

---

## ENTRY: P0 CLOSEOUT TO 96

### TIMESTAMP
2026-04-19 21:10

### ENGINE
BUILD_CLOSEOUT

### PHASE
ALL

### SPRINT
P0

### TASK
0490_audit_report + runtime closeout

### ACTION
Executar backlog P0 da auditoria formal: formalizar TKT-010, fechar F3 com tracing/SLI/SLO, endurecer governança sensível e publicar fechamento normativo em 00/01/02

### RESULT
- TKT-010 formalizado em `src/tests/integration/test_tkt_010_non_leakage.py`
- tracing e SLI/SLO expostos via `/observability/*` e `/admin/*`
- deleção de tenant com usuários/documentos ativos bloqueada
- rebaixamento de admin exige aprovação e ticket
- closeout oficial publicado em `00_discovery/0091`, `01_prd/0091` e `02_spec/0191`
- score consolidado atualizado para 96/100
- validação final verde: `pytest -q = 201 passed, 14 skipped`, `frontend smoke = 6 passed`

### DECISIONS
O núcleo Discovery → PRD → SPEC foi fechado em 96/100; backlog restante é incremental e não bloqueia o estado aprovado

### STATUS
COMPLETED

---

## ENTRY: INITIAL GIT PUBLISH

### TIMESTAMP
2026-04-19 23:05

### ENGINE
REPOSITORY_GOVERNANCE

### PHASE
GOVERNANCE

### SPRINT
NONE

### TASK
Inicializar versionamento e publicar snapshot oficial do projeto

### ACTION
Criar `.gitignore`, proteger `.env`/artefatos locais, inicializar o repositório git local, configurar `origin` para `ricardoakinaga-dev/cvg-master-rag` e publicar o snapshot atual em `main`

### RESULT
- `.gitignore` criado para excluir segredos, `node_modules`, caches, ambientes virtuais, logs locais e corpus operacional
- estado e log de runtime atualizados conforme AGENTS/CVG
- snapshot atual preparado para commit inicial e push para `origin/main`

### DECISIONS
O primeiro publish do repositório usa apenas código, documentação e artefatos reproduzíveis; dados operacionais locais e credenciais ficam fora do histórico git

### STATUS
COMPLETED

---

## ENTRY: REPOSITORY SCOPE CLEANUP

### TIMESTAMP
2026-04-19 23:15

### ENGINE
REPOSITORY_GOVERNANCE

### PHASE
GOVERNANCE

### SPRINT
NONE

### TASK
Remover diretórios auxiliares do repositório versionado

### ACTION
Excluir `BRIEFING/` e `transcricao-yt/` do índice git, registrar ambos no `.gitignore` e manter esses diretórios apenas no ambiente local

### RESULT
- `BRIEFING/` removido do versionamento
- `transcricao-yt/` removido do versionamento
- `.gitignore` atualizado para evitar reintrodução acidental desses diretórios

### DECISIONS
Esses diretórios deixam de compor o escopo oficial do repositório remoto e permanecem somente como apoio local

### STATUS
COMPLETED

---

## ENTRY: LOCAL STACK STARTUP

### TIMESTAMP
2026-04-19 23:30

### ENGINE
LOCAL_RUNTIME

### PHASE
DEV_RUNTIME

### SPRINT
NONE

### TASK
Instalar dependências utilizáveis e subir a stack do projeto em localhost

### ACTION
Validar `src/venv`, rodar `pnpm install`, iniciar `qdrant_rag` em Docker e subir backend/frontend em portas livres (`8010` e `3000`)

### RESULT
- backend FastAPI respondendo em `http://localhost:8010/docs`
- frontend Next.js respondendo em `http://localhost:3000`
- Qdrant respondendo em `http://localhost:6333/readyz`
- `pnpm build` concluído com sucesso
- `pip install -r requirements.txt` não foi reaplicado integralmente porque o pin `qdrant-client==1.7.4` não resolve no ambiente atual; o `venv` existente já contém `qdrant-client 1.17.1` funcional

### DECISIONS
Foi mantido o ambiente virtual já funcional do projeto em vez de forçar downgrade/incompatibilidade do `qdrant-client` com Python 3.12

### STATUS
IN_PROGRESS

---

## ENTRY: LARGE DOCUMENT INGESTION FIX

### TIMESTAMP
2026-04-19 23:06

### ENGINE
BUILD_INCREMENTAL

### PHASE
LOCAL_RUNTIME

### SPRINT
NONE

### TASK
Corrigir falha de indexação em documentos grandes

### ACTION
Ajustar `services.embedding_service` para particionar requests de embeddings abaixo do limite de tokens por requisição e `services.vector_service` para enviar upserts ao Qdrant em lotes menores

### RESULT
- erro de embeddings `max_tokens_per_request` eliminado com batching
- erro do Qdrant `JSON payload ... larger than allowed` eliminado com upserts em lote
- upload autenticado de markdown grande (`4.429.801` caracteres, `4500` chunks) finalizado com status `parsed`
- testes focados verdes: `22 passed`

### DECISIONS
O pipeline agora trata limites de payload dos provedores como restrição operacional explícita, em vez de assumir um único request por documento

### STATUS
COMPLETED

---

## ENTRY: LARGE INGESTION FIX PUBLISH

### TIMESTAMP
2026-04-19 23:15

### ENGINE
REPOSITORY_GOVERNANCE

### PHASE
GOVERNANCE

### SPRINT
NONE

### TASK
Versionar e publicar a correção de ingestão de documentos grandes

### ACTION
Registrar nos artefatos CVG a correção de batching de embeddings e de upsert no Qdrant, consolidar os testes focados e publicar o conjunto em `origin/main`

### RESULT
- correção consolidada em `services.embedding_service` e `services.vector_service`
- testes focados passaram (`22 passed`)
- publicação preparada com trilha de runtime e execution log atualizadas

### DECISIONS
`frontend/next-env.d.ts` foi tratado como ruído local do runtime e mantido fora do commit para preservar apenas mudanças funcionais e de governança

### STATUS
COMPLETED

---

## ENTRY: DASHBOARD INVENTORY SYNC

### TIMESTAMP
2026-04-19 23:28

### ENGINE
BUILD_INCREMENTAL

### PHASE
LOCAL_RUNTIME

### SPRINT
NONE

### TASK
Corrigir números do dashboard para refletir a indexação operacional

### ACTION
Trocar o `/health` para usar `get_workspace_inventory` e ajustar `dashboard`/`app-shell` para exibir totais e breakdown entre corpus canônico e uploads operacionais

### RESULT
- `/health` passou a retornar `operational_documents` e `operational_chunks`
- dashboard passou a mostrar total do workspace em vez de apenas corpus canônico
- shell lateral e banner principal passaram a usar o mesmo inventário consolidado
- validação verde: teste focado do health e `pnpm exec tsc --noEmit`

### DECISIONS
Uploads indexados via fluxo operacional continuam fora do “catálogo canônico”, mas agora entram corretamente na observabilidade do workspace

### STATUS
COMPLETED

---

## ENTRY: FORMAL AUDIT REFRESH

### TIMESTAMP
2026-04-19 16:15

### ENGINE
AUDIT

### PHASE
04_AUDIT

### SPRINT
NONE

### TASK
0490_audit_report

### ACTION
Descrição do que foi feito

### RESULT
Resultado da ação

### DECISIONS
Decisões tomadas

### STATUS
IN_PROGRESS | READY_FOR_NEXT_STEP | BLOCKED | WAITING_HUMAN_APPROVAL | COMPLETED

---

## INITIAL ENTRY

### TIMESTAMP
2026-04-19 00:00

### ENGINE
SYSTEM

### PHASE
INIT

### SPRINT
NONE

### TASK
SETUP

### ACTION
Engenharia reversa do RAG Enterprise Premium — documentação completa

### RESULT
Documentação CVG completa:
- 00_discovery: 10/10 documentos ✅
- 01_prd: 11/11 documentos ✅
- 02_spec: 19/19 documentos ✅
- 03_build: 30+ documentos ✅
- 04_audit: 13/13 documentos ✅

### DECISIONS
Sistema逆向工程完成，SPEC APROVADA (100/100)，BUILD PRONTO，AUDIT PRÉ-BUILD

### STATUS
READY_FOR_NEXT_STEP

---

## ENTRY: SPEC COMPLETION

### TIMESTAMP
2026-04-19 10:00

### ENGINE
SPEC

### PHASE
02_SPEC

### SPRINT
NONE

### TASK
0190_spec_validation

### ACTION
Validação final do SPEC — gate approval

### RESULT
Score 100/100 ✅ APROVADO — 19/19 documentos criados

### DECISIONS
Avançar para BUILD engine conforme sequência CVG

### STATUS
COMPLETED

---

## ENTRY: BUILD INITIATED

### TIMESTAMP
2026-04-19 10:30

### ENGINE
BUILD

### PHASE
03_BUILD

### SPRINT
NONE

### TASK
0300_build_engineer_master

### ACTION
Criação de documentação BUILD completa

### RESULT
Documentação criada:
- 0300_build_engineer_master.md ✅
- 0301_ROADMAP.md ✅
- 0302_BACKLOG_MASTER.md ✅
- PHASE0_SPRINTS/ (4 sprints) ✅
- PHASE1_SPRINTS/ (3 sprints) ✅
- PHASE2_SPRINTS/ (3 sprints) ✅
- PHASE3_SPRINTS/ (3 sprints) ✅
- PHASE4_SPRINTS/ (3 sprints) ✅
- 0390_build_gate.md ✅

### DECISIONS
Build documentation completo, pronto para execução

### STATUS
READY_FOR_NEXT_STEP

---

## ENTRY: AUDIT COMPLETION

### TIMESTAMP
2026-04-19 11:00

### ENGINE
AUDIT

### PHASE
04_AUDIT

### SPRINT
NONE

### TASK
0490_audit_report

### ACTION
Relatório final de auditoria

### RESULT
Documentação criada:
- 0400_audit_scope.md ✅
- 0401_audit_plan.md ✅
- 0410_prd_adherence_audit.md ✅
- 0411_spec_adherence_audit.md ✅
- 0412_runtime_analysis.md ✅
- 0413_logs_audit.md ✅
- 0414_metrics_audit.md ✅
- 0415_integrations_audit.md ✅
- 0416_data_integrity_audit.md ✅
- 0417_security_governance_audit.md ✅
- 0418_operational_experience_audit.md ✅
- 0420_gap_analysis.md ✅
- 0421_remediation_plan.md ✅
- 0490_audit_report.md ✅

### DECISIONS
Auditoria pré-build concluída — 14 GAPs identificados com plano de remediação

### STATUS
COMPLETED

---

## ENTRY: FORMAL AUDIT REFRESH

### TIMESTAMP
2026-04-19 16:15

### ENGINE
AUDIT

### PHASE
04_AUDIT

### SPRINT
NONE

### TASK
0490_audit_report

### ACTION
Auditoria formal do estado atual usando apenas docs/00_discovery, docs/01_prd e docs/02_spec como base normativa

### RESULT
0490_audit_report.md atualizado com score 89/100, validação de runtime e backlog corretivo P0-P2 para atingir 96/100

### DECISIONS
Notas e backlog passam a ser ancorados exclusivamente nas trilhas 00, 01 e 02; fontes fora desse conjunto não definem score

### STATUS
COMPLETED

---

## 📌 REGRAS DE USO

* Registrar toda ação relevante
* Registrar antes e depois de cada execução
* Nunca apagar histórico
* Manter rastreabilidade completa

---

## ENTRY: RETRIEVAL PROFILE OFFICIALIZATION

### TIMESTAMP
2026-04-19 19:35

### ENGINE
BUILD_INCREMENTAL

### PHASE
POST_96_INCREMENTAL

### SPRINT
P1

### TASK
retrieval_profile official contract

### ACTION
Implementado `retrieval_profile` oficial com quatro perfis (`hybrid`, `hyde_hybrid`, `semantic_hybrid`, `semantic_hyde_hybrid`) no backend e no frontend, cobrindo `/search` e `/query`

### RESULT
- `src/models/schemas.py` atualizado com contrato oficial
- `src/services/search_service.py` consolidado para resolver profile + HyDE + filtro semantic
- `src/services/vector_service.py` passou a respeitar `strategy=semantic` em Qdrant e fallback local
- `src/api/main.py` alinhado para usar a mesma resolução de profile em `/search` e `/query`
- `frontend/app/search/page.tsx` e `frontend/app/chat/page.tsx` ganharam seletor configurável com modo padrão do sistema
- `frontend/lib/api.ts` e `frontend/types/index.ts` alinhados ao novo contrato
- `src/tests/test_sprint5.py` recebeu cobertura do profile oficial

### VALIDATION
- `pytest -q` → `204 passed, 14 skipped`
- `pnpm -C frontend exec tsc --noEmit` → OK
- `pnpm -C frontend lint` → OK
- `pnpm -C frontend test:smoke` → `6 passed`

### DECISIONS
Mudança mantida como incremento pós-96, sem reabrir gate nem alterar score oficial; quando o profile não é informado, o sistema preserva o comportamento legado por endpoint

### STATUS
COMPLETED

---

## ENTRY: MEDICAL CHUNK SIZE TUNING

### TIMESTAMP
2026-04-19 23:35

### ENGINE
BUILD_INCREMENTAL

### PHASE
LOCAL_RUNTIME

### SPRINT
NONE

### TASK
Elevar chunking padrão para corpus médico e validar impacto no chat

### ACTION
Atualizar o baseline de chunking para `CHUNK_SIZE=1200` e `CHUNK_OVERLAP=240`, alinhar `core.config`, `chunker`, `reindex_corpus`, `verify_setup`, `.env.example`, `README` e o `.env` local; reiniciar o backend e reindexar o documento médico operacional `ceeb49c4-9f6a-405d-b2ef-2bbba3f1313f`

### RESULT
- defaults do runtime passaram a ser `1200/240`
- `verify_setup.py` validou o novo baseline em runtime
- o PDF médico reindexado caiu de `1393` para `1150` chunks
- distribuição dos chunks do PDF médico ficou em ~`1161.7` chars de média e ~`1163` chars de mediana
- `/health?workspace_id=default` passou a reportar `operational_chunks: 5820`
- a pergunta clínica no chat continuou falhando com `Não sei.`, mas agora o desvio observado no runtime atual aponta para retrieval heterogêneo no workspace, com chunks do documento operacional `9fd3ba1f-1906-4aae-8089-0829ba292653` dominando a busca padrão

### DECISIONS
Chunk maior foi mantido como baseline porque melhora a densidade contextual dos documentos médicos, mas o próximo ajuste relevante não é novo tuning de chunk size e sim revisão do retrieval/profile para workspace misto

### STATUS
COMPLETED

---

## ENTRY: RETRIEVAL DUPLICATE COLLAPSE

### TIMESTAMP
2026-04-19 23:48

### ENGINE
BUILD_INCREMENTAL

### PHASE
LOCAL_RUNTIME

### SPRINT
NONE

### TASK
Corrigir busca híbrida dominada por chunks repetitivos irrelevantes

### ACTION
Endurecer `src/services/vector_service.py` para deduplicar candidatos com texto idêntico no mesmo documento, ordenar o `top_k` pelo `confidence_score` efetivo e penalizar hits densos de baixíssima diversidade lexical quando não existe evidência sparse

### RESULT
- `/search` para `qual o tratamento para convulsão em cão?` deixou de retornar o documento operacional repetitivo de Pix no topo
- os resultados agora passam a apontar para o documento médico `ceeb49c4-9f6a-405d-b2ef-2bbba3f1313f`
- teste focado verde: `2 passed`
- o `/query` ainda responde `Não sei.` porque a recuperação, embora agora esteja no documento correto, ainda não traz o trecho terapêutico mais específico nas primeiras posições

### DECISIONS
O ranking deixou de confiar apenas no RRF bruto quando ele está inflado por duplicação mecânica; para seleção final de resultados, o sistema agora privilegia o score efetivamente exposto ao usuário e elimina redundância óbvia antes do `top_k`

### STATUS
COMPLETED

---

## ENTRY: QUERY NEURAL FALLBACK

### TIMESTAMP
2026-04-19 23:56

### ENGINE
BUILD_INCREMENTAL

### PHASE
LOCAL_RUNTIME

### SPRINT
NONE

### TASK
Melhorar a segunda camada do chat quando a primeira busca retorna contexto fraco

### ACTION
Ajustar `src/services/search_service.py` para que `/query` faça um retry automático com `reranking_method=neural` quando a primeira rodada de retrieval vier com `low_confidence=true` e o usuário não tiver pedido um reranking explícito

### RESULT
- a mesma pergunta clínica `qual o tratamento para convulsão em cão?` deixou de retornar `Não sei.`
- o fallback passou a selecionar chunks médicos como `1009`, `1022` e `0380` do documento `ceeb49c4-9f6a-405d-b2ef-2bbba3f1313f`
- teste focado verde: `2 passed`
- a resposta continua marcada com `grounded=false`/`low_confidence=true` porque o grounding atual depende de overlap lexical entre resposta em português e citações em inglês

### DECISIONS
O retry neural fica restrito a casos de baixa confiança e só entra quando o usuário não configurou manualmente o reranking, preservando controle explícito da API e evitando custo extra em queries saudáveis

### STATUS
COMPLETED

---

## ENTRY: MULTILINGUAL GROUNDING HARDENING

### TIMESTAMP
2026-04-20 00:08

### ENGINE
BUILD_INCREMENTAL

### PHASE
LOCAL_RUNTIME

### SPRINT
NONE

### TASK
Corrigir grounding para respostas em português sobre citações em inglês

### ACTION
Endurecer `src/services/grounding_service.py` para validar claims usando unidades menores da citação, fallback semântico com embeddings e overlap de cognatos longos entre línguas próximas; cobrir o comportamento em `src/tests/test_sprint5.py`

### RESULT
- `verify_grounding` deixou de depender apenas de overlap lexical literal
- teste focado verde: `3 passed`
- a query real `qual o tratamento para convulsão em cão?` agora retorna:
  - `grounded: true`
  - `citation_coverage: 1.0`
  - `low_confidence: false`
  - `needs_review: false`
- o retry neural continua sendo o método de retrieval usado para essa query (`reranking_method=neural`)

### DECISIONS
O grounding multilíngue permanece conservador offline porque o fallback semântico só entra quando embeddings estão disponíveis; sem embeddings, o sistema ainda fica ancorado nos checks lexicais e de contexto

### STATUS
COMPLETED
