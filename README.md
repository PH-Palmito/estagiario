# Axel

Assistente local para Windows com foco em voz, automação de desktop, navegação no navegador e apoio operacional no dia a dia.

O projeto foi pensado para rodar localmente, com Ollama para LLM, Faster-Whisper para transcrição e Piper para TTS. A proposta é ter um assistente útil de verdade, controlando apps, sites, mídia e tarefas práticas sem depender de cloud para tudo.

Opcionalmente, o projeto também pode usar Gemini API como cérebro principal de texto, mantendo o Ollama local como fallback.

## O que ele faz

- Controle por voz com `--voice` e escuta por botão com `--hotword`
- Abertura e fechamento de aplicativos e sites
- Navegação básica no navegador, leitura de tela e resumos de conteúdo
- Controle de mídia e volume
- Memória local de atalhos, preferências e contexto operacional
- Snapshot local da carteira para consultas rápidas de investimentos
- Interface opcional com `--ui`

## Status atual

- Foco principal: automação local e utilidade prática
- Análise de imagem: pausada por enquanto para economizar recurso
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
  Opcional. Perfil dedicado do navegador para o Axel ler a carteira privada com Playwright. Rode `.\venv\Scripts\python.exe .\scripts\open_wallet_playwright_profile.py`, faca login no Investidor10 uma vez e use o caminho mostrado nessa variavel.

- `AXEL_BRAPI_TOKEN`
  Token opcional da BRAPI para ampliar a cobertura de cotações e fundamentos por ticker, especialmente fora do snapshot da carteira.

- `AXEL_BRAPI_ENABLED`
  Liga ou desliga a tentativa de usar BRAPI antes do fallback atual via Investidor10.

- Clima
  O Axel usa Open-Meteo para consultas de clima. Nessa integraçao, nao e preciso configurar chave.

- `AXEL_NEWSAPI_KEY`
  Chave opcional da NewsAPI para buscar notícias recentes por ativo.

- `AXEL_NEWSAPI_ENABLED`
  Liga ou desliga o uso da NewsAPI nas respostas de fatos relevantes e notícias.

- `AXEL_SPOTIFY_CLIENT_ID` e `AXEL_SPOTIFY_CLIENT_SECRET`
  Credenciais opcionais da Spotify Web API para o Axel buscar a faixa certa antes de abrir/tocar.

- `AXEL_SPOTIFY_ACCESS_TOKEN`
  Opcional. Se você gerar um token de usuário com permissão de playback, o Axel também pode mandar tocar via API em vez de só abrir a faixa.

- `AXEL_SPOTIFY_DEVICE_ID`
  Opcional. Permite fixar em qual dispositivo Spotify a reprodução deve começar.

Se essa variável da carteira não estiver preenchida, o Axel ainda abre a área geral do Investidor10, mas não pula direto para o seu link da carteira.

## Gemini opcional como principal

Quando `AXEL_GEMINI_API_KEY` estiver preenchida e `AXEL_GEMINI_PRIMARY_TEXT_ENABLED=1`, o Axel passa a usar Gemini como principal nas chamadas de texto e deixa o Ollama como fallback.

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
- Ollama como fallback automático se a API falhar
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

Baixar uma voz Piper:

```powershell
.\venv\Scripts\python.exe .\main.py --download-piper-voice pt_BR-faber-medium
```

Teste rápido das integrações de memória:

```powershell
.\venv\Scripts\python.exe .\scripts\check_memory_integrations.py
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

Isso deixa a resposta mais rápida, mas os dados podem estar desatualizados até uma nova atualização.

Também existe um modo híbrido por ticker:

- primeiro o Axel tenta responder pela memória local da carteira
- se faltar contexto do ativo, ele pode consultar BRAPI (quando configurada)
- se ainda faltar cobertura, usa o fallback atual por página do Investidor10
- para notícias e fatos relevantes, o Axel tenta NewsAPI primeiro e usa Gemini como complemento ou fallback

## Estrutura do projeto

- `main.py`: loop principal, voz, UI e execução
- `core/`: roteamento, normalização e validação
- `tools/`: automações e integrações
- `llm/`: clientes e prompts dos modelos
- `memory/`: estado local e snapshots
- `voice/`: captura de áudio e TTS

## Publicar no GitHub sem vazar dados

Antes de publicar:

- revise seu `.env`
- não suba `venv/`, `.tmp/`, `models/` e arquivos de cache
- não suba `memory/*.json`, porque ali podem existir preferências, histórico, contexto e snapshots pessoais
- não suba `memory/obsidian_vault/`, porque o vault local pode guardar memória pessoal do Axel

Importante:
Se esses arquivos já estiverem rastreados no Git, o `.gitignore` sozinho não remove do histórico. Nesse caso, limpe o stage antes do primeiro push público.

Exemplo:

```powershell
git rm --cached -r venv .tmp models
git rm --cached memory/*.json
git rm --cached -r memory/obsidian_vault
```

## Licença

Este projeto usa a licença MIT. Veja `LICENSE`.
