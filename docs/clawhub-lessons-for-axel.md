---
title: "ClawHub Lessons for Axel"
type: "axel-doc"
topic: "agent-ecosystem"
updated_at: "2026-05-30"
tags: ["axel", "clawhub", "openclaw", "plugins", "skills"]
source:
  - "https://clawhub.ai/"
  - "https://docs.openclaw.ai/clawhub"
  - "https://github.com/openclaw/clawhub"
---

# ClawHub Lessons for Axel

## Resumo

ClawHub e um catalogo de skills e plugins para OpenClaw. Para o Axel, o valor nao esta em copiar o ecossistema inteiro, mas em usar o catalogo como radar de ideias praticas para agentes: providers de modelo, memoria, canais de comunicacao, automacao web, observabilidade, seguranca, pesquisa, Google Workspace e workflows.

## Decisao de adocao

O Axel vai aproveitar as ideias do ClawHub em quatro frentes principais:

1. Governanca de actions: manter `ActionSpec`, mas adicionar classe canonica de acao, risco, reversibilidade, hash do payload, decisao e auditoria.
2. Workflow planner duravel: criar um arquivo legivel para tarefas grandes com ideia, pesquisa, gate, design, plano, tarefas, handoff e fechamento.
3. Memoria em camadas: evoluir de busca simples para recall progressivo com busca semantica, resumo expandido e transcript original.
4. Observabilidade: ampliar o painel de saude com custos de API, tokens, latencia, fallback de modelo, taxa de erro e ranking de actions/skills/toolsets.

O que nao muda: o Axel continua local-first, com actions locais simples para Windows e resposta rapida por voz.

## Ideias mais proveitosas para o Axel

## Comparacao com o que o Axel ja usa

### Actions e tools

O Axel ja possui um sistema proprio de actions com `ActionSpec`, catalogo, schema, categoria, flag de leitura/escrita e confirmacao. Para uso local no Windows, isso continua melhor do que trocar por um plugin generico do ClawHub.

O que o ClawHub tem de melhor:

- workflows com estado persistente e handoff claro;
- governanca de tool calls fora do modelo;
- auditoria mais rica por acao;
- aprovacoes vinculadas ao payload, evitando que parametros mudem depois da aprovacao;
- dashboard de observabilidade para custos, tokens, sessoes e chamadas de ferramenta.

Decisao:

- manter `ActionSpec` como nucleo de actions do Axel;
- melhorar a camada ao redor dele com ideias de policy, auditoria e workflow planner.

### Planejamento e tarefas longas

O Axel ja tem `AxelBrain`, toolsets, agentes especialistas e aprendizado procedural. O ClawHub ainda parece mais forte em planejamento duravel de execucao, especialmente no modelo do OpenClaw Workflow Planner: ideia, pesquisa, gate, design, plano, tarefas, handoff e fechamento em um arquivo legivel.

Aplicacao no Axel:

- criar um `WORKFLOW_PLAN.md` ou equivalente para tarefas grandes;
- separar ideias, decisoes, tarefas abertas, tarefas concluidas e handoff de implementacao;
- preservar identidade estavel de cada tarefa mesmo quando o plano for atualizado;
- permitir retomar uma tarefa grande sem depender do historico da conversa.

### Governanca e seguranca

O Axel ja tem confirmacao e `sandbox_policy`, mas o ClawHub mostra um padrao melhor: policy enforcement fora do prompt, classificacao de acao, risco, reversibilidade, alvo, payload hash, decisao e trilha de auditoria.

Aplicacao no Axel:

- adicionar `action_class` canonica nas actions;
- calcular `payload_hash` antes da confirmacao;
- invalidar aprovacao se os parametros mudarem;
- registrar `action_id`, risco, alvo, decisao, resultado e erro;
- considerar modo fail-closed para acoes criticas.

### Memoria

O Axel ja tem memoria curta, memoria longa, memoria operacional, sessoes e skills. O ClawHub traz boas referencias de memoria markdown-first, memoria vetorial, busca hibrida BM25 + vetor, memoria episodica e recall em camadas.

Aplicacao no Axel:

- manter markdown/JSON legivel como fonte de verdade;
- adicionar indice semantico local para recall;
- usar busca hibrida em vez de apenas tokens;
- separar recall simples, expandido e transcript completo;
- criar resumo episodico por sessao/dia.

### Canais remotos

O Axel escolheu Telegram Bot como canal remoto principal. ClawHub reforca que canal remoto deve ter permissao, auditoria e confirmacao proprias.

Aplicacao no Axel:

- Telegram como canal principal;
- comandos sensiveis exigem confirmacao;
- cada mensagem remota registra origem, usuario, chat, comando, decisao e resposta;
- Discord fica apenas como alternativa futura.

### Google e agenda

O ClawHub tem plugins de Google Workspace/OAuth com Calendar, Gmail, Drive, Docs, Sheets e Tasks. Para o Axel, o mais proveitoso e usar isso como desenho de integracao, nao copiar escopos amplos.

Aplicacao no Axel:

- comecar por Google Calendar ou Google Tasks;
- usar OAuth direto;
- preferir conta Google dedicada ao Axel;
- pedir escopos minimos;
- colocar eventos no briefing e nos lembretes proativos.

### Observabilidade

O Axel ja registra `execution_log.jsonl` e tem painel de saude. O ClawHub aponta um nivel acima: dashboard de tokens, custos, tools, sessoes, memoria e cron.

Aplicacao no Axel:

- mostrar no HUD ultimos erros, latencia media, provedor usado, fallback de modelo e actions mais chamadas;
- registrar custo estimado quando usar API remota;
- rankear actions, skills, toolsets e agentes por sucesso/erro/frequencia.

## O que parece melhor no ClawHub

1. Workflow planner duravel para tarefas grandes.
2. Governanca de actions com payload hash e aprovacao forte.
3. Memoria semantica/episodica com recall em camadas.
4. Observabilidade com dashboard de uso, custo, tools e sessoes.
5. Google OAuth pronto como referencia de integracao.
6. Ecossistema/catalogo para descobrir capacidades novas.

## O que o Axel deve manter como melhor

1. Actions locais simples e diretas para Windows.
2. Roteadores e toolsets ajustados ao uso por voz.
3. Foco local-first com Ollama como retaguarda.
4. Briefing, carteira, agenda e HUD personalizados.
5. Controle fino de tarefas pequenas sem arquitetura pesada.

### 1. Provider NVIDIA NIM como fallback de IA

ClawHub lista um plugin NVIDIA NIM Provider com modelos de chat, visao, embeddings e geracao de imagem por endpoints compativeis com OpenAI.

Aplicacao no Axel:

- avaliar NVIDIA API como fallback quando Gemini estiver sem cota, lento ou indisponivel;
- manter Ollama local como retaguarda offline;
- criar um roteador de modelos com prioridade: Gemini, NVIDIA, Ollama;
- registrar motivo do fallback no log de execucao.

### 2. Memoria vetorial e memoria com recall automatico

Ha plugins de memoria com LanceDB, Milvus e camadas persistentes.

Aplicacao no Axel:

- evoluir a memoria longa para busca semantica local;
- separar memoria factual, preferencias, sessoes, decisoes e procedimentos;
- usar recall automatico apenas quando tiver alta relevancia para evitar poluir prompts.

### 3. Google OAuth e calendario real

ClawHub lista plugin de Google Workspace com Gmail, Calendar, Drive, Docs, Sheets e Slides via OAuth.

Aplicacao no Axel:

- usar como referencia para a futura integracao com Google Agenda;
- pensar em OAuth direto, sem depender de gateway de terceiros;
- reaproveitar no briefing, lembretes e agenda de compromissos.

### 4. Canal remoto sem numero de celular

Ha plugins e exemplos de canais como WhatsApp, Slack, Discord, Teams, Google Chat, Matrix e outros. Para o Axel, o objetivo principal e falar com ele remotamente sem depender de numero de celular. A escolha principal sera Telegram Bot.

Aplicacao no Axel:

- priorizar Telegram Bot como canal remoto principal;
- manter Discord Bot apenas como alternativa futura;
- tratar cada canal remoto como uma origem separada, com permissoes e confirmacoes proprias;
- manter leitura/resumo e envio em fluxos diferentes;
- registrar auditoria local de comandos e mensagens enviados por automacao.

### 5. Observabilidade e seguranca

ClawHub lista plugins de diagnostics, OpenTelemetry, Prometheus, preflight security, approval gates e audit trails.

Aplicacao no Axel:

- evoluir `execution_log.jsonl` para metricas de latencia, erro, ferramenta usada e fallback de modelo;
- criar painel de saude com ultimos erros por dominio;
- criar preflight para comandos sensiveis de arquivo, sistema, navegador autenticado e mensagens.

### 6. Toolsets e skills como produto interno

O catalogo separa skills e plugins por categorias. Isso reforca a ideia do Axel ter um catalogo interno de capacidades.

Aplicacao no Axel:

- criar `memory/skills/` para procedimentos reutilizaveis;
- criar uma tela/lista de capacidades instaladas no painel;
- permitir que o Axel diga quais capacidades estao disponiveis, quais estao configuradas e quais precisam de credencial.

## O que evitar

- instalar plugins sem auditoria;
- depender de gateway externo para tarefas locais;
- adicionar canais antes de concluir seguranca e confirmacao;
- transformar o Axel em um marketplace pesado;
- usar memoria vetorial sem controle de relevancia.

## Ordem recomendada

1. NVIDIA API fallback no roteador de modelos.
2. Catalogo interno de capacidades e toolsets.
3. Memoria semantica local.
4. Google Agenda via OAuth.
5. Telegram Bot com confirmacao e auditoria.
6. Observabilidade ampliada no painel de saude.
