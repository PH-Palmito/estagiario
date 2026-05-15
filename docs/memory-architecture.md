# Memoria e arquitetura do Axel

Data da decisao: 2026-05-12.

## Decisao de schema

A memoria estruturada passa a ser pensada em buckets versionados:

- `profile`: dados estaveis do operador.
- `preferences`: preferencias explicitas de uso, tom, voz e fluxo.
- `operational_context`: consolidado do momento, gerado a partir de uso recente, tarefas, foco, apps e lembretes.
- `current_topic`: assunto em andamento para follow-ups.
- `semantic_notes`: notas longas e vault.
- `execution_evidence`: logs reais de uso.
- `research_sources`: fontes recuperadas para sustentar uma resposta.

Todo registro novo deve carregar `schema_version`, `bucket`, `key`, `value`, `source`, `confidence`, `evidence`, `tags`, `created_at` e `updated_at`. Quando a informacao envelhece rapido, tambem deve ter `expires_at`.

## Memoria operacional consolidada

O arquivo `memory/operational_context.py` ja monta o contexto operacional a partir de perfil, preferencias de voz, memoria operacional manual, historico recente da UI, assunto atual, avancos, gargalos, tarefas e lembretes. A decisao agora e tratar esse payload como leitura de estado, nao como fonte absoluta.

Preferencias explicitas continuam em `memory/operational_memory.json`. Contexto derivado fica em `memory/operational_context.json`. Essa separacao evita misturar algo que o operador pediu para lembrar com uma inferencia temporaria do sistema.

## Revisao de logs reais

O script `scripts/review_execution_logs.py` cria `memory/execution_log_review.json` a partir de `memory/execution_log.jsonl`.

Pontos observados no log recente:

- `daily_briefing` aparece como fluxo recorrente e deve usar contexto operacional consolidado.
- Comandos de briefing, carteira e musica podem passar de 5 segundos; vale pensar em cache, resposta progressiva ou fonte ja preparada.
- Lembretes por voz podem carregar erro de transcricao, entao o ideal e guardar texto original e texto normalizado/corrigido separadamente.
- A memoria de proximos avancos ja mudou depois da ultima rodada, sinal de que o sistema esta reagindo ao estado real.

## Camada inicial de pesquisa com fontes

`memory/research_sources.py` recupera fontes locais antes da resposta:

- perfil quando a pergunta tocar em dados pessoais, stack ou objetivos;
- contexto operacional quando a pergunta pedir memoria, foco, agora ou preferencias;
- documentos em `docs/`;
- notas do vault via busca semantica simples existente.

A camada ainda nao substitui busca web nem APIs externas. Ela prepara o contrato: cada fonte tem titulo, tipo, trecho, localizador, confianca e horario de recuperacao.

## Conversa, opiniao e limite

Nas respostas opinativas, o Axel deve separar internamente:

- fato: algo sustentado por fonte recuperada, memoria explicita ou log;
- leitura: a interpretacao do assistente sobre esses fatos;
- limite: o que nao foi verificado, pode estar desatualizado ou depende de dado externo.

Na fala final, isso nao precisa virar uma lista sempre. O ponto e evitar uma opiniao com cara de fato quando a base for fraca.
