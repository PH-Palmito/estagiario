# Axel: o que aproveitar do OpenClaw e onde o Supabase entra

## Resumo direto

OpenClaw faz sentido como referência de arquitetura, não como base para enfiar inteira dentro do Axel agora.

Para o Axel, o melhor caminho é:

1. manter o loop crítico local e rápido
2. copiar padrões bons do OpenClaw
3. usar banco apenas para memória estruturada, sync e observabilidade

Se o objetivo principal continuar sendo voz + Windows + resposta curta + automação local, o banco não deve entrar no caminho quente de captura, transcrição, roteamento e execução.

## O que vale portar do OpenClaw

### 1. Hierarquia de memória

O OpenClaw separa memória por camadas. Isso combina muito com o Axel.

Proposta para o Axel:

- `MEMORY.md`
  fatos duráveis, preferências e decisões estáveis

- `memory/YYYY-MM-DD.md`
  contexto recente e diário

- `WORKING.md`
  estado atual de tarefa longa, gargalos e próximos passos

- `skills/`
  instruções e procedimentos por domínio

Benefício:

- menos perda de contexto
- melhor continuidade entre sessões
- mais clareza entre memória temporária e permanente

### 2. Política de ferramentas por risco

O OpenClaw trata ferramentas como capacidades explícitas, com allow/deny.

No Axel, vale evoluir para classes de risco:

- `safe`
  ler tela, listar apps, resumir página

- `confirm`
  fechar app, apagar arquivo, enviar mensagem, atualizar banco

- `blocked`
  ações perigosas, invasivas, destrutivas ou fora da política

Benefício:

- comportamento mais previsível
- menos chance de ação errada
- mais fácil expor o Axel fora do terminal no futuro

### 3. Skills reais por domínio

Hoje o Axel tem comandos e lógica espalhados. O OpenClaw mostra valor em separar comportamento por skill.

Skills candidatas para o Axel:

- `investimentos`
- `navegação web`
- `código`
- `mídia`
- `produtividade`

Cada skill pode definir:

- comandos aceitos
- contexto necessário
- ferramentas autorizadas
- memória relevante
- respostas de fallback

### 4. Separação entre núcleo, adaptadores e ferramentas

O Axel deve caminhar para três camadas:

- `runtime`
  voz, estado, fila, regras, aprovação

- `adapters`
  UI, terminal, navegador, banco, mensageria futura

- `tools`
  ações concretas no sistema

Benefício:

- menos acoplamento
- mais fácil adicionar WhatsApp, Telegram, app mobile ou painel web
- mais fácil testar

### 5. Observabilidade e trilha de execução

OpenClaw valoriza workspace e memória. Para o Axel, isso pode virar uma trilha clara:

- comando ouvido
- transcrição corrigida
- intenção roteada
- ação executada
- resultado
- tempo gasto
- falha ou confirmação

Isso ajuda muito no ajuste fino da voz e dos comandos.

## O que eu não copiaria agora

### 1. Gateway completo e canais demais

Não vale colocar WhatsApp, Slack, Telegram, dispositivos remotos e nós móveis agora se o foco ainda é desktop local.

### 2. Marketplace amplo de skills

Trazer skill de terceiros cedo demais aumenta risco e complexidade.

### 3. Banco como dependência do loop principal

Se o Axel depender do banco para ouvir, entender e agir, você vai trocar velocidade por fragilidade.

## Onde o Supabase faz sentido

Supabase faz mais sentido como plano de controle e memória estruturada do que como cérebro principal.

Use Supabase para:

- guardar snapshots de carteira
- sincronizar memória entre máquinas
- registrar histórico de comandos
- guardar preferências por usuário
- armazenar tarefas, planos e gargalos
- habilitar painel web futuro

Não use Supabase para:

- decidir comando em tempo real
- depender da rede para cada fala
- bloquear o runtime local se a internet cair

## Arquitetura recomendada

### Modo local-first

Fluxo ideal:

1. o Axel ouve localmente
2. transcreve localmente
3. roteia localmente
4. executa localmente
5. salva localmente
6. sincroniza com banco em segundo plano, quando fizer sentido

Esse é o melhor equilíbrio entre velocidade, privacidade e robustez.

## Como eu usaria o Supabase na prática

### Tabelas iniciais úteis

- `profiles`
  dados básicos do operador e preferências globais

- `voice_preferences`
  hotword, thresholds, voz, estilo

- `command_history`
  frase original, correção, intenção, resultado, duração

- `portfolio_snapshots`
  valor investido, valor atual, rentabilidade, proventos, timestamp, fonte

- `memories`
  memória durável estruturada com tipo, prioridade e fonte

- `tasks`
  backlog do Axel, gargalos, melhorias e status

- `tool_events`
  auditoria de uso de ferramenta

### Recursos do Supabase que mais combinam

- Postgres
  base principal e consultas ricas

- Auth
  útil se o Axel virar multiusuário ou tiver painel web

- Realtime
  útil para painel ao vivo e sincronização de estado

- Storage
  útil se você quiser guardar capturas, áudios, logs ou anexos

- Edge Functions
  útil para jobs e integrações assíncronas

## Melhor ordem para implementar

### Fase 1. Organizar memória local

- criar `WORKING.md`
- separar memória curta e longa
- padronizar snapshots de investimento
- registrar trilha de execução

### Fase 2. Criar abstração de persistência

- interface única de storage
- backend local por arquivo ou SQLite
- backend opcional em Supabase

### Fase 3. Sync opcional com Supabase

- snapshots de investimento
- command history
- tarefas e gargalos

### Fase 4. Painel e automações remotas

- dashboard web
- monitoramento
- comandos vindos de fora do desktop

## Veredito

OpenClaw é útil como inspiração para:

- memória em camadas
- skills
- políticas de ferramentas
- separação de runtime e adaptadores

Supabase é útil se entrar como:

- memória estruturada
- sync opcional
- trilha de execução
- base para painel e multi-dispositivo

Se eu tivesse que resumir em uma frase:

Copie a disciplina arquitetural do OpenClaw e use o Supabase como retaguarda, não como muleta do loop principal.
