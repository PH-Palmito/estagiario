import difflib
import re
import subprocess
import unicodedata

from config import GEMINI_API_KEY
from llm.gemini_client import ask_gemini_grounded_model
from llm.ollama_client import ask_model
from llm.vision_client import choose_vision_model, installed_vision_models, vision_status_text
from memory.current_topic import load_current_topic, update_current_topic_from_conversation
from memory.obsidian_sync import search_vault_context
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


def _clean_topic_sentence(text: str) -> str:
    clean = " ".join(str(text or "").split()).strip()
    if not clean:
        return ""
    clean = re.sub(
        r"^(?:resumo da tela|panorama da tela|visao rapida da tela|detalhando a tela)\s*:\s*",
        "",
        clean,
        flags=re.I,
    ).strip()
    clean = re.sub(r"^(?:na tela esta|na tela está|na tela parece haver)\s+", "", clean, flags=re.I).strip()
    return clean


def _distill_topic_summary(summary: str, page_title: str = "", useful_lines: list[str] | None = None) -> str:
    summary_clean = _clean_topic_sentence(summary)
    title_clean = _clean_topic_sentence(page_title)
    highlights = _select_relevant_lines(useful_lines or [], limit=2)
    if _looks_like_finance_context(page_title, summary, useful_lines or []):
        ticker = _extract_primary_ticker(page_title, summary, useful_lines or [])
        direction = _extract_directional_hint(" ".join([summary_clean, *highlights]))
        base = f"{ticker or title_clean or 'Esse ativo'} aparece ligado a cotacao, rentabilidade e dividendos."
        if direction:
            base += f" No trecho visivel, ele esta {direction}."
        if highlights:
            base += f" Ponto mais util agora: {highlights[0]}."
        return base
    if title_clean and highlights:
        return f"{title_clean}. O ponto mais util aqui e {highlights[0]}."
    if highlights:
        return highlights[0]
    return summary_clean


def _select_relevant_lines(lines: list[str], limit: int = 4) -> list[str]:
    selected = []
    seen = set()
    noise_terms = {
        "ir para o",
        "ir para",
        "acesse",
        "uma so conta",
        "uma só conta",
        "e gratis",
        "é gratis",
        "e grátis",
        "comentarios",
        "comentários",
        "inscreva se",
        "inscreva-se",
        "arrow_upward",
    }
    for raw_line in list(lines or []):
        clean = _clean_topic_sentence(raw_line).strip(" .;:-")
        normalized = _normalize(clean)
        if not clean or normalized in seen:
            continue
        if len(clean) < 8:
            continue
        if re.match(r"^https?://", clean, flags=re.I):
            continue
        if any(term in normalized for term in noise_terms):
            continue
        selected.append(clean)
        seen.add(normalized)
        if len(selected) >= limit:
            break
    return selected


def _looks_like_finance_context(page_title: str, summary: str, useful_lines: list[str]) -> bool:
    blob = _normalize(" ".join([page_title or "", summary or "", *list(useful_lines or [])]))
    finance_terms = {
        "cotacao",
        "indicadores",
        "rentabilidade",
        "dividendos",
        "proventos",
        "petr4",
        "vale3",
        "itub4",
        "bbas3",
        "fii",
        "acoes",
        "acao",
        "mercado",
        "carteira",
        "investidor10",
        "preco teto",
        "dy",
        "roe",
        "p vp",
        "p/l",
        "patrimonio",
    }
    return any(term in blob for term in finance_terms)


def _extract_primary_ticker(page_title: str, summary: str, useful_lines: list[str]) -> str:
    text = " ".join([page_title or "", summary or "", *list(useful_lines or [])])
    match = re.search(r"\b[A-Z]{4}\d{1,2}\b", text)
    return match.group(0).upper() if match else ""


def _extract_directional_hint(text: str) -> str:
    compact = " ".join(str(text or "").split())
    lowered = compact.lower()
    if "arrow_upward" in lowered and ("0,00%" in compact or "0.00%" in compact):
        return "sem movimento relevante na variacao visivel"
    positive = re.search(r"(?:\+|\b)(\d+(?:,\d+)?)\s*%", compact)
    negative = re.search(r"-(\d+(?:,\d+)?)\s*%", compact)
    if negative:
        return f"em queda visivel de {negative.group(1)}%"
    if "arrow_downward" in lowered:
        return "em queda na variacao visivel"
    if positive and positive.group(1) not in {"0,00", "0.00", "0"}:
        return f"em alta visivel de {positive.group(1)}%"
    if "arrow_upward" in lowered:
        return "em alta na variacao visivel"
    return ""


def _finance_profile_hint(topic_name: str, summary: str, useful_lines: list[str]) -> str:
    blob = _normalize(" ".join([topic_name or "", summary or "", *list(useful_lines or [])]))
    if any(token in blob for token in {"petr4", "petrobras", "petroleo", "petroleo", "combustiveis", "combustíveis"}):
        return (
            "O perfil aqui costuma ser mais de geracao de caixa e dividendos, com risco forte de commodity, cambio e interferencia politica."
        )
    if any(token in blob for token in {"fii", "fundo imobiliario", "fundo imobiliário"}):
        return "O foco tende a ser renda e previsibilidade de fluxo, mas sensivel a juros, vacancia e qualidade dos contratos."
    if any(token in blob for token in {"banco", "itub4", "bbas3", "sanb11", "bradesco"}):
        return "Aqui eu olharia mais para qualidade do lucro, inadimplencia, eficiencia e sensibilidade ao ciclo de juros."
    return "Eu trataria isso olhando tese, risco, qualidade do lucro ou do caixa e se o momento atual combina com seu perfil."


def _build_finance_fallback_reading(question: str, page_title: str, summary: str, useful_lines: list[str]) -> str:
    topic_name = _clean_topic_sentence(page_title) or "esse ativo"
    highlights = _select_relevant_lines(useful_lines, limit=3)
    combined_text = " ".join([summary or "", *highlights])
    ticker = _extract_primary_ticker(page_title, summary, useful_lines)
    direction = _extract_directional_hint(combined_text)
    profile = _finance_profile_hint(topic_name, summary, useful_lines)

    opening = f"Pelo que aparece, {ticker or topic_name} parece estar sendo analisado por cotacao, rentabilidade e dividendos."
    if direction:
        opening += f" No recorte visivel, ele esta {direction}."
    else:
        opening += " Mas esse recorte sozinho ainda nao mostra uma tendencia clara de alta ou queda."

    visible_point = ""
    if highlights:
        chosen_highlight = highlights[0]
        for candidate in highlights:
            candidate_norm = _normalize(candidate)
            if any(term in candidate_norm for term in {"dividend", "rentabilidade", "%", "lucro", "prejuizo", "prejuizo", "provento"}):
                chosen_highlight = candidate
                break
        visible_point = f" O que mais chama atencao agora e: {chosen_highlight}."

    closing = (
        f" Minha leitura inicial e esta: {profile} "
        "Entao eu nao chamaria de bom ou ruim por esse print isolado; eu chamaria de ponto de partida para decidir se vale aprofundar fundamentos, preco e momento."
    )

    normalized_question = _normalize(question)
    if any(term in normalized_question for term in {"vale a pena", "e bom", "é bom", "comprar", "vender", "o que voce acha", "o que acha"}):
        return opening + visible_point + " " + closing

    return opening + visible_point + " " + profile


def _fallback_contextual_reading(summary: str, page_title: str, useful_lines: list[str]) -> str:
    if _looks_like_finance_context(page_title, summary, useful_lines):
        return _build_finance_fallback_reading("", page_title, summary, useful_lines)

    focus = _clean_topic_sentence(page_title or summary.split(".")[0].strip())
    if not focus:
        focus = "esse conteudo"

    highlights = _select_relevant_lines(useful_lines, limit=2)

    if highlights:
        return (
            f"O tema aqui parece ser {focus}. O que ficou mais relevante nesse trecho e {highlights[0]}. "
            + (f"Tambem apareceu {highlights[1]}. " if len(highlights) > 1 else "")
            + "Minha leitura inicial e que isso merece ser entendido pelo assunto em si, nao so pelo titulo da pagina."
        )

    return (
        f"O foco aqui parece ser {focus}. Eu consigo te dar uma leitura inicial com o que ficou salvo, "
        "mas ainda falta densidade para transformar isso numa analise mais forte."
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


def _ask_grounded_finance_reading(question: str, item: dict, summary: str, page_title: str, useful_lines: list[str]) -> str | None:
    if not GEMINI_API_KEY:
        return None

    prompt = (
        "Voce e o Axel analisando uma tela financeira, mas pode complementar com pesquisa web em tempo real.\n"
        "Responda em portugues do Brasil, de forma util, clara e um pouco mais densa do que o normal.\n"
        "Soe como um assistente elegante com leitura de analista cuidadoso.\n"
        "Explique o que a tela sugere sobre o ativo, se ha sinal de alta, queda ou lateralizacao no recorte visivel, qual parece ser o perfil do ativo e o que ainda falta para uma opiniao forte.\n"
        "Nao trate compra ou venda como certeza. Nao cite fontes nem links se Pedro nao pedir isso.\n"
        "Separe naturalmente fato visivel, leitura e cautela, sem usar lista.\n"
        "Pode responder em 3 a 5 frases.\n\n"
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
        grounded = ask_gemini_grounded_model(
            prompt,
            timeout_seconds=35,
            max_output_tokens=360,
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
    finance_context = _looks_like_finance_context(page_title, summary, useful_lines)
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

    if finance_context:
        if can_go_broader or _looks_like_live_research_question(question, page_title, summary):
            grounded_answer = _ask_grounded_finance_reading(question, item, summary, page_title, useful_lines)
            if grounded_answer:
                return grounded_answer

        finance_prompt = (
            "Voce e o Axel analisando uma pagina financeira lida na tela.\n"
            "Responda em portugues do Brasil, de forma util, clara e mais analitica do que um resumo simples.\n"
            "Interprete o que o recorte visivel sugere sobre o ativo ou pagina: se parece alta, queda ou estabilidade; que tipo de tese aparece; e qual a principal cautela antes de formar opiniao forte.\n"
            "Use apenas o que esta salvo abaixo e conhecimento geral nao-datado do modelo. Nao invente numeros novos nem fatos especificos recentes.\n"
            "Evite repetir o titulo literalmente. Prefira transformar sinais visiveis em leitura pratica.\n"
            "Nao use markdown nem listas. Pode responder em 3 ou 4 frases.\n\n"
            f"Titulo da pagina: {page_title or 'nao informado'}\n"
            f"Resumo salvo:\n{summary}\n\n"
            "Trechos uteis salvos:\n"
            + ("\n".join(f"- {line}" for line in useful_lines[:12]) if useful_lines else "- nenhum trecho extra salvo")
            + f"\n\nPergunta do Pedro:\n{question}\n\nResposta:"
        )
        try:
            answer = ask_model(finance_prompt, timeout_seconds=22, num_predict=220, temperature=0.2)
            answer = _clean_answer(answer)
            if not answer or _looks_incomplete_answer(answer):
                return _build_finance_fallback_reading(question, page_title, summary, useful_lines)
            return answer
        except Exception:
            return _build_finance_fallback_reading(question, page_title, summary, useful_lines)

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
            "Responda em 2 a 4 frases.\n\n"
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
            "Tente responder em 2 a 4 frases, separando implicitamente: o que parece ter acontecido, sua leitura e o limite dessa leitura.\n\n"
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

def answer_visual_question_with_memory(question: str) -> str:
    current_topic = load_current_topic() or {}
    visual_answer = answer_last_visual_question(question)
    if "Ainda nÃ£o tenho uma pÃ¡gina ou imagem analisada" not in visual_answer:
        topic_name = str(current_topic.get("topic", "")).strip() or str(current_topic.get("page_title", "")).strip() or "Assunto visual"
        summary = str(current_topic.get("summary", "")).strip()
        update_current_topic_from_conversation(
            user_input=question,
            assistant_response=visual_answer,
            topic=topic_name,
            source="screen_followup",
            related_title=str(current_topic.get("page_title", "")).strip(),
            related_summary=summary,
        )
        return visual_answer

    if not current_topic:
        return visual_answer

    topic_name = str(current_topic.get("topic", "")).strip() or "assunto recente"
    summary = str(current_topic.get("summary", "")).strip()
    last_question = str(current_topic.get("last_user_question", "")).strip()
    last_answer = str(current_topic.get("last_assistant_answer", "")).strip()
    lines = [str(item).strip() for item in (current_topic.get("lines") or []) if str(item).strip()]
    vault_matches = search_vault_context(" ".join(filter(None, [question, topic_name, summary])), limit=2, max_chars=260)
    vault_context = " ".join(f"{item['name']}: {item['excerpt']}" for item in vault_matches) if vault_matches else ""
    normalized_question = _normalize(question)

    if any(term in normalized_question for term in {"qual voce escolheria", "qual voce prefere", "vale a pena", "existem melhores", "tem melhores", "existe melhor"}):
        if summary:
            answer = (
                f"Seguindo o assunto {topic_name}, eu escolheria pelo equilibrio entre qualidade em portugues, naturalidade e latencia. "
                f"O ponto central aqui continua sendo: {summary}"
            )
        else:
            answer = f"Seguindo o assunto {topic_name}, eu escolheria pela opcao mais consistente entre qualidade, velocidade e controle."
        update_current_topic_from_conversation(
            user_input=question,
            assistant_response=answer,
            topic=topic_name,
            source="conversation_memory",
            related_title=str(current_topic.get("page_title", "")).strip(),
            related_summary=summary,
        )
        return answer

    prompt = (
        "Voce e o Axel respondendo uma pergunta de follow-up usando a memoria recente do assunto.\n"
        "Responda em portugues do Brasil, curto, natural e util.\n"
        "Soe como um assistente operacional elegante e conversavel.\n"
        "Use o assunto atual como ancora principal. Se a pergunta parecer continuacao de uma conversa, trate assim.\n"
        "Nao invente fatos especificos que nao estejam no resumo salvo, mas voce pode complementar com conhecimento geral quando a pergunta pedir opiniao, comparacao ou explicacao.\n"
        "Nao fale sobre metodologia nem sobre memoria interna. Fale diretamente do tema.\n"
        "Nao use markdown.\n\n"
        f"Assunto atual: {topic_name}\n"
        f"Resumo salvo: {summary or 'nao informado'}\n"
        f"Contexto semantico do vault: {vault_context or 'nenhum trecho relevante encontrado'}\n"
        f"Ultima pergunta relacionada: {last_question or 'nao informada'}\n"
        f"Ultima resposta relacionada: {last_answer or 'nao informada'}\n"
        "Pontos auxiliares:\n"
        + ("\n".join(f"- {line}" for line in lines[:8]) if lines else "- nenhum ponto extra salvo")
        + f"\n\nPergunta atual do Pedro:\n{question}\n\nResposta:"
    )
    try:
        answer = ask_model(prompt, timeout_seconds=20, num_predict=140, temperature=0.25)
        answer = _clean_answer(answer)
    except Exception:
        answer = ""

    lower_answer = answer.lower()
    looks_generic = any(
        marker in lower_answer
        for marker in (
            "sou um modelo",
            "text to speech",
            "aqui estao",
            "aqui estão",
            "caracteristicas",
            "características",
            "1.",
            "2.",
            "3.",
        )
    )

    if not answer or _looks_incomplete_answer(answer) or looks_generic:
        if summary:
            answer = (
                f"Seguindo o assunto {topic_name}, eu tenderia a escolher pela combinacao entre qualidade em portugues, naturalidade e latencia. "
                f"O pano de fundo continua sendo este: {summary}"
            )
        else:
            answer = f"Seguimos no assunto {topic_name}. Se quiser, eu posso aprofundar por comparacao, contexto ou opiniao pratica."

    update_current_topic_from_conversation(
        user_input=question,
        assistant_response=answer,
        topic=topic_name,
        source="conversation_memory",
        related_title=str(current_topic.get("page_title", "")).strip(),
        related_summary=summary,
    )
    return answer

def answer_visual_question_with_context_memory(question: str) -> str:
    current_topic = load_current_topic() or {}
    normalized_question = _normalize(question)
    current_source = str(current_topic.get("source", "")).strip().lower()
    if current_topic and current_source in {"conversation", "conversation_memory"} and any(
        term in normalized_question
        for term in {"qual voce escolheria", "qual voce prefere", "vale a pena", "existem melhores", "tem melhores", "existe melhor"}
    ):
        topic_name = str(current_topic.get("topic", "")).strip() or "assunto recente"
        summary = str(current_topic.get("summary", "")).strip()
        answer = (
            f"Seguindo o assunto {topic_name}, eu escolheria pelo equilibrio entre qualidade em portugues, naturalidade e latencia. "
            f"O ponto central aqui continua sendo: {summary or 'comparar consistencia, custo e controle local.'}"
        )
        update_current_topic_from_conversation(
            user_input=question,
            assistant_response=answer,
            topic=topic_name,
            source="conversation_memory",
            related_title=str(current_topic.get("page_title", "")).strip(),
            related_summary=summary,
        )
        return answer

    if current_topic and current_source in {"conversation", "conversation_memory"} and any(
        term in normalized_question
        for term in {"e por que", "e porque", "por que", "porque"}
    ):
        topic_name = str(current_topic.get("topic", "")).strip() or "assunto recente"
        summary = str(current_topic.get("summary", "")).strip()
        answer = (
            f"Porque, nesse assunto {topic_name}, o ganho principal costuma estar em controle, previsibilidade e alinhamento com o que voce prioriza. "
            f"O pano de fundo continua sendo este: {summary or 'seguir uma escolha mais coerente com seu contexto.'}"
        )
        update_current_topic_from_conversation(
            user_input=question,
            assistant_response=answer,
            topic=topic_name,
            source="conversation_memory",
            related_title=str(current_topic.get("page_title", "")).strip(),
            related_summary=summary,
        )
        return answer

    visual_answer = answer_last_visual_question(question)
    fallback_markers = (
        "Ainda n",
        "NÃ£o consigo confirmar",
        "Nao consigo confirmar",
        "NÃ£o encontrei",
        "Nao encontrei",
        "consigo confirmar",
        "reler a tela",
        "resumir a pÃ¡gina de novo",
    )
    if not any(marker in visual_answer for marker in fallback_markers):
        topic_name = str(current_topic.get("topic", "")).strip() or str(current_topic.get("page_title", "")).strip() or "Assunto visual"
        summary = str(current_topic.get("summary", "")).strip()
        update_current_topic_from_conversation(
            user_input=question,
            assistant_response=visual_answer,
            topic=topic_name,
            source="screen_followup",
            related_title=str(current_topic.get("page_title", "")).strip(),
            related_summary=summary,
        )
        return visual_answer

    if not current_topic:
        return visual_answer

    topic_name = str(current_topic.get("topic", "")).strip() or "assunto recente"
    summary = str(current_topic.get("summary", "")).strip()
    last_question = str(current_topic.get("last_user_question", "")).strip()
    last_answer = str(current_topic.get("last_assistant_answer", "")).strip()
    lines = [str(item).strip() for item in (current_topic.get("lines") or []) if str(item).strip()]
    vault_matches = search_vault_context(" ".join(filter(None, [question, topic_name, summary])), limit=2, max_chars=260)
    vault_context = " ".join(f"{item['name']}: {item['excerpt']}" for item in vault_matches) if vault_matches else ""
    preferred_vault_matches = [
        item for item in vault_matches
        if item.get("name") not in {"current_topic", "operational_context", "home"}
    ] or vault_matches

    if any(term in normalized_question for term in {"me fala mais", "me fale mais", "fala mais", "fale mais", "mais sobre isso", "mais sobre esse tema", "mais sobre esse assunto"}):
        extra = ""
        if preferred_vault_matches:
            extra = re.sub(r"\s+", " ", preferred_vault_matches[0]["excerpt"]).strip()
            extra = re.sub(r"^#\s*\w+\s*", "", extra).strip()
        distilled = _distill_topic_summary(summary, str(current_topic.get("page_title", "")).strip(), lines)
        if _looks_like_finance_context(str(current_topic.get("page_title", "")).strip(), summary, lines):
            answer = _build_finance_fallback_reading(question, str(current_topic.get("page_title", "")).strip(), summary, lines)
        else:
            answer = (
                f"Seguindo esse tema, o centro da questao e {distilled or topic_name}. "
                f"{extra[:220] if extra else 'Se quiser, eu posso abrir isso em contexto, comparacao ou impacto pratico.'}"
            ).strip()
        update_current_topic_from_conversation(
            user_input=question,
            assistant_response=answer,
            topic=topic_name,
            source="conversation_memory",
            related_title=str(current_topic.get("page_title", "")).strip(),
            related_summary=summary,
        )
        return answer

    prompt = (
        "Voce e o Axel respondendo uma pergunta de follow-up usando a memoria recente do assunto.\n"
        "Responda em portugues do Brasil, curto, natural e util.\n"
        "Soe como um assistente operacional elegante e conversavel.\n"
        "Use o assunto atual como ancora principal. Se a pergunta parecer continuacao de uma conversa, trate assim.\n"
        "Nao invente fatos especificos que nao estejam no resumo salvo, mas voce pode complementar com conhecimento geral quando a pergunta pedir opiniao, comparacao ou explicacao.\n"
        "Nao fale sobre metodologia nem sobre memoria interna. Fale diretamente do tema.\n"
        "Nao use markdown.\n\n"
        f"Assunto atual: {topic_name}\n"
        f"Resumo salvo: {summary or 'nao informado'}\n"
        f"Contexto semantico do vault: {vault_context or 'nenhum trecho relevante encontrado'}\n"
        f"Ultima pergunta relacionada: {last_question or 'nao informada'}\n"
        f"Ultima resposta relacionada: {last_answer or 'nao informada'}\n"
        "Pontos auxiliares:\n"
        + ("\n".join(f"- {line}" for line in lines[:8]) if lines else "- nenhum ponto extra salvo")
        + f"\n\nPergunta atual do Pedro:\n{question}\n\nResposta:"
    )
    try:
        answer = ask_model(prompt, timeout_seconds=20, num_predict=140, temperature=0.25)
        answer = _clean_answer(answer)
    except Exception:
        answer = ""

    if not answer or _looks_incomplete_answer(answer):
        if _looks_like_finance_context(str(current_topic.get("page_title", "")).strip(), summary, lines):
            answer = _build_finance_fallback_reading(question, str(current_topic.get("page_title", "")).strip(), summary, lines)
        elif summary:
            distilled = _distill_topic_summary(summary, str(current_topic.get("page_title", "")).strip(), lines)
            answer = (
                f"Seguindo o assunto {topic_name}, minha leitura continua nessa linha: {distilled or summary} "
                "Se quiser, eu posso aprofundar isso por comparacao, risco ou contexto."
            )
        else:
            answer = f"Seguimos no assunto {topic_name}. Se quiser, eu posso aprofundar por comparacao, contexto ou opiniao pratica."

    update_current_topic_from_conversation(
        user_input=question,
        assistant_response=answer,
        topic=topic_name,
        source="conversation_memory",
        related_title=str(current_topic.get("page_title", "")).strip(),
        related_summary=summary,
    )
    return answer
