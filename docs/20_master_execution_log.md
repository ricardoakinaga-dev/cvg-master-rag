# MASTER EXECUTION LOG — CVG RAG Enterprise Premium

---

## ENTRY: P4 FINAL TOOLING CLOSEOUT

### TIMESTAMP
2026-04-22 22:05

### ENGINE
AUDIT

### PHASE
P4_FINAL_TOOLING

### SPRINT
P4

### TASK
Executar a última perseguição focada em tooling para aproximar o score de 96/100 sem mudar escopo funcional

### ACTION
Rerodar lint/build/typecheck/E2E/backend completos, preservar a arquitetura estabilizada e consolidar a nota final do programa.

### RESULT
- backend verde: `218 passed, 17 skipped`
- frontend lint verde
- frontend build verde
- frontend typecheck verde
- frontend Playwright verde: `6 passed`
- score consolidado em `95/100`

### DECISIONS
- o programa ficou operacionalmente estável em 95/100
- a perseguição de 96/100 passou a ser essencialmente decisão de tooling fino

### STATUS
COMPLETED

---

## ENTRY: CLINICAL ACRONYM RETRIEVAL CLEANUP

### TIMESTAMP
2026-04-22 23:18

### ENGINE
AUDIT

### PHASE
CLINICAL_ACRONYM_RETRIEVAL

### SPRINT
OPS_VALIDATION

### TASK
Corrigir o caso em que perguntas veterinárias abreviadas, como `qual os sintomas de DRC em gatos`, estavam puxando bibliografia e chunks fora de escopo no topo do retrieval.

### ACTION
Inspecionar os chunks efetivamente retornados pelo log e confirmar que a contaminação vinha de queries abreviadas com sigla clínica, agravadas pelo retry neural automático. Implementar expansão explícita de siglas clínicas em `src/services/search_service.py` (`DRC`, `IRC`, `DUT`, `ITU`, `IRCF`), bloquear o retry neural automático para queries dominadas por siglas e apertar o suporte lexical mínimo em `src/services/vector_service.py`/`src/services/search_service.py` para exigir termos de conteúdo em vez de overlap genérico como `sintomas`, `doença` e `gatos`. Adicionar testes de regressão e reiniciar o backend local na mesma `8000`.

### RESULT
- a query `qual os sintomas de DRC em gatos` deixou de cair em bibliografia e referências
- o retry neural automático não foi mais aplicado nesse caso (`reranking_applied=false`)
- o top 5 da API passou a conter apenas chunks renais/urinários (`1286`, `1265`, `1288`, `1283`, `1264`)
- chunk gastrointestinal genérico saiu do topo após o reforço do suporte lexical por termos de conteúdo
- a resposta final permaneceu corretamente abstida: `Não tenho informações suficientes para responder a esta pergunta de forma precisa.`
- testes verdes cobrindo expansão de siglas, gate do retry neural e suporte lexical de conteúdo

### DECISIONS
- tratar siglas clínicas abreviadas como problema de recuperação, não de geração
- preferir expansão lexical controlada a depender de retry neural em queries curtas e ambíguas
- manter a abstenção enquanto o corpus não trouxer um chunk explicitamente suportando a lista de sintomas pedida

### STATUS
COMPLETED

---

## ENTRY: RANKING SCORE NORMALIZATION

### TIMESTAMP
2026-04-22 23:11

### ENGINE
AUDIT

### PHASE
RANKING_SCORE_NORMALIZATION

### SPRINT
OPS_VALIDATION

### TASK
Eliminar a saturação artificial do score exposto pelo retrieval híbrido, que estava empatando muitos resultados topo em `1.0` e mascarando a ordenação real dos chunks.

### ACTION
Medir os sinais reais retornados pelo retrieval (`dense_score`, `sparse_score`, `RRF`) para a query veterinária ampla e confirmar que a função `_compute_confidence_score` em `src/services/vector_service.py` somava diretamente um BM25 aberto (`~3.0-3.6`) com outros sinais e depois cortava em `1.0`. Substituir essa composição por normalização monotônica de `sparse_score` e `RRF`, preservando interpretabilidade frente ao threshold do retrieval. Adicionar testes de regressão em `src/tests/test_sprint5.py` para evitar nova saturação e garantir que o comportamento do threshold continue consistente. Reiniciar o backend local na mesma `8000` e validar a API real.

### RESULT
- scores do retrieval da query `qual os sinais de doença renal crônica e gatos` deixaram de colapsar em `1.0`
- distribuição real observada na API após a correção: `0.7599`, `0.7445`, `0.6861`, `0.6782`, `0.6616`
- testes direcionados verdes para normalização de confidence score e preservação do threshold
- runtime local preservado na mesma `8000`, sem dependências novas e sem portas extras
- a resposta final continua abstida (`Não sei.`), mas agora o ranking expõe gradação útil para a próxima rodada de refinamento semântico

### DECISIONS
- manter o score exposto como sinal calibrado para threshold/observabilidade, separado do RRF bruto
- tratar o problema remanescente como ordenação semântica do corpus, não mais como saturação numérica do ranking

### STATUS
COMPLETED

---

## ENTRY: RETRIEVAL AND RUNTIME DEBUG FOR VETERINARY QUERY

### TIMESTAMP
2026-04-22 22:59

### ENGINE
AUDIT

### PHASE
RETRIEVAL_RUNTIME_DEBUG

### SPRINT
OPS_VALIDATION

### TASK
Provar com evidência real se o chat estava consultando chunks no Qdrant, corrigir o motivo de resultados zerados para consulta veterinária e eliminar a resposta quebrada que ainda aparecia no runtime local.

### ACTION
Inspecionar `src/services/vector_service.py` e validar a query diretamente no Qdrant com e sem filtro de `workspace_id`; identificar que o zero-result da API não vinha do `workspace_id`, mas do pós-filtro que assumia `catalog_scope=canonical` mesmo sem filtro explícito e descartava uploads operacionais. Corrigir esse comportamento mantendo o filtro canônico apenas quando solicitado explicitamente, adicionar testes de regressão e reiniciar o backend local na mesma `8000`. Em seguida, diagnosticar que `src/start_api.py` sobe o backend sem carregar `src/.env`, o que deixava o serviço de resposta sem `OPENAI_API_KEY`; corrigir o bootstrap do script para carregar `.env` sem sobrescrever variáveis já exportadas e revalidar o processo normal de subida. Por fim, ajustar o fallback offline em `src/services/llm_service.py` para não priorizar frases anatômicas com números em perguntas sobre sinais, e alinhar `src/services/search_service.py` para marcar respostas abstidas (`Não sei.`) como `low_confidence=true` com motivo `abstained`.

### RESULT
- prova objetiva de que a pergunta veterinária já recuperava chunks no Qdrant, inclusive do PDF `Semiologia Veterinária - A arte de Diagnosticar.pdf`
- causa raiz do zero-result na API encontrada e corrigida: filtro implícito de `catalog_scope=canonical`
- testes verdes para manter hits operacionais sem filtro explícito e preservar o filtro canônico quando solicitado
- falha operacional do runtime local encontrada: backend rodando sem `src/.env`
- backend reiniciado na mesma porta `8000`, sem dependência nova e sem porta extra
- fallback offline deixou de produzir a frase anatômica quebrada
- validação final no `/query`: a pergunta `qual os sinais de doença renal crônica e gatos` agora retorna `Não sei.`, com `confidence=low`, `low_confidence=true` e `low_confidence_reason=abstained`

### DECISIONS
- não remover o filtro de `workspace_id`; ele não era a causa do problema observado
- manter abstenção explícita quando os chunks recuperados não sustentarem a resposta específica pedida
- próximo refinamento deve atacar ordenação/reranking do retrieval veterinário, não autenticação, portas ou infraestrutura

### STATUS
COMPLETED

---

## ENTRY: AUTH RUNTIME RECOVERY

### TIMESTAMP
2026-04-22 23:10

### ENGINE
BUILD_FIX

### PHASE
AUTH_RUNTIME

### SPRINT
LOGIN_RECOVERY

### TASK
Corrigir o dashboard que exibia `Login falhou` para `admin@demo.local`

### ACTION
Resolver conflitos de merge nos arquivos centrais de autenticação: `frontend/app/login/page.tsx`, `frontend/components/layout/enterprise-session-provider.tsx`, `src/api/main.py`, `src/services/api_security.py`, `frontend/tests/phase2-gate.spec.ts` e `frontend/eslint.config.mjs`. Unificar o contrato em sessão por cookie `HttpOnly`, mantendo bearer apenas como fallback compatível para testes/integrações já existentes. Ajustar `frontend/playwright.config.ts` para usar `python3` no backend de teste.

### RESULT
- `POST /auth/login` voltou a responder `200`
- o backend voltou a emitir `Set-Cookie: cvg_master_rag_session=...; HttpOnly`
- `cd frontend && pnpm exec tsc --noEmit` ficou verde
- `cd frontend && pnpm exec playwright test tests/phase2-gate.spec.ts -g "rotas principais renderizam no desktop"` passou, confirmando saída real de `/login`

### DECISIONS
- o contrato oficial de sessão do dashboard permanece por cookie `HttpOnly`
- armazenamento local de token no frontend não deve voltar a ser fonte primária de autenticação

### STATUS
COMPLETED

---

## ENTRY: LOCAL RUNTIME REVALIDATION

### TIMESTAMP
2026-04-22 21:56

### ENGINE
AUDIT

### PHASE
LOCAL_RUNTIME

### SPRINT
OPS_VALIDATION

### TASK
Verificar containers, reaproveitar runtime existente e subir o app local sem instalar dependências nem abrir novas portas.

### ACTION
Inspecionar `docker ps -a`, portas em escuta e processos locais; manter backend já ativo em `8000`; reciclar o frontend degradado que ocupava `3010`; subir novamente o Next.js na mesma porta com `NEXT_PUBLIC_API_BASE_URL` apontando para o IP local da máquina.

### RESULT
- containers ativos confirmados: Redis, Qdrant e Postgres
- backend saudável em `http://127.0.0.1:8000/health`
- frontend voltou a responder `200` em `http://127.0.0.1:3010/login`
- acesso por rede validado em `http://192.168.15.10:3010/login`
- nenhuma dependência nova instalada e nenhuma porta extra aberta

### DECISIONS
- manter reaproveitamento de `3010` para frontend e `8000` para backend
- evitar reinstalação enquanto `frontend/node_modules` e serviços base permanecerem íntegros

### STATUS
COMPLETED

---

## ENTRY: AUTH LOGIN DEBUG

### TIMESTAMP
2026-04-22 22:00

### ENGINE
AUDIT

### PHASE
AUTH_DEBUG

### SPRINT
OPS_VALIDATION

### TASK
Investigar por que a UI local não conseguia logar apesar de backend e frontend estarem ativos.

### ACTION
Inspecionar logs do backend, validar a rota `POST /auth/login`, comparar o store local de autenticação em `src/data/enterprise/admin_state.json` com o contrato esperado pelo frontend/testes e alinhar `frontend/.env` ao backend operacional em `8000`.

### RESULT
- backend local confirmado saudável e rota `/auth/login` correta
- falha isolada no usuário `admin@demo.local` por alteração prévia do `password_hash`
- credencial demo restaurada no store local para voltar a aceitar `demo1234`
- `frontend/.env` corrigido de `http://localhost:8010` para `http://localhost:8000`
- validação final: `POST /auth/login` voltou a responder `200` com `Set-Cookie`

### DECISIONS
- manter o contrato demo local de `admin@demo.local` para compatibilidade com UI e testes existentes
- tratar o auth local como store persistido em JSON, não como dependência do Postgres de infraestrutura

### STATUS
COMPLETED

---

## ENTRY: AUTH UI RUNTIME DEBUG

### TIMESTAMP
2026-04-22 22:05

### ENGINE
AUDIT

### PHASE
AUTH_UI_DEBUG

### SPRINT
OPS_VALIDATION

### TASK
Resolver o caso em que a API autenticava no terminal, mas a UI ainda não conseguia concluir o login no navegador.

### ACTION
Validar preflight CORS com origem `http://192.168.15.10:3010`, verificar o `Set-Cookie` emitido pelo backend local e reiniciar o processo existente em `8000` com `CORS_ALLOWED_ORIGINS` compatível com `localhost` e IP local, além de `SESSION_COOKIE_SECURE=false` para o ambiente HTTP de desenvolvimento. Confirmar o fluxo completo com Playwright em `localhost` e no IP da máquina.

### RESULT
- preflight CORS para o IP local deixou de falhar
- `Set-Cookie` passou a ser emitido sem `Secure` em HTTP local
- login real na UI validado com sucesso em `http://127.0.0.1:3010/login`
- login real na UI validado com sucesso em `http://192.168.15.10:3010/login`
- nenhuma porta nova aberta e nenhum pacote instalado

### DECISIONS
- manter a configuração HTTP relaxada apenas no runtime local de desenvolvimento
- preservar HTTPS + cookie `Secure` para ambientes reais de staging/produção

### STATUS
COMPLETED

---

## ENTRY: QUERY GUARDRAILS AGAINST OFF-SCOPE ANSWERS

### TIMESTAMP
2026-04-22 22:15

### ENGINE
AUDIT

### PHASE
QUERY_GUARDRAILS

### SPRINT
OPS_VALIDATION

### TASK
Investigar por que o chat respondia fora de escopo e confirmar se a busca vetorial realmente passava pelo Qdrant.

### ACTION
Reproduzir o bug com uma pergunta fora de escopo no endpoint `/query`, inspecionar o payload de retrieval retornado pelo backend, confirmar a coleção ativa no Qdrant e endurecer o score/gating do retrieval para não aceitar chunks recuperados apenas por overlap numérico incidental. Adicionar testes direcionados e reiniciar o backend local na mesma `8000`.

### RESULT
- Qdrant confirmado ativo e sendo consultado pelo runtime
- causa raiz identificada: match incidental de `2014` elevava artificialmente o score de um chunk irrelevante
- `src/services/vector_service.py` passou a penalizar overlap puramente numérico sem suporte textual mínimo
- `src/services/search_service.py` passou a abortar a resposta quando retrieval low-confidence não sustenta a query
- testes direcionados verdes: `3 passed`
- validação real do `/query` agora retorna abstinência correta para pergunta fora de escopo

### DECISIONS
- manter groundedness/citation coverage como sinal secundário, não suficiente para “salvar” retrieval sem suporte mínimo à pergunta
- tratar overlap numérico isolado como evidência fraca no corpus enterprise atual

### STATUS
COMPLETED

---

## ENTRY: MARKDOWN ANSWER QUALITY RECOVERY

### TIMESTAMP
2026-04-22 22:40

### ENGINE
AUDIT

### PHASE
ANSWER_QUALITY

### SPRINT
OPS_VALIDATION

### TASK
Investigar por que respostas de perguntas válidas ainda estavam fracas, curtas demais ou enviesadas apesar do retrieval já estar protegido contra fora de escopo.

### ACTION
Inspecionar documentos e chunks reais do corpus canônico, identificar achatamento de seções Markdown em chunks multiassunto, corrigir o parser Markdown para preservar headings/seções, corrigir o chunker para quebrar explicitamente em separadores `---`, adicionar testes unitários e reindexar os documentos canônicos mais acionados pelo chat.

### RESULT
- `politicas_fluxpay.md` passou de `2` para `7` chunks mais temáticos
- respostas de reembolso/retenção/liquidação passaram a recuperar contexto mais específico
- testes direcionados verdes para parse e chunking Markdown
- nenhuma dependência nova instalada
- nenhum serviço novo criado; backend local existente continuou na `8000`

### DECISIONS
- preservar o chunking recursivo como baseline, mas com fronteiras fortes de Markdown
- reindexar de forma direcionada os documentos mais impactantes antes de qualquer rodada ampla no corpus inteiro

### STATUS
COMPLETED
