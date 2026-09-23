# Axel

Axel e um assistente pessoal local para Windows. Ele nasceu como um projeto de aprendizado e automacao do dia a dia: ouvir comandos por voz, abrir aplicativos, resumir informacoes, lembrar preferencias, ajudar com estudos, acompanhar tarefas e organizar pequenos fluxos pessoais sem depender de tudo na nuvem.

O foco do projeto e simples: transformar o computador em um ambiente um pouco mais conversavel, pratico e adaptado ao usuario.

## Destaques

- Comandos por texto ou voz.
- Abertura de aplicativos, sites, arquivos e pastas.
- Leitura e resumo de conteudo do navegador ou da tela.
- Controle basico de midia, volume e janelas.
- Memoria local para preferencias, atalhos, rotinas e contexto.
- Briefing diario, lembretes e apoio a estudos.
- HUD opcional para acompanhar estado, midia, clima, carteira, estudos e saude do sistema.
- Integracoes opcionais com Telegram, Spotify, Supabase, Obsidian, Gemini, NVIDIA NIM e Ollama.

## O que torna o Axel diferente

Axel nao e apenas um chatbot em terminal. A ideia e que ele consiga agir no ambiente local com cuidado: entender comandos naturais, escolher uma acao, pedir confirmacao quando houver risco e manter um historico do que decidiu.

Alguns exemplos de uso:

```text
abrir o navegador
resumir essa pagina
tocar uma musica para focar
criar um lembrete para amanha
comecar meu dia
modo economia
saude do Axel
```

Ele tambem tem uma camada de memoria adaptativa. Isso permite frases como:

```text
nao quero aviso de treino hoje
quando eu estiver estudando, seja mais didatico
pare de colocar foco do dia no briefing
volta como era
```

## Status do projeto

Este e um projeto pessoal em evolucao, ainda sem instalador final e sem garantia de compatibilidade fora do meu ambiente principal.

Hoje o Axel funciona melhor em:

- Windows.
- Python 3.11 ou superior.
- Ambiente local com Ollama instalado.
- Uso individual, com configuracoes e memoria mantidas no proprio computador.

Partes do projeto ainda sao experimentais, especialmente automacoes de navegador, canais remotos, leitura de carteira, memoria longa e integracoes externas.

## Instalacao rapida

Clone o repositorio e crie um ambiente virtual:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Depois, edite o arquivo `.env` com as integracoes que quiser usar. Para o modo mais local possivel, deixe as chaves remotas vazias e use o Ollama.

## Como rodar

Modo texto:

```powershell
.\venv\Scripts\python.exe .\main.py
```

Modo voz com escuta por hotword:

```powershell
.\venv\Scripts\python.exe .\main.py --voice --hotword
```

Modo voz com interface:

```powershell
.\venv\Scripts\python.exe .\main.py --voice --hotword --ui
```

Teste rapido de voz:

```powershell
.\venv\Scripts\python.exe .\main.py --voice-test
```

Verificacao do ambiente:

```powershell
.\venv\Scripts\python.exe .\main.py --setup
.\venv\Scripts\python.exe .\main.py --doctor
```

## Inicializacao com o Windows

O Axel pode ser configurado para abrir junto com o Windows:

```powershell
.\venv\Scripts\python.exe .\main.py --install-startup
```

Para desativar:

```powershell
.\venv\Scripts\python.exe .\main.py --uninstall-startup
```

Para conferir o estado:

```powershell
.\venv\Scripts\python.exe .\main.py --startup-status
```

## Configuracao

As configuracoes ficam no arquivo `.env`. As principais sao:

- `AXEL_OLLAMA_BASE_URL`: endereco do Ollama local.
- `AXEL_OLLAMA_TEXT_MODEL`: modelo local usado para texto.
- `AXEL_OLLAMA_VISION_MODEL`: modelo local opcional para visao.
- `AXEL_GEMINI_API_KEY`: chave opcional do Gemini.
- `AXEL_NVIDIA_API_KEY`: chave opcional da NVIDIA NIM.
- `AXEL_SUPABASE_*`: sincronizacao opcional de memoria.
- `AXEL_OBSIDIAN_*`: espelhamento opcional de memoria em notas Markdown.
- `AXEL_TELEGRAM_*`: canal remoto por bot do Telegram.
- `AXEL_SPOTIFY_*`: busca e controle opcional de musica.

O arquivo `.env.example` traz comentarios com mais detalhes sobre cada opcao.

## Recursos principais

**Voz e audio**  
Captura comandos, transcreve fala e responde por TTS. O projeto suporta Faster-Whisper para transcricao e Piper para voz local.

**Automacao local**  
Abre aplicativos, sites e arquivos, controla midia, consulta janela ativa, usa clipboard e executa acoes registradas com politicas de seguranca.

**Navegador e tela**  
Le conteudo visivel, resume paginas, captura contexto do navegador e pode usar modelos visuais quando configurados.

**Memoria local**  
Guarda preferencias, atalhos, lembretes, rotinas, contexto de estudo, historico operacional e snapshots locais.

**HUD**  
Interface opcional com paineis para texto, midia, tempo, carteira, estudos e saude do sistema.

**Canais remotos**  
O Telegram pode funcionar como canal remoto com allowlist. Acoes sensiveis sao bloqueadas ou exigem confirmacao.

## Estrutura do projeto

- `main.py`: entrada principal do assistente.
- `core/`: roteamento, decisoes, seguranca, fluxo de conversa e runtime.
- `actions/`: catalogo de acoes que o Axel pode executar.
- `tools/`: automacoes locais e integracoes.
- `services/`: fluxos maiores, como briefing, Telegram, carteira e notificacoes.
- `voice/`: captura, transcricao e sintese de voz.
- `ui/`: HUD e ponte com a interface.
- `memory/`: estado local, preferencias, snapshots e memorias.
- `docs/`: notas tecnicas, planos e contratos internos.
- `tests/`: testes automatizados.

## Privacidade antes de publicar

Este projeto foi feito para uso pessoal, entao e importante revisar arquivos locais antes de tornar o repositorio publico.

Nao publique:

- `.env`
- `venv/`
- `.tmp/`
- `models/`
- arquivos locais em `memory/` com historico, preferencias, snapshots, logs ou contexto pessoal
- `memory/obsidian_vault/`, se ele contiver notas pessoais

O `.gitignore` ajuda a evitar novos vazamentos, mas nao remove arquivos que ja tenham sido rastreados pelo Git. Antes do primeiro push publico, confira com:

```powershell
git status
git ls-files memory
```

Se algum artefato pessoal aparecer como rastreado, remova do indice antes de publicar.

## Qualidade

Rodar a verificacao local:

```powershell
.\venv\Scripts\python.exe .\scripts\quality_check.py
```

Rodar testes:

```powershell
.\venv\Scripts\python.exe -m unittest
```

## Documentacao tecnica

Alguns detalhes internos ficam em `docs/`, incluindo arquitetura de memoria, actions, contratos de runtime, comandos principais e roadmap.

Arquivos uteis:

- `docs/golden-commands.md`
- `docs/action-rpc.md`
- `docs/memory-architecture.md`
- `docs/memory-artifacts-policy.md`
- `docs/axel-runtime-contracts.md`

## Licenca

Este projeto usa a licenca MIT. Veja `LICENSE`.
