---
title: "Hermes Agent Lessons for Axel"
type: "axel-doc"
topic: "agent-architecture"
updated_at: "2026-05-28"
tags: ["axel", "hermes", "agent", "memory", "skills"]
source:
  - "https://github.com/NousResearch/hermes-agent"
  - "https://hermes-agent.nousresearch.com/docs/"
  - "https://hermes-agent.org/pt/"
---

# Hermes Agent Lessons for Axel

## Resumo

O Hermes Agent e uma boa referencia para evoluir o Axel, mas nao deve ser copiado inteiro. O valor principal esta nas ideias de arquitetura: memoria curta curada, busca de sessoes, skills como memoria procedural, toolsets por contexto e um orquestrador central de decisao.

O Axel deve continuar local-first, rapido por voz e integrado ao Windows. As ideias do Hermes entram como inspiracao para deixar o Axel mais coerente, lembrando melhor, escolhendo ferramentas com mais criterio e aprendendo procedimentos reutilizaveis.

## Confirmacao pelo site oficial em portugues

O site `hermes-agent.org/pt` reforca pontos importantes para o Axel:

- Hermes se posiciona como agente auto-hospedado, com memoria persistente, criacao automatica de habilidades e gateway multiplataforma.
- O gateway inclui Telegram, Discord, Slack, WhatsApp, Signal e CLI; para o Axel, Telegram Bot segue como canal remoto principal.
- O sistema de habilidades usa `SKILL.md` portatil e compativel com hubs de skills; isso combina com `memory/skills/` no Axel.
- O Hermes suporta automacoes agendadas, sub-agentes paralelos, navegador, execucao local, Docker, SSH e endpoints compativeis com OpenAI.
- O README atual descreve suporte nativo ao Windows para CLI, gateway, TUI e tools; apenas o painel de chat no dashboard ainda depende de WSL2 por usar POSIX PTY. O Axel deve aproveitar ideias mantendo sua execucao nativa Windows/local-first.

## Segunda revisao do repositorio

A revisao do README do `NousResearch/hermes-agent` mostrou ideias adicionais que ainda nao estavam fortes no plano do Axel:

- interface de terminal/TUI com autocomplete, historico, interrupcao e streaming de output;
- comandos compartilhados entre CLI e gateway remoto: `/new`, `/reset`, `/model`, `/retry`, `/undo`, `/compress`, `/usage`, `/insights`, `/skills`, `/stop`, `/status`;
- transcricao de audio/voice memo no gateway de mensagens;
- continuidade de conversa entre CLI, Telegram e outros canais;
- `hermes setup`, `hermes update` e `hermes doctor` como padrao de setup, atualizacao e diagnostico;
- MCP integration para conectar servidores externos sem acoplar tudo no nucleo;
- context files como `AGENTS.md` para moldar conversas por projeto/workspace;
- scripts Python que chamam tools via RPC, reduzindo custo de contexto em pipelines repetidos;
- terminal backends locais/remotos, incluindo Docker, SSH, Modal e Daytona;
- batch trajectory generation e trajectory compression para gerar/evoluir datasets de comportamento.

Aplicacao no Axel:

- criar comandos naturais e/ou slash commands para reset, retry, undo, usage, insights, skills, stop e status;
- no Telegram Bot, aceitar audio curto e transcrever como entrada de voz remota;
- criar `axel setup`, `axel doctor` e, no futuro, `axel update`;
- avaliar MCP como camada futura para integrar ferramentas externas sem acoplamento direto;
- adotar arquivos de contexto por workspace, inspirados em `AGENTS.md`;
- criar scripts operacionais que executem tools/actions por RPC local quando um fluxo repetido ficar caro em contexto;
- deixar backends remotos e geracao de trajetorias como pesquisa futura, nao prioridade imediata.

## O que aproveitar

### 1. Memoria curta curada

Inspiracao: Hermes separa memoria do agente e perfil do usuario em arquivos pequenos, sempre injetaveis no contexto.

Aplicacao no Axel:

- criar `memory/core_memory.md` para fatos operacionais estaveis do Axel;
- criar `memory/user_profile.md` para preferencias e dados estaveis do operador;
- manter limite rigido de tamanho;
- criar rotina de consolidacao quando a memoria crescer demais;
- usar essas memorias como contexto prioritario antes da memoria longa.

Beneficio esperado:

- respostas mais consistentes;
- menos dependencia de busca textual na memoria longa;
- melhor continuidade entre sessoes.

### 2. Busca de sessoes antigas

Inspiracao: Hermes registra sessoes e permite pesquisar conversas antigas.

Aplicacao no Axel:

- salvar turnos relevantes em SQLite;
- usar FTS5 para busca local;
- criar comando tipo "lembra quando falamos sobre ...";
- permitir que o briefing e a conversa consultem sessoes recentes quando fizer sentido.

Beneficio esperado:

- o Axel passa a recuperar contexto real de conversas passadas;
- menos necessidade de transformar tudo manualmente em memoria permanente;
- melhor continuidade para projetos longos.

### 3. Skills como memoria procedural

Inspiracao: Hermes trata skills como conhecimento de "como fazer", nao apenas como fatos.

Aplicacao no Axel:

- criar pasta `memory/skills/`;
- cada skill deve ter `SKILL.md`, gatilhos, passos, riscos, exemplos e comandos relacionados;
- comecar com skills para briefing, noticias da carteira, avaliacao de projeto, leitura visual, uso do navegador e rotinas de voz;
- permitir que o Axel sugira criar ou atualizar skill quando repetir o mesmo procedimento.

Beneficio esperado:

- aprendizado reutilizavel;
- menos regras espalhadas;
- evolucao mais organizada do comportamento.

### 4. Toolsets por contexto

Inspiracao: Hermes agrupa ferramentas por capacidades e contexto de uso.

Aplicacao no Axel:

- criar uma politica de toolsets por modo:
  - `voz_rapida`: comandos seguros, curtos e locais;
  - `programacao`: arquivos, terminal, analise de codigo e testes;
  - `carteira`: investimentos, noticias, dividendos e alertas;
  - `navegador`: leitura, clique, busca, resumo e automacao web;
  - `sistema`: apps, janelas, teclado, audio e futuro controle de LEDs;
  - `pesquisa`: web, fontes, sintese e opiniao fundamentada.
- expor quais toolsets estao ativos no painel de saude do Axel.

Beneficio esperado:

- menos erro por ferramenta errada;
- melhor seguranca;
- respostas mais previsiveis por contexto.

### 5. Orquestrador central

Inspiracao: Hermes concentra loop de agente, montagem de contexto, escolha de ferramentas, execucao e persistencia.

Aplicacao no Axel:

- criar `core/axel_brain.py` ou `core/decision_orchestrator.py`;
- entrada: texto do usuario, origem, estado de voz/UI, contexto atual, memoria relevante, ferramentas candidatas e risco;
- saida: plano de decisao com `intent`, `confidence`, `toolset`, `needs_confirmation`, `memory_updates` e `response_mode`;
- manter roteadores atuais como detectores especializados, mas colocar uma camada de julgamento acima deles.

Beneficio esperado:

- o Axel deixa de parecer um conjunto de regras e passa a agir como uma cabeca unica;
- melhora continuidade, seguranca e escolha de ferramenta;
- facilita testar inteligencia do Axel com cenarios reais.

## O que nao trazer agora

- subagentes complexos;
- arquitetura multi-plataforma completa;
- gateway cloud/VPS;
- auto-modificacao sem revisao;
- qualquer fluxo que aumente latencia no modo voz;
- dependencias pesadas que prejudiquem o uso local no Windows.

## Ordem recomendada de implementacao

1. Criar memoria curta curada: `core_memory.md` e `user_profile.md`.
2. Criar busca de sessoes com SQLite/FTS5.
3. Criar formato inicial de skills do Axel.
4. Criar toolsets por contexto e ligar ao painel de saude.
5. Criar `DecisionOrchestrator` como camada acima dos roteadores.
6. Integrar aprendizado: quando um procedimento se repetir, sugerir criar/atualizar skill.

## Segunda camada util do Hermes

Depois do nucleo acima, ainda vale guardar estas ideias como evolucao futura:

1. Painel visual para aprovar/rejeitar skills sugeridas.
2. Memoria episodica com resumo automatico por sessao.
3. Autoavaliacao pos-tarefa: registrar se funcionou, falhou ou precisa ajuste.
4. Ranking de skills, toolsets e agentes por sucesso e utilidade.
5. Execucao multiagente real com handoff entre especialistas.
6. Biblioteca de ferramentas modular por agente/contexto.
7. Planejamento longo com checkpoints e retomada.

## Criterio de sucesso

O aproveitamento do Hermes so vale a pena se o Axel ficar:

- mais rapido de decidir;
- mais facil de testar;
- mais lembrado entre sessoes;
- mais seguro ao executar comandos;
- mais coerente no briefing, na carteira, na agenda e no uso diario por voz.
