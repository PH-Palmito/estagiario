import json
import re

from llm.ollama_client import ask_model


PLANNER_PROMPT = """
Voce e um planejador de acoes para um assistente local.

Sua tarefa e converter o pedido do usuario em uma LISTA JSON de acoes permitidas.

Acoes permitidas:
- open_app
- close_app
- open_url
- run_script
- list_files
- create_file
- write_file
- read_file
- answer_only

Regras:
- Responda SOMENTE com JSON valido.
- A resposta deve ser uma lista JSON.
- Nao use markdown.
- Nao escreva explicacoes.
- Nao invente acoes fora da lista permitida.
- Se for abrir ou fechar um app, use nomes simples como:
  - "bloco de notas"
  - "calculadora"
  - "spotify"
- Se for pesquisa web, use open_url com URL de busca do Google.
- Se o usuario pedir para escrever em arquivo, use:
  {
    "intent": "write_file",
    "target": "nome.txt",
    "content": "conteudo"
  }
- Se nao houver acao executavel e for so pergunta, use:
  {
    "intent": "answer_only",
    "response": "..."
  }

Exemplo de saida:
[
  {"intent": "close_app", "target": "spotify"},
  {"intent": "open_app", "target": "bloco de notas"}
]
"""


ALLOWED_INTENTS = {
    "open_app",
    "close_app",
    "open_url",
    "run_script",
    "list_files",
    "create_file",
    "write_file",
    "read_file",
    "answer_only",
}

LOCAL_STEP_PATTERN = re.compile(
    r"\s*(?:,|\be depois\b|\bdepois\b|\bem seguida\b|\bentao\b|\bentão\b|\be\b)\s+"
    r"(?=(?:abra|abre|abrir|abri|abriu|abrei|inicie|iniciar|feche|fechar|fecha|encerre|encerrar|"
    r"termine|terminar|play|pausa|pausar|pause|continua|continuar|toca|tocar|liga|ligar|ligue|ativa|ativar|ative|desliga|desligar|desligue|desativa|desativar|desative|pesquise|crie|escreva|leia|rode|execute|executar|troca|troque|vai|"
    r"foca|focar|minimiza|minimize|maximiza|maximize|restaura|restaure)\b)",
    flags=re.IGNORECASE,
)

MEDIA_ACTION_WORDS = {
    "play",
    "pausa",
    "pausar",
    "pause",
    "continua",
    "continuar",
    "toca",
    "tocar",
}

MEDIA_TARGET_WORDS = {
    "spotify",
    "youtube",
    "you",
    "chrome",
    "navegador",
}


def extract_json_array(text: str):
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return None

    return match.group(0)


def validate_step(step: dict):
    if not isinstance(step, dict):
        return None

    intent = step.get("intent")
    if intent not in ALLOWED_INTENTS:
        return None

    return {
        "intent": intent,
        "target": step.get("target"),
        "content": step.get("content"),
        "response": step.get("response"),
    }


def plan_actions(user_input: str):
    try:
        raw = ask_model(f"{PLANNER_PROMPT}\n\nPedido do usuario: {user_input}")
    except Exception:
        return None

    json_text = extract_json_array(raw)

    if not json_text:
        return None

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, list):
        return None

    validated = []
    for step in data:
        cleaned = validate_step(step)
        if cleaned:
            validated.append(cleaned)

    return validated or None


def split_local_steps(user_input: str):
    text = user_input.strip()
    if not text:
        return []

    parts = re.split(LOCAL_STEP_PATTERN, text)
    parts = [part.strip(" ,.") for part in parts if part and part.strip(" ,.")]
    repaired = []
    index = 0

    while index < len(parts):
        current = parts[index]
        current_lower = current.lower().strip()
        next_part = parts[index + 1] if index + 1 < len(parts) else ""
        next_lower = next_part.lower().strip()

        if current_lower in MEDIA_ACTION_WORDS and next_lower in MEDIA_TARGET_WORDS:
            repaired.append(f"{current} {next_part}")
            index += 2
            continue

        repaired.append(current)
        index += 1

    return repaired


def looks_like_multi_step_request(user_input: str):
    text = user_input.lower().strip()

    triggers = [
        " e depois ",
        " depois ",
        " em seguida ",
        " entao ",
        " então ",
        " e ",
        ",",
    ]

    action_words = [
        "abra",
        "abrir",
        "abriu",
        "play",
        "pausa",
        "pausar",
        "pause",
        "continua",
        "continuar",
        "toca",
        "tocar",
        "liga",
        "ligar",
        "ligue",
        "ativa",
        "ativar",
        "ative",
        "desliga",
        "desligar",
        "desligue",
        "desativa",
        "desativar",
        "desative",
        "pesquise",
        "crie",
        "escreva",
        "leia",
        "rode",
        "execute",
        "troca",
        "troque",
        "vai",
        "foca",
        "focar",
        "minimiza",
        "minimize",
        "maximiza",
        "maximize",
        "restaura",
        "restaure",
        "feche",
        "fechar",
        "fecha",
        "listar",
        "liste",
        "mostrar",
        "mostre",
    ]

    has_action_word = any(word in text for word in action_words)
    has_separator = any(trigger in text for trigger in triggers)

    return has_action_word and has_separator
