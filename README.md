# Axel

Assistente local para Windows com foco em voz, automação de desktop, navegação no navegador e apoio operacional no dia a dia.

O projeto foi pensado para rodar localmente, com Ollama para LLM, Faster-Whisper para transcrição e Piper para TTS. A proposta é ter um assistente útil de verdade, controlando apps, sites, mídia e tarefas práticas sem depender de cloud para tudo.

Opcionalmente, o projeto também pode usar Gemini API como cérebro principal de texto, NVIDIA NIM como segunda opção remota e Ollama local como fallback.

## O que ele faz

- Controle por voz com `--voice` e escuta por botão com `--hotword`
- Abertura e fechamento de aplicativos e sites
- Navegação básica no navegador, leitura de tela e resumos de conteúdo
- Controle de mídia e volume
- Memória local de atalhos, preferências e contexto operacional
- Snapshot local da carteira para consultas rápidas de investimentos
- Interface opcional com `--ui`, HUD em PySide6/WebEngine e paineis internos
- Canal remoto por Telegram Bot com allowlist, polling local e confirmacao segura para midia leve
- AxelBrain 2.0 para decisao, seguranca por canal, historico e diagnosticos
- Modo de performance para reduzir polling, animacoes e custo em notebook medio/fraco
- Logs locais para diagnosticar startup, HUD, voz, actions e tarefas em segundo plano

## Status atual

- Foco principal: automação local e utilidade prática
- Núcleo de actions, roteamento, voz, briefing, carteira, memória e UI modularizados
- Análise de imagem disponível por tela, navegador, clipboard e arquivo quando houver modelo visual configurado
- Suíte de testes `unittest` cobrindo comandos, actions, voz, carteira, UI runtime e fluxos principais
- HUD otimizado para troca rapida entre paineis animados
- AxelBrain 2.0 ativo como nucleo de decisao, contrato de seguranca por canal e introspeccao no HUD
- Telegram Bot ativo como canal remoto principal, com allowlist por `chat_id`, leitura remota e confirmacao por botoes para midia leve
- Painel `Dia`/cockpit diario removido temporariamente do runtime por estabilidade
- WhatsApp local em pausa: base de webhook/allowlist existe, mas integracao real depende de provedor/numero
- Plataforma principal: Windows

## Requisitos

- Windows
- Python 3.11+ recomendado
- [Ollama](https://ollama.com/) rodando localmente

Bibliotecas usadas no projeto:

- `requests`
- `sounddevice`
- `numpy`
- `scipy`
- `faster-whisper`
- `huggingface_hub`
- `pyperclip`
- `rapidocr_onnxruntime`
- `Pillow`
- `opencv-python`

## Instalação

1. Clone o projeto.
2. Crie e ative uma virtualenv.
3. Instale as dependências que você pretende usar.
4. Copie `.env.example` para `.env` e ajuste o que for seu.
5. Inicie o Ollama.

Exemplo no PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install requests sounddevice numpy scipy faster-whisper huggingface_hub pyperclip rapidocr_onnxruntime pillow opencv-python
Copy-Item .env.example .env
```

## Configuração por ambiente

As configurações sensíveis e pessoais agora ficam no `.env`.

Variáveis principais:

- `AXEL_OLLAMA_BASE_URL`
  URL base do Ollama local.

- `AXEL_OLLAMA_TEXT_MODEL`
  Modelo padrão para conversa, planejamento e interpretação.

- `AXEL_OLLAMA_VISION_MODEL`
  Modelo visual opcional.

- `AXEL_GEMINI_API_KEY`
  Chave opcional da Gemini API. Se estiver vazia, o Axel continua 100% no Ollama.

- `AXEL_GEMINI_MODEL`
  Modelo usado para perguntas de conversa mais complexas. Padrão: `gemini-2.5-flash`.

- `AXEL_GEMINI_PRIMARY_TEXT_ENABLED`
  Se ativado, o Gemini vira o modelo principal para chamadas de texto do Axel, com fallback para Ollama se a API falhar.

- `AXEL_NVIDIA_API_KEY`
  Chave opcional da NVIDIA NIM API. Por padrão, entra como segunda opção remota quando Gemini falhar ou não estiver configurado.

- `AXEL_NVIDIA_MODEL`
  Modelo NVIDIA usado no endpoint OpenAI-compatible da NVIDIA. Padrão: `meta/llama-3.1-70b-instruct`.

- `AXEL_NVIDIA_TEXT_FALLBACK_ENABLED`
  Se ativado, tenta NVIDIA depois do Gemini e antes do Ollama local.

- `AXEL_GEMINI_COMPLEX_CHAT_ENABLED`
  Se ativado, o Gemini entra apenas em perguntas mais complexas, analíticas ou opinativas. Comandos operacionais continuam no fluxo normal.

- `AXEL_SUPABASE_REST_URL`
  URL REST do projeto Supabase.

- `AXEL_SUPABASE_PUBLISHABLE_KEY`
  Chave publishable do projeto Supabase.

- `AXEL_SUPABASE_ANON_KEY`
  Chave anon do projeto Supabase.

- `NEXT_PUBLIC_SUPABASE_URL`
  Alias aceito pelo Axel para reaproveitar a URL de projetos front-end com Supabase.

- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
  Alias aceito pelo Axel para reaproveitar a chave publishable de projetos front-end com Supabase.

- `AXEL_SUPABASE_MEMORY_TABLE`
  Nome da tabela usada para sincronizar memórias simples do Axel.

- `AXEL_SUPABASE_SYNC_ENABLED`
  Liga ou desliga a sincronização opcional com Supabase.

- `AXEL_OBSIDIAN_VAULT_PATH`
  Caminho opcional para seu vault do Obsidian. Se ficar vazio, o Axel cria um vault local em `memory/obsidian_vault`.

- `AXEL_OBSIDIAN_SYNC_ENABLED`
  Liga ou desliga o espelhamento das memórias principais em notas Markdown estilo Obsidian.

- `AXEL_INVESTIDOR10_WALLET_URL`
  Seu link direto da carteira no Investidor10. Pode ser um link privado/autenticado ou uma carteira pública.

- `AXEL_WALLET_PLAYWRIGHT_USER_DATA_DIR`
  Opcional. Perfil dedicado do navegador para o Axel ler a carteira privada com Playwright. Rode `.\venv\Scripts\python.exe .\scripts\open_wallet_playwright_profile.py`, faça login no Investidor10 uma vez e use o caminho mostrado nessa variável.

- `AXEL_INVESTMENT_BACKGROUND_REFRESH_ENABLED`
  Liga ou desliga a tentativa de atualizar a carteira em segundo plano ao iniciar. Padrao recomendado: `0`; assim a carteira atualiza sob demanda e nao compete com voz, UI e briefing.

- `AXEL_BRAPI_TOKEN`
  Token opcional da BRAPI para ampliar a cobertura de cotações e fundamentos por ticker, especialmente fora do snapshot da carteira.

- `AXEL_BRAPI_ENABLED`
  Liga ou desliga a tentativa de usar BRAPI antes do fallback atual via Investidor10.

- Clima
  O Axel usa Open-Meteo para consultas de clima. Nessa integração, não é preciso configurar chave.

- `AXEL_NEWSAPI_KEY`
  Chave opcional da NewsAPI para buscar notícias recentes por ativo.

- `AXEL_NEWSAPI_ENABLED`
  Liga ou desliga o uso da NewsAPI nas respostas de fatos relevantes e notícias.

- `AXEL_TELEGRAM_BOT_TOKEN`
  Token do bot criado no BotFather. Fica no `.env`; nao publique esse valor.

- `AXEL_TELEGRAM_ALLOWED_CHAT_IDS`
  Lista de `chat_id`s autorizados a falar com o Axel pelo Telegram, separados por virgula ou ponto e virgula.

- `AXEL_TELEGRAM_POLL_INTERVAL_SECONDS`
  Intervalo do polling local do Telegram. Padrao recomendado: `2`.

- `AXEL_SPOTIFY_CLIENT_ID` e `AXEL_SPOTIFY_CLIENT_SECRET`
  Credenciais opcionais da Spotify Web API para o Axel buscar a faixa certa antes de abrir/tocar.

- `AXEL_SPOTIFY_ACCESS_TOKEN`
  Opcional. Se você gerar um token de usuário com permissão de playback, o Axel também pode mandar tocar via API em vez de só abrir a faixa.

- `AXEL_SPOTIFY_DEVICE_ID`
  Opcional. Permite fixar em qual dispositivo Spotify a reprodução deve começar.

Se essa variável da carteira não estiver preenchida, o Axel ainda abre a área geral do Investidor10, mas não pula direto para o seu link da carteira.

## WhatsApp local em pausa

A base local do WhatsApp existe para consulta via webhook local, com allowlist e token, mas a integracao real esta pausada ate haver um provedor/numero definido.

Variaveis relacionadas:

- `AXEL_WHATSAPP_ALLOWED_SENDERS`
- `AXEL_WHATSAPP_WEBHOOK_TOKEN`
- `AXEL_WHATSAPP_BRIDGE_HOST`
- `AXEL_WHATSAPP_BRIDGE_PORT`

Por seguranca, o modo atual deve permanecer read-only: responder perguntas e consultar o Axel. Envio de mensagens para terceiros precisa de confirmacao explicita e ainda nao deve ser ativado automaticamente.

## Telegram Bot

O Telegram Bot e o canal remoto principal do Axel para falar com ele sem depender de numero de celular.

Configuracao basica:

1. Crie o bot no BotFather.
2. Coloque o token em `AXEL_TELEGRAM_BOT_TOKEN`.
3. Envie `/start` ou uma mensagem para o bot.
4. No Axel, use `descobrir chat id telegram` para listar chats recentes.
5. Coloque seu `chat_id` em `AXEL_TELEGRAM_ALLOWED_CHAT_IDS`.
6. Inicie o bot com `iniciar bot telegram`.

Comandos uteis:

- `status do telegram`
- `descobrir chat id telegram`
- `iniciar bot telegram`
- `simular telegram briefing`

Audio no Telegram:

- O bot reconhece mensagens `voice` e `audio`.
- Quando iniciado pelo polling, ele baixa o arquivo do Telegram e tenta transcrever com Faster-Whisper.
- O texto transcrito entra no mesmo fluxo remoto seguro, com os mesmos bloqueios e confirmacoes.
- Se a transcricao nao estiver disponivel no ambiente, o bot responde explicitamente em vez de tratar audio como mensagem vazia.

Perfil de seguranca atual:

- consultas de leitura podem responder direto no Telegram
- midia leve, como musica e volume, exige botao `Confirmar`/`Cancelar`
- app, janela, URL, clique, digitacao, arquivos, scripts e acoes sensiveis ficam bloqueados no Telegram
- o modo remoto ampliado foi testado e desativado por seguranca

Logs uteis:

- `memory/telegram_bot.log`: eventos do bot, callbacks, bloqueios e confirmacoes

## AxelBrain 2.0

O AxelBrain 2.0 e o nucleo executivo do Axel. Ele fica acima dos roteadores e registra a decisao de cada turno.

Ele produz:

- agente escolhido
- toolset escolhido
- risco
- politica de modelo
- memoria consultada
- proximo passo
- criterios de sucesso
- sinais pos-tarefa
- perfil de seguranca por canal
- guia de execucao por canal

Perfis de seguranca por canal:

- `local_normal`: fluxo local normal, com confirmacao quando necessario
- `remote_read_only`: resposta remota sem acao de escrita
- `remote_light_media_confirmation`: midia leve remota com confirmacao no chat
- `remote_blocked`: comando remoto bloqueado

Comandos de diagnostico:

- `por que o Axel decidiu isso`
- `ultima rota do Axel`
- `historico do axelbrain`
- `insights do axelbrain`

Esses comandos nao executam acoes; eles ajudam a entender como o Axel decidiu, qual detector pegou o comando e quais padroes apareceram na sessao.

## Gemini opcional como principal

Quando `AXEL_GEMINI_API_KEY` estiver preenchida e `AXEL_GEMINI_PRIMARY_TEXT_ENABLED=1`, o Axel passa a usar Gemini como principal nas chamadas de texto. Se `AXEL_NVIDIA_API_KEY` também estiver preenchida e `AXEL_NVIDIA_TEXT_FALLBACK_ENABLED=1`, NVIDIA entra como segunda opção remota antes do Ollama local.

Isso afeta, por exemplo:

- conversa
- opinião
- planejamento
- respostas com leitura de tela já salva
- partes textuais de interpretação e apoio operacional

Exemplos:

- `o que você acha desse cenário?`
- `compare essas duas ideias`
- `isso faz sentido para o longo prazo?`

Fluxo adotado:

- Gemini como principal quando a chave estiver configurada
- NVIDIA como fallback remoto automático se Gemini falhar
- Ollama como fallback local se as APIs remotas falharem
- Se quiser limitar o Gemini depois, basta desligar `AXEL_GEMINI_PRIMARY_TEXT_ENABLED` e manter só o modo complexo

Também existe um uso híbrido nas perguntas sobre a tela: quando você faz uma leitura de página e depois pergunta algo mais amplo, o Axel pode usar a tela como contexto inicial e consultar outras fontes pela web via grounding do Gemini, em vez de ficar preso apenas ao trecho visível.

## Supabase opcional para memória

O Axel continua `local-first`, mas agora pode sincronizar partes úteis da memória com Supabase:

- `ui_state`
- `operational_context`
- `voice_preferences`
- `profile`
- `vision_history`
- `current_topic`

O schema inicial da tabela está em [supabase-schema.sql](C:\Users\almei\Documents\estudos_Programacao\estagiario\docs\supabase-schema.sql).

Fluxo sugerido:

1. Criar a tabela no SQL Editor do Supabase.
2. Preencher as variáveis no `.env`.
3. Rodar o Axel normalmente.

Se o banco estiver indisponível ou a tabela ainda não existir, o Axel continua funcionando localmente.

## Obsidian opcional para memória longa

Além do Supabase, o Axel agora pode espelhar memórias importantes em notas Markdown:

- `Current Topic`
- `Operational Context`
- `Profile`

Esse fluxo ajuda bastante quando você quer:

- ter uma trilha legível do que o Axel está acompanhando
- usar seu próprio vault como memória semântica
- revisar contexto, assunto atual e perfil fora do app

Se `AXEL_OBSIDIAN_VAULT_PATH` estiver vazio, o Axel usa `memory/obsidian_vault` como vault local. Se você apontar para um vault real do Obsidian, as notas passam a aparecer lá automaticamente.

## Como rodar

Modo voz com hotword e interface:

```powershell
.\venv\Scripts\python.exe .\main.py --voice --hotword --ui
```

Modo voz sem UI:

```powershell
.\venv\Scripts\python.exe .\main.py --voice --hotword
```

Teste rápido de voz:

```powershell
.\venv\Scripts\python.exe .\main.py --voice-test
```

Ativar inicializacao com o Windows:

```powershell
.\venv\Scripts\python.exe .\main.py --install-startup
```

Desativar ou verificar:

```powershell
.\venv\Scripts\python.exe .\main.py --uninstall-startup
.\venv\Scripts\python.exe .\main.py --startup-status
```

Quando ativado, o Axel inicia com `--voice --hotword --ui --startup`, entao lembretes vencidos podem ser anunciados por voz mesmo sem voce chamar primeiro.
Ao ligar em modo voz, ele também manda o briefing do dia automaticamente uma vez por dia. Nas outras aberturas do mesmo dia, ele só confirma prontidão. Para abrir sem briefing em algum teste, use `--no-startup-briefing`.
As saudacoes de inicializacao variam entre frases de estudo, codigo e operacao. Para uma saudacao curta em testes, use `--short-startup-greeting`.

Comandos uteis para comecar o dia:

- `rotina diaria`
- `comecar meu dia`
- `saude do Axel`

Calendario:

- `status do calendario`: mostra a ponte externa atual.
- `exportar calendario`: gera `memory/axel_agenda.ics` para importar no Google Agenda, Outlook ou Samsung Calendar.
- `importar calendario C:\caminho\agenda.ics`: importa eventos simples de um arquivo ICS para a agenda local.

Comandos operacionais:

- `python main.py --setup`: revisar configuracao inicial, chaves, Telegram, voz e dependencias
- `python main.py --doctor`: diagnosticar problemas de Telegram, modelos, memoria, HUD, voz e logs
- `python main.py --backup-memory`: criar snapshot dos arquivos criticos de memoria antes de refatoracoes
- `python main.py --update` ou `axel update`: mostrar plano seguro de atualizacao com backup, doctor, git status e testes; ainda nao executa update automatico

Contexto por workspace:

- O Axel carrega instrucoes locais se encontrar `AGENTS.md`, `AXEL.md`, `.agents/AGENTS.md`, `.agents/AXEL.md` ou `.axel/context.md` na raiz do projeto.
- Use [workspace-context-template.md](C:\Users\almei\Documents\estudos_Programacao\estagiario\docs\workspace-context-template.md) como modelo.
- Pergunte `contexto do workspace` para conferir o que foi carregado.

Scripts operacionais:

- `python scripts/axel_action.py --list`: listar actions registradas em JSON.
- `python scripts/axel_action.py memory.backup.list --arg limit=3`: executar action de leitura sem abrir o chat.
- Actions de escrita ficam bloqueadas por padrao; veja [action-rpc.md](C:\Users\almei\Documents\estudos_Programacao\estagiario\docs\action-rpc.md).
- MCP fica reservado como camada futura para ferramentas externas via actions registradas; veja [mcp-integration-plan.md](C:\Users\almei\Documents\estudos_Programacao\estagiario\docs\mcp-integration-plan.md).

Mercado Livre e produtos:

- Quando o Axel lê produtos listados no navegador, ele salva um cache curto em `memory/browser_product_cache.json`.
- Comandos como `produtos recentes`, `mais barato em cache` e `browser_products_cache` reaproveitam esse snapshot sem reler a tela.

Contrato de comandos:

- Os 20 fluxos principais ficam em [golden-commands.md](C:\Users\almei\Documents\estudos_Programacao\estagiario\docs\golden-commands.md).
- A suite `tests/test_golden_commands_v1.py` garante roteamento, normalizacao, validacao e confirmacao esperada para essa lista.
- A suite `tests/test_golden_ui_commands_v2.py` cobre HUD, painel de saude e modos de performance.

Observacao: `rotina diaria` e `comecar meu dia` chamam o briefing/resumo textual. O painel visual `Dia` foi removido temporariamente porque estava causando instabilidade no HUD.

## Interface, HUD e performance

O HUD roda em um processo PySide6 separado e renderiza `ui/axel_web_hud.html` via WebEngine.

Paineis atuais:

- `Texto`
- `Midia`
- `Tempo`
- `Carteira`
- `Noticias`
- `Saude`
- `Estudos`
- `Treino`

Para reduzir travamentos ao trocar rapido entre abas, o HUD usa um modo leve temporario durante a transicao: diminui o ritmo do canvas, oculta detalhes decorativos pesados e aplica somente a ultima aba clicada.

Comandos uteis:

- `mostrar hud`
- `fechar hud`
- `modo economia`
- `modo equilibrado`
- `saude do Axel`

Logs uteis:

- `memory/ui_hud.log`: erros do processo do HUD
- `memory/execution_log.jsonl`: eventos de rota, actions, latencia e respostas
- `memory/background_tasks.jsonl`: historico de tarefas em segundo plano

Baixar uma voz Piper:

```powershell
.\venv\Scripts\python.exe .\main.py --download-piper-voice pt_BR-faber-medium
```

Teste rápido das integrações de memória:

```powershell
.\venv\Scripts\python.exe .\scripts\check_memory_integrations.py
```

Verificacao local de qualidade:

```powershell
.\venv\Scripts\python.exe .\scripts\quality_check.py
```

Para incluir lint com Ruff, instale as dependencias de desenvolvimento e rode:

```powershell
.\venv\Scripts\pip.exe install -r requirements-dev.txt
.\venv\Scripts\python.exe .\scripts\quality_check.py --lint
```

Bootstrap do vault semântico do Obsidian:

```powershell
.\venv\Scripts\python.exe .\scripts\bootstrap_obsidian_vault.py
```

## Fluxo de investimentos

O Axel trabalha com dois modos para investimentos:

1. Atualização da carteira.
   Comandos como `abrir investidor 10`, `atualizar carteira` ou `analisar investimentos` fazem leitura da página e salvam um snapshot local.

2. Consulta rápida local.
   Depois disso, perguntas como `modo investimentos`, `valor investido`, `quanto rendeu?` e `qual meu patrimônio?` são respondidas usando a memória local salva.

3. Resumo diario desde o ultimo snapshot.
   Comandos como `o que mudou na carteira desde ontem`, `resumo diario da carteira` e `mudancas da carteira desde ontem` comparam o historico local salvo em `memory/investment_snapshot_history.json` com o snapshot atual. Quando ainda nao ha dia anterior salvo, o Axel explica a limitacao e usa o snapshot atual para ativos que mais variaram, dividendos, preco-teto e noticias relevantes.

Isso deixa a resposta mais rápida, mas os dados podem estar desatualizados até uma nova atualização.

Também existe um modo híbrido por ticker:

- primeiro o Axel tenta responder pela memória local da carteira
- se faltar contexto do ativo, ele pode consultar BRAPI (quando configurada)
- se ainda faltar cobertura, usa o fallback atual por página do Investidor10
- para notícias e fatos relevantes, o Axel tenta NewsAPI primeiro e usa Gemini como complemento ou fallback

## Estrutura do projeto

- `main.py`: loop principal, voz, UI e execução
- `core/`: roteamento, AxelBrain 2.0, contrato de seguranca, normalizacao e validacao
- `actions/`: catalogo de acoes registradas, risco e confirmacao
- `services/`: briefing, carteira, Telegram, visao e fluxos de dominio
- `tools/`: automacoes e integracoes
- `ui/`: HUD local, painel web e ponte com estado de runtime
- `llm/`: clientes e prompts dos modelos
- `memory/`: estado local e snapshots
- `voice/`: captura de áudio e TTS

## Publicar no GitHub sem vazar dados

Antes de publicar:

- revise seu `.env`
- não suba `venv/`, `.tmp/`, `models/` e arquivos de cache
- não suba `memory/*.json`, `memory/*.jsonl`, `memory/*.tmp`, dumps `.html/.txt` e outros artefatos locais, porque ali podem existir preferências, histórico, contexto e snapshots pessoais
- não suba `memory/obsidian_vault/`, porque o vault local pode guardar memória pessoal do Axel
- veja a política completa em `docs/memory-artifacts-policy.md`

Importante:
Se esses arquivos já estiverem rastreados no Git, o `.gitignore` sozinho não remove do histórico. Nesse caso, limpe o stage antes do primeiro push público.

Exemplo:

```powershell
git rm --cached -r venv .tmp models
git rm --cached memory/*.json
git rm --cached memory/*.tmp
git rm --cached memory/*.html
git rm --cached memory/*.txt
git rm --cached -r memory/obsidian_vault
```

## Licença

Este projeto usa a licença MIT. Veja `LICENSE`.
