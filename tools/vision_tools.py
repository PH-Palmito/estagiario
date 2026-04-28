import difflib
import re
import subprocess
import unicodedata

from llm.ollama_client import ask_model
from llm.vision_client import choose_vision_model, installed_vision_models, vision_status_text
from memory.vision_history import last_vision_analysis, last_vision_item


LIGHT_VISION_MODEL = "moondream"
LOW_COST_VISUAL_QA_MODE = True


def vision_status() -> str:
    return vision_status_text()


def vision_install_hint() -> str:
    vision_models = installed_vision_models()
    if vision_models:
        return f"Visão local já está pronta. Modelo ativo: {choose_vision_model()}."
    return (
        "Para ativar análise visual semântica, instale um modelo visual no Ollama. "
        "O mais leve para começar: ollama pull moondream. "
        "Depois teste: interpretar imagem da tela."
    )


def start_light_vision_model_download() -> str:
    if any(model.lower().startswith(LIGHT_VISION_MODEL) for model in installed_vision_models()):
        return f"O modelo visual {LIGHT_VISION_MODEL} já está instalado. Pode testar: interpretar imagem da tela."

    try:
        subprocess.Popen(
            ["ollama", "pull", LIGHT_VISION_MODEL],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError:
        return "Não encontrei o comando ollama no PATH. Abra o Ollama ou rode manualmente: ollama pull moondream."
    except Exception as exc:
        return f"Não consegui iniciar o download do modelo visual: {exc}"

    return (
        f"Iniciei o download do modelo visual {LIGHT_VISION_MODEL} em segundo plano. "
        "Quando terminar, diga: status da visão."
    )


def active_vision_model() -> str:
    return f"Modelo visual escolhido: {choose_vision_model()}."


def last_visual_analysis() -> str:
    return last_vision_analysis()


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", str(text or ""))
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _normalize(text: str) -> str:
    text = _strip_accents(text).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.1f}".replace(".", ",")


LABEL_DISPLAY = {
    "matematica": "Matemática",
    "portugues": "Português",
    "ciencias": "Ciências",
    "educacaofisica": "Educação física",
    "educacao fisica": "Educação física",
    "historia": "História",
    "geografia": "Geografia",
    "ingles": "Inglês",
}


def _display_label(label: str) -> str:
    clean = re.sub(r"\s+", " ", str(label or "")).strip(" .:-")
    normalized = _normalize(clean)
    compact = normalized.replace(" ", "")
    if compact in LABEL_DISPLAY:
        return LABEL_DISPLAY[compact]
    if normalized in LABEL_DISPLAY:
        return LABEL_DISPLAY[normalized]
    return clean[:1].upper() + clean[1:]


def _extract_chart_values(summary: str) -> list[dict]:
    values = []
    for match in re.finditer(r"([^:;\n]+):\s*aproximadamente\s*([0-9]+(?:[,.][0-9]+)?)", str(summary or ""), flags=re.I):
        raw_label = match.group(1).strip(" .:-")
        raw_label = re.sub(r"^.*\b(?:barras|valores|dados)\s*", "", raw_label, flags=re.I).strip(" .:-")
        if not raw_label:
            continue
        try:
            value = float(match.group(2).replace(",", "."))
        except ValueError:
            continue
        label = _display_label(raw_label)
        values.append(
            {
                "label": label,
                "key": _normalize(label),
                "compact_key": _normalize(label).replace(" ", ""),
                "value": value,
            }
        )
    return values


def _extract_chart_title(summary: str) -> str:
    match = re.search(r"T[íi]tulo:\s*(.+?)(?:\.\s*Valores|\.\s*Dados|$)", str(summary or ""), flags=re.I)
    if not match:
        return ""
    title = match.group(1).strip(" .")
    return title


def _find_chart_label(question: str, values: list[dict]) -> dict | None:
    normalized = _normalize(question)
    compact = normalized.replace(" ", "")
    for item in values:
        if item["key"] and item["key"] in normalized:
            return item
        if item["compact_key"] and item["compact_key"] in compact:
            return item
        if item["compact_key"] and difflib.SequenceMatcher(None, item["compact_key"], compact).ratio() >= 0.82:
            return item
    return None


def _answer_chart_question(question: str, summary: str) -> str | None:
    values = _extract_chart_values(summary)
    normalized = _normalize(question)
    drop_match = re.search(
        r"(?:queda|alta)\s+aproximada\s+de\s+([0-9]+(?:[,.][0-9]+)?)\s*%",
        str(summary or ""),
        flags=re.I,
    )
    if drop_match and any(term in normalized for term in {"porcentagem", "percentual", "queda", "caiu", "variacao", "variação"}):
        percent = drop_match.group(1).replace(".", ",")
        direction = "queda" if "queda" in drop_match.group(0).lower() else "alta"
        return f"Pela última análise do gráfico, a {direction} aproximada da primeira até a última barra é de {percent}%."

    if not values:
        return None

    title = _extract_chart_title(summary)
    title_prefix = f"No gráfico {title}, " if title else "Nesse gráfico, "

    if any(term in normalized for term in {"ganhou", "venceu", "vencedor", "maior", "mais alta", "mais votada", "preferida"}):
        winner = max(values, key=lambda item: item["value"])
        return f"{title_prefix}quem lidera é {winner['label']}, com aproximadamente {_format_number(winner['value'])}."

    if any(term in normalized for term in {"menor", "menos", "mais baixa", "ultimo", "pior"}):
        loser = min(values, key=lambda item: item["value"])
        return f"{title_prefix}o menor valor é {loser['label']}, com aproximadamente {_format_number(loser['value'])}."

    label = _find_chart_label(question, values)
    if label:
        return f"{title_prefix}{label['label']} aparece com aproximadamente {_format_number(label['value'])}."

    if any(term in normalized for term in {"listar", "lista", "valores", "dados", "materias", "categorias"}):
        pairs = "; ".join(f"{item['label']}: {_format_number(item['value'])}" for item in values)
        return f"{title_prefix}os valores estimados são: {pairs}."

    if "titulo" in normalized or "assunto" in normalized or "sobre o que" in normalized:
        if title:
            return f"O título do gráfico é: {title}."
        return "Não consegui recuperar o título do gráfico na última análise."

    return None


def _has_chart_question_terms(question: str) -> bool:
    normalized = _normalize(question)
    return any(
        term in normalized
        for term in {
            "ganhou",
            "venceu",
            "vencedor",
            "maior",
            "menor",
            "materia",
            "categoria",
            "grafico",
            "barra",
            "porcentagem",
            "percentual",
            "queda",
            "caiu",
            "variacao",
            "matematica",
            "portugues",
            "ciencias",
            "educacao fisica",
            "historia",
            "geografia",
            "ingles",
        }
    )


def _has_price_question_terms(question: str) -> bool:
    normalized = _normalize(question)
    return any(term in normalized for term in {"preco", "valor", "custa", "custo", "quanto custa"})


def _context_has_price(text: str) -> bool:
    normalized = _normalize(text)
    return bool(re.search(r"r\$\s*\d|\d+,\d{2}", text, flags=re.I)) or any(
        term in normalized for term in {"preco", "valor atual", "valor investido", "patrimonio"}
    )


def _clean_answer(answer: str) -> str:
    answer = " ".join(str(answer or "").split()).strip()
    answer = re.sub(
        r"^(aqui esta|aqui está)\s+(a\s+)?resposta\s+(para\s+a\s+pergunta\s+do\s+pedro\s*)?:\s*",
        "",
        answer,
        flags=re.I,
    ).strip()
    if "Resumo salvo:" in answer or "Pergunta do Pedro:" in answer or "Trechos úteis salvos:" in answer:
        return ""
    return answer


def answer_last_visual_question(question: str) -> str:
    item = last_vision_item()
    if not item:
        return "Ainda não tenho uma página ou imagem analisada para responder. Primeiro peça: o que tem na tela, resuma a tela ou analisar imagem da tela."

    summary = str(item.get("summary", "")).strip()
    if not summary:
        return "A última análise ficou vazia. Analise a página ou imagem de novo e me pergunte em seguida."

    deterministic = _answer_chart_question(question, summary)
    if deterministic:
        return deterministic

    details = item.get("details") if isinstance(item.get("details"), dict) else {}
    page_title = str(details.get("page_title", "")).strip()
    page_url = str(details.get("page_url", "")).strip()
    lines = details.get("lines") if isinstance(details.get("lines"), list) else []
    useful_lines = []
    for line in lines[:24]:
        clean = " ".join(str(line or "").split()).strip()
        if clean:
            useful_lines.append(clean)
    context_text = "\n".join([summary, page_title, page_url, *useful_lines])

    if _has_chart_question_terms(question) and not _extract_chart_values(summary):
        return "Não consigo confirmar isso pela última análise salva. Se for sobre um gráfico, peça para analisar a imagem ou a tela de novo."

    if _has_price_question_terms(question) and not _context_has_price(context_text):
        return "Não encontrei preço ou valor na última análise salva. Abra a página do item ou peça para eu ler a tela de novo."

    if LOW_COST_VISUAL_QA_MODE:
        return "Não consigo confirmar isso pela última análise salva. Se quiser, peça para eu reler a tela ou resumir a página de novo."

    prompt = (
        "Voce e o Axel respondendo uma pergunta sobre a ultima pagina, imagem ou tela analisada.\n"
        "Responda em portugues do Brasil, curto e util.\n"
        "Use somente o resumo e os trechos salvos abaixo. Se nao houver informacao suficiente, diga que nao da para confirmar pela analise salva.\n"
        "Nao invente valores, nomes, pessoas, conclusoes ou dados externos.\n\n"
        "Se um trecho disser 'feito com React', isso significa tecnologia usada, nao o nome do projeto.\n"
        "Se a pergunta pedir preco, valor, vencedor, pessoa, animal ou objeto e isso nao estiver nos trechos, diga que nao da para confirmar.\n\n"
        f"Fonte salva: {item.get('source', 'analise')}\n"
        f"Titulo da pagina: {page_title or 'nao informado'}\n"
        f"URL: {page_url or 'nao informada'}\n"
        f"Resumo salvo:\n{summary}\n\n"
        "Trechos uteis salvos:\n"
        + ("\n".join(f"- {line}" for line in useful_lines) if useful_lines else "- nenhum trecho extra salvo")
        + "\n\n"
        f"Pergunta do Pedro:\n{question}\n\n"
        "Resposta:"
    )
    try:
        answer = ask_model(prompt, timeout_seconds=25, num_predict=180, temperature=0.1)
        answer = _clean_answer(answer)
        return answer or "Não consegui responder com segurança usando a última análise visual."
    except Exception:
        return "Estou sem o raciocínio local agora, mas consigo responder perguntas objetivas se a última análise tiver o dado salvo."
