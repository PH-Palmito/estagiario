# Axel

Assistente local para Windows com foco em voz, automação de desktop, navegação no navegador e apoio operacional no dia a dia.

O projeto foi pensado para rodar localmente, com Ollama para LLM, Faster-Whisper para transcrição e Piper para TTS. A proposta é ter um assistente útil de verdade, controlando apps, sites, mídia e tarefas práticas sem depender de cloud para tudo.

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

- `AXEL_INVESTIDOR10_WALLET_URL`
  Seu link direto da carteira no Investidor10.

Se essa variável da carteira não estiver preenchida, o Axel ainda abre a área geral do Investidor10, mas não pula direto para o seu link pessoal.

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

## Fluxo de investimentos

O Axel trabalha com dois modos para investimentos:

1. Atualização da carteira
   Comandos como `abrir investidor 10`, `atualizar carteira` ou `analisar investimentos` fazem leitura da página e salvam um snapshot local.

2. Consulta rápida local
   Depois disso, perguntas como `modo investimentos`, `valor investido`, `quanto rendeu?` e `qual meu patrimônio?` são respondidas usando a memória local salva.

Isso deixa a resposta mais rápida, mas os dados podem estar desatualizados até uma nova atualização.

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

Importante:
Se esses arquivos já estiverem rastreados no Git, o `.gitignore` sozinho não remove do histórico. Nesse caso, limpe o stage antes do primeiro push público.

Exemplo:

```powershell
git rm --cached -r venv .tmp models
git rm --cached memory/*.json
```

## Licença

Este projeto usa a licença MIT. Veja `LICENSE`.
