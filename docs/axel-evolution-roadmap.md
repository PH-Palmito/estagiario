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

## Fase 3: Pesquisa com fontes

### Objetivo

Permitir que o Axel responda temas dependentes de atualidade com fundamento.

### Entregas

- modo pesquisa
- busca de fontes atuais
- síntese com citação de origem
- separação entre dado e leitura

### Casos de uso

- “o que você acha disso?”
- “qual cenário parece mais provável?”
- “o que está acontecendo com esse assunto?”
- “quem está liderando essa disputa?”

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

## Fase 4: Investimentos

### Objetivo

Transformar o Axel em um analista pessoal útil, com base nas suas regras.

### Entregas

- carteira local estruturada
- watchlist
- preço-teto por ativo
- critérios por categoria
- comparação entre preço atual e critério pessoal
- resumo de tese e risco

### Perguntas que ele deve responder

- “está abaixo do meu preço-teto?”
- “quanto rendeu?”
- “qual ativo ficou interessante?”
- “quais notícias afetam essa tese?”
- “esse ativo está caro ou barato pelo meu critério?”

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
