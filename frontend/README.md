# Frontend Canônico

Este diretório é o frontend canônico da **Fase 2 — Produto Premium**.

## Status

- app ativo do produto
- integrado ao backend em `src/api/main.py`
- cobre documentos, busca, chat, dashboard e auditoria
- já inclui a fundação enterprise do `Sprint G1` com login, sessão, tenant e `/admin`
- shell responsivo com navegação desktop e drawer mobile
- validado com `pnpm exec tsc --noEmit`, `pnpm lint`, `pnpm build` e `pnpm test:smoke`

## Comandos

```bash
pnpm install
pnpm dev
pnpm exec tsc --noEmit
pnpm lint
pnpm build
pnpm test:smoke
```

## Variáveis

Use `NEXT_PUBLIC_API_BASE_URL` para apontar o backend.

Exemplo:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Observação

Não existe uma segunda base de frontend ativa neste repositório. Use apenas `frontend/` como implementação principal.

## Execução local

- use `NEXT_PUBLIC_API_BASE_URL` para apontar o backend local
- a interface principal cobre documentos, busca, chat, dashboard e auditoria sem depender de Swagger para a rotina normal
- a navegação lateral vira drawer em telas reduzidas
- o smoke test sobe backend isolado em `8010` e frontend isolado em `3005`
- o smoke usa `NEXT_DIST_DIR=.next-playwright` para não misturar cache de teste com o build principal
