import difflib
import re
import subprocess
import unicodedata

from config import GEMINI_API_KEY
from llm.gemini_client import ask_gemini_grounded_model
from llm.ollama_client import ask_model
from llm.vision_client import choose_vision_model, installed_vision_models, vision_status_text
from memory.current_topic import load_current_topic, update_current_topic_from_conversation
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
    answer = re.sub(r"[*_`#>\[\]]+", "", answer).strip()
    answer = re.sub(
        r"^(aqui esta|aqui está)\s+(a\s+)?resposta\s+(para\s+a\s+pergunta\s+do\s+pedro\s*)?:\s*",
        "",
        answer,
        flags=re.I,
    ).strip()
    answer = re.sub(r"^(eu|axel|assistente|resposta)\s*:\s*", "", answer, flags=re.I).strip()
    if "Resumo salvo:" in answer or "Pergunta do Pedro:" in answer or "Trechos úteis salvos:" in answer:
        return ""
    return answer


def _looks_incomplete_answer(answer: str) -> bool:
    normalized = " ".join(str(answer or "").split()).strip()
    if not normalized:
        return True

    if len(normalized) < 24:
        return True

    lowered = normalized.lower().rstrip()
    dangling_endings = (
        "pelo que",
        "olha, pelo que",
        "acho que",
        "me parece que",
        "isso mostra que",
        "isso sugere que",
    )
    if lowered.endswith(dangling_endings):
        return True

    if not re.search(r"[.!?]$|:$", normalized):
        words = normalized.split()
        if len(words) <= 7:
            return True

    return False


def _looks_like_contextual_reading_question(question: str) -> bool:
    normalized = _normalize(question)
    starters = (
        "o que voce acha",
        "o que acha",
        "o que voce pensa",
        "o que pensa",
        "voce acha",
        "vc acha",
        "acha que",
        "existem",
        "existe",
        "tem",
        "qual sua opiniao",
        "qual a sua opiniao",
        "qual sua leitura",
        "como voce ve",
        "como voce interpreta",
        "me explica",
        "me explique",
        "explica",
        "explique",
        "detalha",
        "detalhar",
        "interpreta",
        "interprete",
        "me fala mais",
        "fala mais",
        "me contextualiza",
        "contextualiza",
        "me da contexto",
        "me de contexto",
        "sobre esse tema",
        "sobre esse assunto",
        "mais sobre isso",
        "o que isso significa",
        "o que isso quer dizer",
        "isso e bom",
        "isso e ruim",
        "faz sentido",
        "vale a pena",
        "isso preocupa",
        "isso e relevante",
    )
    return any(normalized.startswith(starter) for starter in starters)


def _looks_like_broader_context_question(question: str) -> bool:
    normalized = _normalize(question)
    broader_terms = (
        "voce acha",
        "vc acha",
        "acha que",
        "existem melhores",
        "existe melhor",
        "tem melhores",
        "tem melhor",
        "qual voce escolheria",
        "qual voce prefere",
        "vale mais a pena",
        "recomenda",
        "recomendaria",
        "me fala mais",
        "fala mais",
        "sobre esse tema",
        "sobre esse assunto",
        "mais sobre isso",
        "me contextualiza",
        "contextualiza",
        "me da contexto",
        "me de contexto",
        "me explica melhor",
    )
    return any(term in normalized for term in broader_terms)


def _looks_like_live_research_question(question: str, page_title: str, summary: str) -> bool:
    normalized = _normalize(" ".join([question, page_title, summary]))
    live_terms = {
        "noticia",
        "noticias",
        "jornal",
        "congresso",
        "senado",
        "camara",
        "camara",
        "governo",
        "lula",
        "bolsonaro",
        "politica",
        "politico",
        "mercado",
        "investimento",
        "investimentos",
        "acao",
        "acoes",
        "economia",
        "stf",
        "eleicao",
        "eleicoes",
        "youtube",
        "reddit",
        "wikipedia",
        "comparacao",
        "comparar",
        "melhores",
        "recomenda",
        "recomendaria",
    }
    return any(term in normalized for term in live_terms)


def _fallback_contextual_reading(summary: str, page_title: str, useful_lines: list[str]) -> str:
    focus = page_title or summary.split(".")[0].strip()
    if not focus:
        focus = "esse conteudo"

    highlight = ""
    for line in useful_lines:
        clean = " ".join(str(line or "").split()).strip(" .")
        if len(clean) >= 24:
            highlight = clean
            break

    if highlight:
        return (
            f"A primeira vista, o centro disso parece ser {focus}. Minha leitura inicial e que o ponto mais relevante gira em torno de {highlight}. "
            "Posso ir alem, se voce quiser, mas por enquanto estou me guiando pelo que ficou visivel na tela."
        )

    return (
        f"A primeira vista, o foco parece ser {focus}. Eu consigo te dar uma leitura inicial com o que ficou salvo, "
        "mas ainda nao chamaria isso de conclusao forte sem reler ou pesquisar um pouco mais."
    )


def _ask_grounded_contextual_reading(question: str, item: dict, summary: str, page_title: str, useful_lines: list[str]) -> str | None:
    if not GEMINI_API_KEY:
        return None

    prompt = (
        "Voce e o Axel respondendo uma pergunta sobre o tema da ultima tela lida, mas pode consultar outras fontes da web em tempo real.\n"
        "Responda em portugues do Brasil, de forma curta, natural e util.\n"
        "Soe como um assistente operacional elegante: calmo, preciso e levemente espirituoso, sem exagero.\n"
        "Use a tela salva como ponto de partida para identificar o tema e, se ajudar, complemente com pesquisa Google via grounding.\n"
        "O foco principal deve ser explicar o tema, dar contexto, opiniao ou comparacao util sobre o assunto em si.\n"
        "Nao desperdice a resposta falando sobre metodologia, fontes ou sobre o fato de ter lido uma tela, a menos que isso seja realmente necessario para nao induzir erro.\n"
        "Nao cite fontes, links ou nomes de veiculos se o usuario nao pedir isso explicitamente.\n"
        "Nao use markdown, listas, negrito, titulos nem rotulos como 'Eu:' ou 'Resposta:'.\n"
        "Prefira 2 ou 3 frases.\n\n"
        f"Fonte salva: {item.get('source', 'analise')}\n"
        f"Titulo da pagina: {page_title or 'nao informado'}\n"
        f"Resumo salvo:\n{summary}\n\n"
        "Trechos uteis salvos:\n"
        + ("\n".join(f"- {line}" for line in useful_lines[:10]) if useful_lines else "- nenhum trecho extra salvo")
        + "\n\n"
        f"Pergunta do Pedro:\n{question}\n\n"
        "Resposta:"
    )
    try:
        grounded = ask_gemini_grounded_model(
            prompt,
            timeout_seconds=30,
            max_output_tokens=260,
            temperature=0.2,
        )
        answer = _clean_answer(grounded.get("text", ""))
        if not answer or _looks_incomplete_answer(answer):
            return None
        return answer
    except Exception:
        return None


def _answer_contextual_reading_question(question: str, item: dict, summary: str, page_title: str, useful_lines: list[str]) -> str | None:
    if not _looks_like_contextual_reading_question(question):
        return None

    normalized_question = _normalize(question)
    can_go_broader = _looks_like_broader_context_question(question) or any(
        marker in normalized_question
        for marker in {
            "o que voce acha",
            "o que acha",
            "o que voce pensa",
            "o que pensa",
            "qual sua opiniao",
            "qual a sua opiniao",
        }
    )

    if can_go_broader:
        if _looks_like_live_research_question(question, page_title, summary):
            grounded_answer = _ask_grounded_contextual_reading(question, item, summary, page_title, useful_lines)
            if grounded_answer:
                return grounded_answer

        prompt = (
            "Voce e o Axel respondendo uma pergunta sobre o tema da ultima tela lida, com liberdade para dar uma leitura mais ampla.\n"
            "Responda em portugues do Brasil, de forma curta, natural e util.\n"
            "Soe como um assistente operacional elegante: calmo, preciso e levemente espirituoso, sem exagero.\n"
            "Use o resumo salvo e os trechos visiveis para identificar o tema principal.\n"
            "Voce pode complementar com conhecimento geral do modelo quando a pergunta pedir comparacao, recomendacao, contexto ou leitura mais ampla.\n"
            "Fale principalmente do assunto em si, nao da tela.\n"
            "Nao finja que viu na tela o que nao estava nela.\n"
            "Se completar com leitura mais ampla, faça isso de modo natural, sem soar burocratico.\n"
            "Nao use markdown, negrito, titulos, listas, aspas decorativas nem rotulos como 'Eu:' ou 'Resposta:'.\n"
            "Responda em 2 ou 3 frases.\n\n"
            f"Fonte salva: {item.get('source', 'analise')}\n"
            f"Titulo da pagina: {page_title or 'nao informado'}\n"
            f"Resumo salvo:\n{summary}\n\n"
            "Trechos uteis salvos:\n"
            + ("\n".join(f"- {line}" for line in useful_lines[:12]) if useful_lines else "- nenhum trecho extra salvo")
            + "\n\n"
            f"Pergunta do Pedro:\n{question}\n\n"
            "Resposta:"
        )
    else:
        prompt = (
            "Voce e o Axel respondendo uma pergunta de leitura e opiniao sobre o tema da ultima pagina ou tela lida.\n"
            "Responda em portugues do Brasil, de forma curta, natural e util.\n"
            "Soe como um assistente operacional elegante: calmo, preciso e levemente espirituoso, sem exagero.\n"
            "Baseie-se somente no resumo salvo e nos trechos visiveis abaixo.\n"
            "Foque em explicar ou interpretar o tema, nao em descrever que houve uma tela.\n"
            "Nao invente fatos, nomes, dados, contexto externo nem noticias adicionais.\n"
            "Se faltar contexto, deixe isso claro de forma natural.\n"
            "Nao use markdown, negrito, titulos, listas, aspas decorativas nem rotulos como 'Eu:' ou 'Resposta:'.\n"
            "Tente responder em 2 ou 3 frases, separando implicitamente: o que parece ter acontecido, sua leitura e o limite dessa leitura.\n\n"
            f"Fonte salva: {item.get('source', 'analise')}\n"
            f"Titulo da pagina: {page_title or 'nao informado'}\n"
            f"Resumo salvo:\n{summary}\n\n"
            "Trechos uteis salvos:\n"
            + ("\n".join(f"- {line}" for line in useful_lines[:12]) if useful_lines else "- nenhum trecho extra salvo")
            + "\n\n"
            f"Pergunta do Pedro:\n{question}\n\n"
            "Resposta:"
        )
    try:
        answer = ask_model(prompt, timeout_seconds=20, num_predict=140, temperature=0.25)
        answer = _clean_answer(answer)
        if not answer or _looks_incomplete_answer(answer):
            return _fallback_contextual_reading(summary, page_title, useful_lines)
        return answer
    except Exception:
        return _fallback_contextual_reading(summary, page_title, useful_lines)


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

    contextual_reading = _answer_contextual_reading_question(question, item, summary, page_title, useful_lines)
    if contextual_reading:
        return contextual_reading

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
