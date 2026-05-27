---
title: "Axel Evolution Roadmap"
type: "axel-doc"
topic: "roadmap"
updated_at: "2026-05-25"
tags: ["axel", "roadmap", "architecture"]
---

# Axel Evolution Roadmap

## Visão do produto

O Axel deve evoluir para um mordomo digital local, útil de verdade, com quatro capacidades centrais:

- executar ações no computador
- conversar com naturalidade
- manter memória útil
- pesquisar e opinar com fundamento quando o tema exigir atualidade

Objetivo final:

> Um assistente local que age, pensa, conversa e argumenta bem, sem perder velocidade, controle e custo baixo.

## Princípios de arquitetura

### 1. Local-first

O loop principal deve continuar local:

- ouvir
- transcrever
- entender
- agir
- responder

Nada crítico deve depender de internet.

### 2. Pesquisa sob demanda

Internet entra quando a pergunta exige atualidade:

- notícias
- política
- cotações
- fundamentos
- calendário econômico
- contexto recente

### 3. Memória separada por camadas

- memória imediata da sessão
- memória operacional
- memória durável
- memória estruturada de domínio

### 4. Opinião com honestidade epistemológica

O Axel não deve soar neutro demais nem fingir certeza.

Toda resposta opinativa deve distinguir:

- fato
- interpretação
- incerteza

### 5. Banco como retaguarda

Banco serve para persistência, sync e painel futuro.

Banco não deve estar no caminho quente da execução por voz.

## Fase 1: Base confiável

### Objetivo

Consolidar o Axel como mordomo operacional confiável.

### Entregas

- estabilizar voz e execução de comandos
- consolidar snapshots e memória operacional
- registrar trilha de execução
- reduzir respostas genéricas e falhas de roteamento
- melhorar recuperação de contexto recente

### Definição de pronto

- abrir, fechar, focar, navegar e ler tela com confiabilidade
- histórico básico de comando e resposta disponível
- menos ambiguidade entre modo conversa e modo comando

### Itens técnicos

- `execution_log.jsonl` ou equivalente
- `WORKING.md` para estado atual de evolução
- separação clara entre eventos de voz, intenção e ação
- padronização de mensagens de erro e fallback

## Fase 2: Conversa e opinião

### Objetivo

Fazer o Axel conversar melhor e formular opiniões úteis sobre assuntos gerais.

### Entregas

- modo de resposta opinativa
- distinção entre resposta factual e resposta interpretativa
- respostas curtas, mais humanas e menos aleatórias
- follow-up mais coerente
- variações de fala para o Axel inteiro, com cadência diferente por contexto

### Formato ideal de resposta

Estrutura interna:

- o que sei
- minha leitura
- onde estou inferindo

### Definição de pronto

Ao perguntar algo aberto, o Axel:

- não responde como suporte engessado
- não alucina conversa
- dá uma leitura curta e honesta
- admite quando está inferindo

### Itens técnicos

- novo modo de prompt para opinião
- separação `chat factual` e `chat interpretativo`
- memória curta de contexto conversacional
- heurística para detectar pedido de opinião
- biblioteca global de variações de resposta por contexto

## Fase 3: Pesquisa com fontes

### Objetivo

Permitir que o Axel responda temas dependentes de atualidade com fundamento.

### Entregas

- modo pesquisa
- busca de fontes atuais
- síntese com citação de origem
- separação entre dado e leitura
- respostas úteis sobre clima e contexto operacional do dia
- agenda local conectada ao briefing diário
- suporte futuro a mapa geográfico consultável

### Casos de uso

- “o que você acha disso?”
- “qual cenário parece mais provável?”
- “o que está acontecendo com esse assunto?”
- “quem está liderando essa disputa?”
- “como está o clima hoje?”
- “vai chover?”
- “mostrar no mapa”
- “onde fica isso?”

### Definição de pronto

Em assuntos atuais, o Axel:

- busca fontes
- resume pontos relevantes
- dá uma leitura própria baseada nelas
- sinaliza incerteza quando necessário

### Itens técnicos

- camada `research`
- classificador de pergunta dependente de atualidade
- resposta com seções internas:
  - fatos verificados
  - leitura
  - limites
- integração com clima atual e previsão curta
- camada futura de mapa geográfico e localização contextual

## Fase 4: Investimentos

### Objetivo

Transformar o Axel em um analista pessoal útil, com base nas suas regras.

### Entregas

- carteira local estruturada
- watchlist
- preço-teto por ativo
- preço-teto automático com margem de segurança configurável
- critérios por categoria
- comparação entre preço atual e critério pessoal
- resumo de tese e risco
- acompanhamento de notícias importantes por ativo
- monitoramento proativo de preço, dividendos, volatilidade e fatos relevantes

### Perguntas que ele deve responder

- “está abaixo do meu preço-teto?”
- “quanto rendeu?”
- “qual ativo ficou interessante?”
- “quais notícias afetam essa tese?”
- “houve alguma notícia importante sobre meus ativos?”
- “esse ativo está caro ou barato pelo meu critério?”
- “mercado abriu como hoje?”
- “algum ativo meu merece atenção agora?”
- “houve dividendos creditados?”
- “algum fundo está com vacância aumentando?”

### Definição de pronto

O Axel deixa de só ler a página e passa a:

- comparar com sua regra
- resumir cenário
- apontar divergência entre tese e preço

### Itens técnicos

- schema de ativos
- schema de critérios pessoais
- snapshots históricos
- normalização de preço, rentabilidade e proventos
- camada de `investment_reasoning`
- coleta de notícias relevantes por ticker com priorização por impacto
- camada de `portfolio_monitoring`
- biblioteca de respostas com variações por contexto

## Fase 5: Persistência estruturada

### Objetivo

Criar uma camada de storage para evoluir sem acoplamento.

### Entregas

- interface única de persistência
- backend local
- backend opcional remoto
- sync assíncrono

### Onde o Supabase entra

O Supabase é forte para:

- `profiles`
- `voice_preferences`
- `command_history`
- `portfolio_snapshots`
- `memories`
- `tasks`
- `tool_events`

### Definição de pronto

- o Axel continua funcionando offline
- sync remoto é opcional
- histórico e memória podem ser consultados fora da máquina

### Itens técnicos

- `storage/base.py`
- `storage/local_store.py`
- `storage/supabase_store.py`
- fila de sync
- política de conflito simples

## Fase 6: Skills, risco e autonomia

### Objetivo

Tornar o Axel mais modular e mais autônomo sem perder controle.

### Entregas

- skills por domínio
- políticas de ferramenta por risco
- rotinas agendadas
- propostas automáticas de melhoria
- backlog interno de evolução
- mapa navegável de capacidades e estados do Axel
- modo de mapa geográfico para contexto visual e localização

### Skills candidatas

- `geral`
- `navegação`
- `investimentos`
- `código`
- `mídia`
- `produtividade`

### Política de risco

- `safe`
- `confirm`
- `blocked`

### Definição de pronto

- o Axel sabe qual skill usar
- o Axel sabe quando pedir confirmação
- o Axel pode sugerir melhorias e próximos passos com mais consistência

## O que pode usar OpenClaw ou Paperclip no futuro

### OpenClaw

Útil como inspiração para:

- memória em camadas
- estrutura de skills
- organização do workspace

### Paperclip

Útil como camada futura para:

- coordenação entre agentes
- orquestração de tarefas
- heartbeats
- budgets
- governance

### Decisão

Não usar nenhum dos dois no núcleo do Axel agora.

Se forem entrar, entram como referência ou camada externa, não como substituto do loop local.

## Prioridades operacionais atuais - revisao tecnica 2026-05-25

Esta lista registra a fila pratica da revisao critica do projeto Axel/Jarvis.
Progresso geral estimado nesta rodada: 100% dos blocos automatizaveis desta rodada.

### Blocos concluidos nesta rodada

- [x] Quebrar fluxo principal em modulos menores: estado, startup, loop principal e turn flow.
- [x] Criar resultado estruturado para actions e executor.
- [x] Criar politica de permissao e risco por action.
- [x] Centralizar roteamento com registry, grupos e telemetria de rota.
- [x] Migrar memorias locais para escrita atomica com locks por arquivo.
- [x] Criar backup e restore de memoria com confirmacao forte.
- [x] Corrigir inicializacao do Axel com Windows.
- [x] Separar log de diagnostico de startup e log de saida do processo.
- [x] Expor saude de startup no painel de diagnostico.
- [x] Criar telemetria de latencia por action.
- [x] Criar recomendacoes de performance para cache/background.
- [x] Registrar conselho preventivo de performance antes de actions pesadas.
- [x] Criar runtime de tarefas em segundo plano.
- [x] Expor status de tarefas em segundo plano por action e comando natural.
- [x] Adicionar background opt-in para briefing.
- [x] Adicionar background opt-in para visao e carteira.
- [x] Criar consulta do ultimo resultado de background.
- [x] Persistir historico de background em JSONL.
- [x] Limitar crescimento de `memory/background_tasks.jsonl`.
- [x] Criar cache TTL para `daily_briefing`.
- [x] Criar cache TTL para resumo e relatorio de carteira.
- [x] Criar cache TTL para ultima analise visual com hash de tela.
- [x] Separar tarefas bloqueantes seguras para background por padrao.
- [x] Criar modo economia para notebook medio/fraco.
- [x] Padronizar mensagens de erro para actions de navegador, rede, visao e arquivo.
- [x] Criar diagnostico e alerta claro para atalho de startup desatualizado.
- [x] Documentar contratos de action, router, memory e background.
- [x] Criar camada inicial `services/` para briefing, visao e carteira.
- [x] Criar interface unica de storage JSON local com backend plugavel.
- [x] Separar politica de cache em modulo proprio com TTLs canonicos.
- [x] Conectar background com notificacao visual automatica ao terminar tarefa.
- [x] Melhorar painel de saude com tarefas recentes de background, duracao e erro/resumo.
- [x] Preparar fila/politica de notificacao por voz opcional para tarefas importantes.
- [x] Criar diagnostico de encoding/mojibake para docs e textos de fala antes de corrigir em lote.
- [x] Criar sandbox logico para classificar arquivo, processo, navegador e dry-run recomendado.
- [x] Documentar checklist de verificacao real de startup apos reiniciar o Windows.
- [x] Validar em reboot real que o Axel inicia sozinho com o Windows.
- [x] Corrigir bloco de encoding/mojibake no runtime de TTS.
- [x] Consumir fila de notificacoes por voz no runtime, respeitando modo foco/silencioso.
- [x] Medir tempo de STT, TTS, roteamento, action e output separadamente.
- [x] Criar dry-run real para rotinas novas antes da execucao.
- [x] Reduzir polling de UI/arquivos quando o Axel estiver em modo silencioso.
- [x] Criar roteador de intencoes com niveis: comando direto, pergunta, tarefa composta, conversa.
- [x] Criar selecao explicita de ferramenta para IA local/nuvem.
- [x] Exigir confirmacao forte para deletar, sobrescrever, restaurar memoria, rodar script e mexer em carteira.
- [x] Registrar trilha de auditoria para actions sensiveis.
- [x] Criar allowlist de automacoes confiaveis.
- [x] Separar comando simples de raciocinio complexo.
- [x] Criar memoria curta da sessao e memoria longa consultavel com score.
- [x] Criar aprendizado de rotinas por repeticao com sugestao antes de automatizar.
- [x] Evitar chamadas bloqueantes no caminho quente da voz.
- [x] Personalidade com respostas curtas, contextuais e menos repetitivas.
- [x] Briefing ao ligar o PC com agenda, clima, carteira e foco do dia.
- [x] Agenda real sincronizada com briefing e lembretes.
- [x] Painel de estudos com revisoes, metas e progresso.
- [x] Monitor proativo de carteira com fatos relevantes e preco-teto.
- [x] Base local do WhatsApp como canal de consulta com allowlist e bloqueio de escrita.
- [x] Ponte WhatsApp local com status, start e simulacao sem nuvem.
- [x] Painel unificado de rotina diaria com agenda, lembretes, estudos, carteira, clima e saude.

### Prioridade imediata

1. Validar ponte local com POST real no endpoint `127.0.0.1`.
2. Multiagente supervisionado para pesquisa, codigo e automacoes longas.
3. Pesquisa com fontes atuais e citacao de origem.
4. Sync remoto opcional para memorias, tarefas e snapshots.
5. Integracao WhatsApp real quando houver provedor/numero definido.

### Correcoes urgentes restantes

- [x] Verificar fluxo real de startup apos reiniciar o Windows.
- [x] Criar alerta claro quando o atalho de startup estiver desatualizado.
- [x] Garantir que actions sensiveis nunca sejam chamadas por background generico.
- [x] Padronizar mensagens de erro para actions que dependem de navegador, rede, visao ou arquivo.
- [x] Revisar arquivos com encoding quebrado em docs e textos de fala.

### Melhorias de performance

- [x] Criar cache TTL para `daily_briefing`.
- [x] Criar cache TTL para resumo de carteira.
- [x] Criar cache TTL para ultima analise visual.
- [x] Medir tempo de STT, TTS, roteamento, action e output separadamente.
- [x] Evitar chamadas bloqueantes no caminho quente da voz.
- [x] Mover actions pesadas seguras para background automaticamente.
- [x] Reduzir polling de UI/arquivos quando o Axel estiver em modo silencioso.
- [x] Adicionar modo leve para reduzir animacoes e tarefas recorrentes.

### Melhorias de arquitetura

- [x] Separar contrato de background entre fila, persistencia e notificacao.
- [x] Criar camada `services/` para orquestradores de briefing, visao e carteira.
- [x] Expandir camada `services/` para voz.
- [x] Consumir fila falavel por runtime de voz sem interromper modo foco/silencioso.
- [x] Criar interface unica de storage para JSON local e backend remoto futuro.
- [x] Separar politicas: permissao, performance, cache e risco.
- [x] Documentar contratos de action, router, memory e background.

### Melhorias de agente

- [x] Criar roteador de intencoes com niveis: comando direto, pergunta, tarefa composta, conversa.
- [x] Criar selecao explicita de ferramenta para IA local/nuvem.
- [x] Separar comando simples de raciocinio complexo.
- [x] Criar memoria curta da sessao e memoria longa consultavel com score.
- [x] Criar aprendizado de rotinas por repeticao com sugestao antes de automatizar.

### Melhorias Jarvis/UX

- [x] Briefing ao ligar o PC com agenda, clima, carteira e foco do dia.
- [x] HUD com painel de tarefas, saude do sistema, voz, agenda e carteira.
- [x] Modo escuta, modo silencioso e modo foco mais visiveis.
- [x] Alertas inteligentes sem interromper trabalho importante.
- [x] Personalidade com respostas curtas, contextuais e menos repetitivas.

### Automacao e seguranca

- [x] Criar sandbox logico para comandos de arquivo, processo e navegador.
- [x] Exigir confirmacao forte para deletar, sobrescrever, restaurar memoria, rodar script e mexer em carteira.
- [x] Registrar trilha de auditoria para actions sensiveis.
- [x] Criar allowlist de automacoes confiaveis.
- [x] Criar dry-run real para rotinas novas antes da execucao.

### Ideias futuras avancadas

- [x] Monitor proativo de carteira com fatos relevantes e preco-teto.
- [x] Agenda real sincronizada com briefing e lembretes.
- [x] Painel de estudos com revisoes, metas e progresso.
- [ ] Integracao WhatsApp com leitura/resumo/envio mediante confirmacao.
- [ ] Multiagente supervisionado para pesquisa, codigo e automacoes longas.

## Prioridade recomendada

### Ordem estratégica

1. Fase 2
2. Fase 3
3. Fase 4
4. Fase 5
5. Fase 6

### Motivo

O maior salto de valor para o Pedro hoje está em:

- conversa melhor
- opinião melhor
- pesquisa com base real
- ajuda útil em investimentos

## Backlog inicial sugerido

### Curto prazo

- criar `WORKING.md`
- criar trilha de execução
- criar modo opinativo
- criar classificador de pergunta factual vs opinativa
- criar camada de pesquisa

### Médio prazo

- guardar watchlist e preço-teto
- criar memória estruturada de investimentos
- criar storage abstrato
- plugar Supabase como backend opcional

### Longo prazo

- painel
- sync multi-dispositivo
- skills modulares
- autonomia supervisionada

## Métrica de sucesso

O Axel está evoluindo bem quando:

- você usa no dia a dia sem medo
- ele conversa sem parecer aleatório
- ele opina sem parecer arrogante ou vazio
- ele responde com fundamento quando o tema exige atualidade
- ele ajuda financeiramente sem virar um guru falso
