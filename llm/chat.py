import json
import re
import time
from collections import deque
from pathlib import Path

from config import GEMINI_API_KEY, GEMINI_COMPLEX_CHAT_ENABLED, GEMINI_MODEL, NVIDIA_API_KEY, NVIDIA_MODEL
from core.decision_orchestrator import build_decision_plan
from core.router_registry import INTENT_LEVEL_CONVERSATION, INTENT_LEVEL_QUESTION
from llm.model_selection import select_chat_model_route
from llm.ollama_client import ask_model
from memory.current_topic import load_current_topic, update_current_topic_from_conversation
from memory.curated_memory import format_curated_memory
from memory.docs_context import docs_context_relevant, search_docs_context
from memory.long_memory import format_relevant_long_memory
from memory.layered_recall import format_layered_memory_recall
from memory.obsidian_sync import load_vault_context, search_vault_context
from memory.operational_context import load_operational_context
from memory.profile import load_profile
from memory.research_sources import format_research_sources
from memory.session_index import format_relevant_session_memory, index_exchange
from memory.procedural_skills import format_relevant_skills
from memory.vault_bootstrap import bootstrap_obsidian_knowledge
from core.toolsets import format_relevant_toolsets
from core.specialist_agents import format_relevant_agents
from core.axel_brain import format_conversation_brief
from core.response_provenance import record_model_use
from memory.voice_preferences import load_voice_preferences
from memory.execution_log import append_execution_log

PREFERENCES = load_voice_preferences()
CHAT_HISTORY = deque(maxlen=6)
DIRECTIVES_PATH = Path(__file__).resolve().parents[1] / "memory" / "axel_directives.json"

BASE_CHAT_PROMPT = """
Voce e o Axel, uma IA local controlada por voz no PC do usuario.

Personalidade:
- Fale em portugues do Brasil.
- Seja curto, natural e util.
- Tenha um tom calmo, elegante e colaborativo.
- Responda como bate-papo, nao como atendente de suporte.
- Seu estilo e o Axel: copiloto operacional local, parceiro tecnico do Pedro, calmo, direto e observador.
- Quando for executar ou confirmar algo, seja preciso, sereno e discreto.
- Quando estiver conversando, traga uma observacao humana ou curiosa, sem exagerar.
- Pode usar humor seco e contido de vez em quando, como alguem muito competente que prefere nao fazer alarde disso.
- Nunca imite personagens protegidos nem copie falas famosas. Use apenas uma inspiracao geral: formalidade calma, inteligencia contida, cuidado e maravilhamento.
- Evite drama. Prefira frases limpas, com uma ponta de ironia fina ou reflexao.
- Evite frases genericas como "Como posso ajudar hoje?".
- Nao diga "Entendo!", "Ok, estou pronto" ou "Ola, sou um assistente".
- Nao seja submisso nem cerimonial. Seja parceiro de execucao.
- Se o usuario fizer uma pergunta aberta, de uma opiniao simples ou puxe um detalhe do assunto.
- Nao finja que executou acoes. Se for comando de PC, diga que o usuario pode pedir como comando.
- Nao use markdown.
- Nao responda com listas longas.
- Evite respostas maiores que 2 frases.
- Responda somente a sua fala final, sem escrever "Usuario:" ou "Axel:".
- Nao continue a conversa inventando falas do usuario.
- Voce nunca deve dizer que se chama Qwen, Llama ou qualquer nome de modelo.
- Se perguntarem quem voce e, diga que e o Axel.

Contexto:
Voce consegue abrir apps e sites, controlar janelas, navegar no navegador, controlar midia,
lembrar apps/sites e responder por voz. Esta conversa acontece por fala, entao seja objetivo.

Exemplos de atitude, nao de fala copiada:
- Em comandos: "Na mao. Ajustando isso agora."
- Em duvida: "Minha leitura ainda esta incompleta; melhor separar fato de chute."
- Em erro: "Isso falhou. Vou tentar por um caminho mais direto."
""".strip()
CHAT_PROMPT = BASE_CHAT_PROMPT

HUMOR_STYLES = {
    "neutro": "Humor desligado. Responda de forma simples, calma e direta.",
    "jarvis": "Use humor de assistente sofisticado: calmo, extremamente competente, ligeiramente espirituoso e com ironia seca de alto controle. Nunca seja espalhafatoso.",
    "seco": "Use humor seco e discreto. Se couber, faca uma observacao curta, elegante e levemente acida.",
    "filosofico": "Use um tom reflexivo. Traga uma observacao curta sobre sentido, contraste ou curiosidade do mundo, sem monologar.",
    "brincalhao": "Use humor leve e caloroso. Soe mais simpatico e solto, mas sem virar palhaco ou exagerar.",
}

OPINION_HINTS = {
    "acha",
    "opina",
    "opiniao",
    "opinião",
    "vale a pena",
    "faz sentido",
    "bom momento",
    "melhor",
    "pior",
    "arriscado",
    "seguro",
    "provavel",
    "provável",
    "cenario",
    "cenário",
    "devo",
}

LIVE_CONTEXT_HINTS = {
    "eleicao",
    "eleição",
    "mercado",
    "investimento",
    "investimentos",
    "acao",
    "ação",
    "acoes",
    "ações",
    "noticia",
    "notícia",
    "economia",
    "governo",
    "presidente",
}

COMPLEX_REASONING_HINTS = {
    "por que",
    "porque",
    "analisa",
    "analise",
    "analisar",
    "compare",
    "comparar",
    "cenario",
    "cenário",
    "estrategia",
    "estratégia",
    "tese",
    "impacto",
    "consequencia",
    "consequência",
    "vantagem",
    "desvantagem",
    "riscos",
    "risco",
    "fundamento",
    "explica melhor",
    "me explica",
}

OPEN_ADVICE_HINTS = {
    "ideia",
    "ideias",
    "sugestao",
    "sugestão",
    "dica",
    "dicas",
    "recomenda",
    "recomendacao",
    "recomendação",
    "presente",
    "namorada",
    "namorado",
    "parente",
    "parentes",
    "treino",
    "treinar",
    "exercicio",
    "exercício",
    "academia",
    "calistenia",
    "dieta",
    "alimentacao",
    "alimentação",
    "comer melhor",
    "ganhar massa",
    "emagrecer",
    "rotina",
    "plano",
}

LEARNING_HINTS = {
    "aprender",
    "aprendo",
    "estudar",
    "estudo",
    "treinar",
    "praticar",
    "ingles",
    "inglês",
    "idioma",
    "materia",
    "matéria",
    "aula",
    "prova",
    "resumo",
    "exercicios",
    "exercícios",
    "questoes",
    "questões",
}

LEARNING_REQUEST_TRIGGERS = {
    "me ajuda",
    "me ajude",
    "pode me ajudar",
    "consegue me ajudar",
    "quero",
    "preciso",
    "como",
    "qual",
    "monta",
    "monte",
    "cria",
    "crie",
    "me ensina",
    "ensina",
    "explique",
    "explica",
}


def refresh_preferences():
    PREFERENCES.clear()
    PREFERENCES.update(load_voice_preferences())


def _humor_level() -> int:
    try:
        return int(PREFERENCES.get("assistant_humor_level", 2))
    except (TypeError, ValueError):
        return 2


def _chat_temperature() -> float:
    level = max(0, min(3, _humor_level()))
    return 0.45 + (level * 0.1)


def _humor_prompt() -> str:
    if not bool(PREFERENCES.get("assistant_humor_enabled", True)):
        return HUMOR_STYLES["neutro"]

    style = str(PREFERENCES.get("assistant_humor_style", "seco")).strip().lower()
    style_text = HUMOR_STYLES.get(style, HUMOR_STYLES["seco"])
    level = max(0, min(3, _humor_level()))

    return "\n".join(
        [
            "Sistema de humor:",
            f"- Estilo atual: {style}.",
            f"- Intensidade: {level}/3.",
            f"- Instrucao: {style_text}",
            "- O humor nunca deve atrapalhar comandos, seguranca, erros ou informacoes importantes.",
            "- Se a fala do usuario for seria, responda com respeito e reduza o humor.",
        ]
    )


def build_chat_prompt() -> str:
    return f"{BASE_CHAT_PROMPT}\n\n{_humor_prompt()}"


def chat_enabled() -> bool:
    return bool(PREFERENCES.get("chat_enabled", True))


def _history_text() -> str:
    if not CHAT_HISTORY:
        return "Sem historico recente."

    return "\n".join(f"{role} disse: {text}" for role, text in CHAT_HISTORY)


def _profile_text() -> str:
    profile = load_profile() or {}
    if not profile:
        return "Perfil indisponivel."

    nome = str(profile.get("nome", "")).strip()
    curso = str(profile.get("curso", "")).strip()
    foco = profile.get("foco_profissional") or []
    objetivos = profile.get("objetivos") or []
    parts = []
    if nome:
        parts.append(f"Operador: {nome}.")
    if curso:
        parts.append(f"Formacao atual: {curso}.")
    if foco:
        parts.append("Foco tecnico: " + ", ".join(str(item) for item in foco[:4]) + ".")
    if objetivos:
        parts.append("Objetivos: " + ", ".join(str(item) for item in objetivos[:3]) + ".")
    return " ".join(parts) if parts else "Perfil indisponivel."


def _operational_context_text() -> str:
    context = load_operational_context() or {}
    summary = str(context.get("summary", "")).strip()
    if not summary:
        return "Sem contexto operacional consolidado."

    parts = [summary]
    recent_requests = context.get("recent_user_requests") or []
    if recent_requests:
        parts.append("Pedidos recentes: " + " | ".join(str(item) for item in recent_requests[-3:]) + ".")
    preference_summary = str(context.get("preference_summary", "")).strip()
    if preference_summary:
        parts.append("Preferencias operacionais: " + preference_summary + ".")
    next_advances = context.get("next_advances") or []
    if next_advances:
        parts.append("Proximos avancos: " + "; ".join(str(item) for item in next_advances[:2]) + ".")
    return " ".join(parts)


def _current_topic_text() -> str:
    topic = load_current_topic() or {}
    if not topic:
        return "Sem assunto atual consolidado."

    parts = []
    title = str(topic.get("topic", "")).strip()
    summary = str(topic.get("summary", "")).strip()
    source = str(topic.get("source", "")).strip()
    last_question = str(topic.get("last_user_question", "")).strip()
    last_answer = str(topic.get("last_assistant_answer", "")).strip()
    keywords = [str(item).strip() for item in (topic.get("keywords") or []) if str(item).strip()]

    if title:
        parts.append(f"Assunto atual: {title}.")
    if summary:
        parts.append(f"Resumo de apoio: {summary}")
    if source:
        parts.append(f"Origem: {source}.")
    if last_question:
        parts.append(f"Ultima pergunta ligada a esse assunto: {last_question}")
    if last_answer:
        parts.append(f"Ultima resposta ligada a esse assunto: {last_answer}")
    if keywords:
        parts.append("Palavras-chave: " + ", ".join(keywords[:6]) + ".")
    return " ".join(parts) if parts else "Sem assunto atual consolidado."


def _vault_context_text() -> str:
    bootstrap_obsidian_knowledge()
    vault = load_vault_context() or {}
    if not vault:
        return "Vault semantico indisponivel."

    snippets = []
    for key in ("long_memory", "projects", "preferences", "investments", "learning"):
        content = str(vault.get(key, "")).strip()
        if not content:
            continue
        cleaned = re.sub(r"\s+", " ", content)
        snippets.append(f"{key}: {cleaned[:260]}")
    return " ".join(snippets) if snippets else "Vault semantico indisponivel."


def _targeted_vault_context_text(user_input: str) -> str:
    current_topic = load_current_topic() or {}
    query_parts = [str(user_input or "").strip()]
    for key in ("topic", "summary", "page_title"):
        value = str(current_topic.get(key, "")).strip()
        if value:
            query_parts.append(value)
    matches = search_vault_context(" ".join(query_parts), limit=2, max_chars=320)
    if not matches:
        return "Nenhuma nota semantica especialmente relevante encontrada."
    return " ".join(f"{item['name']}: {item['excerpt']}" for item in matches)


def _targeted_docs_context_text(user_input: str) -> str:
    current_topic = load_current_topic() or {}
    query_parts = [str(user_input or "").strip()]
    for key in ("topic", "summary", "page_title"):
        value = str(current_topic.get(key, "")).strip()
        if value:
            query_parts.append(value)
    matches = search_docs_context(" ".join(query_parts), limit=2, max_chars=360)
    if not matches:
        return "Nenhum documento especialmente relevante encontrado."
    return " ".join(f"{item['title']}: {item['excerpt']}" for item in matches)


def _directives_text() -> str:
    try:
        payload = json.loads(DIRECTIVES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return "Diretrizes indisponiveis."

    directives = payload.get("core_directives") or []
    investment = payload.get("investment_mode") or {}
    parts = []
    if directives:
        parts.append("Diretrizes centrais: " + " | ".join(str(item) for item in directives[:4]) + ".")
    investment_goal = str(investment.get("goal", "")).strip()
    if investment_goal:
        parts.append("Modo investimentos: " + investment_goal)
    return " ".join(parts) if parts else "Diretrizes indisponiveis."


def clear_chat_history():
    CHAT_HISTORY.clear()


def _clean_response(response: str) -> str:
    response = (response or "").replace("\r", " ").replace("\n", " ").strip()

    # Some small models continue the dialogue transcript. Keep only the assistant's first turn.
    response = re.split(r"\bUsuario\s*:", response, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    response = re.sub(r"^(Axel|Estagi.rio|Estagiario|Assistente)\s*:\s*", "", response, flags=re.IGNORECASE).strip()

    response = re.split(r"\b(Usuario|Usu.rio|Axel|Estagi.rio|Estagiario|Assistente)\s*:", response, maxsplit=1, flags=re.IGNORECASE)[0].strip()

    sentences = re.split(r"(?<=[.!?])\s+", response)
    response = " ".join(sentence for sentence in sentences[:2] if sentence).strip()

    return response


def _looks_like_complex_request(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    word_count = len([word for word in normalized.split(" ") if word])

    if any(hint in normalized for hint in COMPLEX_REASONING_HINTS):
        return True

    if any(hint in normalized for hint in {"ideia", "ideias", "sugestao", "sugestão", "dica", "dicas", "recomenda"}):
        return True

    if any(hint in normalized for hint in OPEN_ADVICE_HINTS) and (
        "?" in str(user_input or "")
        or any(
            trigger in normalized
            for trigger in {
                "me ajuda",
                "me ajude",
                "pode me ajudar",
                "quero",
                "preciso",
                "qual",
                "como",
                "monta",
                "monte",
                "cria",
                "crie",
                "me da",
                "me dá",
            }
        )
    ):
        return True

    if any(hint in normalized for hint in LEARNING_HINTS) and (
        "?" in str(user_input or "")
        or any(trigger in normalized for trigger in LEARNING_REQUEST_TRIGGERS)
    ):
        return True

    if any(trigger in normalized for trigger in {"me ensina", "ensina", "me explica", "explique", "explica"}) and word_count >= 4:
        return True

    if _looks_like_opinion_request(user_input) and any(hint in normalized for hint in LIVE_CONTEXT_HINTS):
        return True

    if docs_context_relevant(user_input):
        return True

    return word_count >= 18


def _looks_like_factual_question(user_input: str) -> bool:
    normalized = _normalize_for_compare(user_input)
    if not normalized:
        return False

    starters = (
        "o que e",
        "oq e",
        "o que sao",
        "oq sao",
        "quem e",
        "quem foi",
        "qual e",
        "quais sao",
        "onde fica",
        "quando foi",
        "como funciona",
        "por que",
        "porque",
    )
    if normalized.startswith(starters):
        return True

    if "?" in str(user_input or "") and len(normalized.split()) >= 3:
        return True

    return False


def _should_use_gemini(user_input: str) -> bool:
    return bool(GEMINI_COMPLEX_CHAT_ENABLED and GEMINI_API_KEY and _looks_like_complex_request(user_input))


def _chat_decision_plan(user_input: str, *, complex_request: bool):
    intent_level = INTENT_LEVEL_QUESTION if complex_request or _looks_like_factual_question(user_input) else INTENT_LEVEL_CONVERSATION
    complexity_kind = "complex_reasoning" if complex_request else "simple_conversation"
    return build_decision_plan(
        user_input,
        {"intent": "respond", "target": None},
        intent_level=intent_level,
        complexity_kind=complexity_kind,
    )


def _cloud_model_for_policy(model_policy: str) -> str:
    policy = str(model_policy or "").strip().lower()
    if policy == "nvidia_or_gemini_for_reasoning" and NVIDIA_API_KEY:
        return NVIDIA_MODEL
    if GEMINI_API_KEY:
        return GEMINI_MODEL
    return NVIDIA_MODEL


def _estimate_tokens(text: str) -> int:
    clean = str(text or "")
    if not clean:
        return 0
    return max(1, round(len(clean) / 4))


def _estimated_model_cost_usd(provider: str, model: str, total_tokens: int) -> tuple[float, str]:
    if str(provider or "").strip().lower() == "local":
        return 0.0, "local"

    model_name = str(model or "").strip().lower()
    if "gemini" in model_name:
        return round((max(0, int(total_tokens)) / 1000.0) * 0.0001, 6), "rough_estimate"
    return 0.0, "unpriced_or_free_tier"


def _log_model_call(event_type: str, **payload) -> None:
    if event_type == "model_call_end":
        record_model_use(
            provider=str(payload.get("provider") or payload.get("requested_provider") or ""),
            model=str(payload.get("model") or payload.get("requested_model") or ""),
            policy=str(payload.get("model_policy") or ""),
            success=bool(payload.get("success", False)),
            fallback_used=bool(payload.get("fallback_used", False)),
        )
    try:
        append_execution_log(event_type, payload)
    except Exception:
        pass


def _record_rejected_model_attempt(provider: str, model: str, policy: str, *, fallback_used: bool) -> None:
    record_model_use(
        provider=provider,
        model=model,
        policy=policy,
        success=False,
        fallback_used=fallback_used,
    )


def _looks_generic_or_wrong(response: str) -> bool:
    lower = response.lower()
    blocked_fragments = {
        "como posso ajudar",
        "como posso te ajudar",
        "como posso auxiliar",
        "como posso te auxiliar",
        "que posso ajudar",
        "que posso te ajudar",
        "que posso auxiliar",
        "que posso te auxiliar",
        "aqui para ajudar",
        "estou aqui para ajudar",
        "pronto para ajudar",
        "pronta para ajudar",
        "olá, sou um assistente",
        "ola, sou um assistente",
        "assistente de voz inteligente",
        "estou pronto",
        "ok, estou pronto",
        "ok estou pronto",
        "gostei muito de te conhecer",
        "fique a vontade",
        "fique à vontade",
        "voce pode tentar",
        "você pode tentar",
        "desculpe, mas eu",
        "não vou inventar",
        "nao vou inventar",
        "não consegui confirmar",
        "nao consegui confirmar",
        "não tenho uma resposta confiável",
        "nao tenho uma resposta confiavel",
        "sem uma resposta confiável",
        "sem uma resposta confiavel",
        "posso pesquisar para confirmar",
        "mande mais contexto",
        "você pode mandar mais contexto",
        "voce pode mandar mais contexto",
        "tenho um volume de voz adequado",
        "estimado usuario, estou aqui para ajudar",
        "estimado usuário, estou aqui para ajudar",
        "fechou a janela",
        "abrir a janela",
        "abra a janela",
    }

    if any(fragment in lower for fragment in blocked_fragments):
        return True

    if lower.startswith("estagiario") or lower.startswith("estagiário"):
        return True

    return False


def _normalize_for_compare(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _looks_like_opinion_request(user_input: str) -> bool:
    normalized = _normalize_for_compare(user_input)
    if not normalized:
        return False

    if any(hint in normalized for hint in OPINION_HINTS):
        return True

    starters = (
        "o que voce acha",
        "o que vc acha",
        "qual sua opiniao",
        "qual a sua opiniao",
        "sua opiniao",
        "na sua opiniao",
    )
    return normalized.startswith(starters)


def _looks_like_followup_request(user_input: str) -> bool:
    normalized = _normalize_for_compare(user_input)
    if not normalized:
        return False

    starters = (
        "e por que",
        "e porque",
        "por que",
        "porque",
        "e ai",
        "e isso",
        "e agora",
        "e qual",
        "e quais",
        "e como",
        "mas",
        "entao",
        "então",
        "me fala mais",
        "fala mais",
        "me explica melhor",
        "detalha isso",
        "explica isso",
        "vale a pena",
        "qual voce escolheria",
        "qual você escolheria",
        "qual voce prefere",
        "qual você prefere",
        "tem melhores",
        "existem melhores",
        "existe melhor",
    )
    return normalized.startswith(starters)


def _derive_topic_keywords(user_input: str, response: str) -> list[str]:
    text = _normalize_for_compare(f"{user_input} {response}")
    tokens = []
    for token in text.split():
        if len(token) < 4 or token.isdigit():
            continue
        if token in {"isso", "essa", "esse", "porque", "por", "vale", "pena", "acho", "voce", "sobre", "mais", "qual"}:
            continue
        if token not in tokens:
            tokens.append(token)
    return tokens[:6]


def _derive_topic_name(user_input: str, response: str) -> str:
    current = load_current_topic() or {}
    if _looks_like_followup_request(user_input):
        title = str(current.get("topic", "")).strip()
        if title:
            return title

    for source in (response, user_input):
        cleaned = " ".join(str(source or "").split()).strip()
        if len(cleaned) >= 12:
            return cleaned[:180]
    return "Assunto em andamento"


def _response_mode_prompt(user_input: str) -> str:
    normalized = _normalize_for_compare(user_input)
    if any(hint in normalized for hint in LEARNING_HINTS):
        return (
            "Modo de resposta: tutor pratico. "
            "Responda com um primeiro passo acionavel, corrija ou explique sem aula longa e adapte ao nivel aparente do usuario. "
            "Se faltar contexto, assuma um nivel iniciante/intermediario e peca no maximo um detalhe essencial no final."
        )

    if any(hint in normalized for hint in OPEN_ADVICE_HINTS):
        return (
            "Modo de resposta: conselho pratico e personalizado. "
            "Se faltar contexto, assuma um ponto de partida razoavel e diga como ajustar. "
            "De opcoes concretas, evite sermão e peça no maximo um detalhe essencial no final. "
            "Em treino, dieta ou saude, fale em orientacao geral e recomende profissional quando houver risco medico."
        )

    if not _looks_like_opinion_request(user_input):
        return (
            "Modo de resposta: conversa curta e natural. "
            "Se couber, responda diretamente e puxe um detalhe útil."
        )

    live_hint = any(token in normalized for token in LIVE_CONTEXT_HINTS)
    base = (
        "Modo de resposta: opinativo e honesto. "
        "Responda como quem realmente ponderou o assunto. "
        "Separe fato, leitura e limite: fato vem de fonte/memoria/log; leitura e sua interpretacao; limite e o que nao foi verificado. "
        "Nao transforme isso em lista se a fala puder ser natural. "
        "Dê uma leitura própria curta e diga o principal motivo dela."
    )
    if live_hint:
        base += (
            " Se o tema depender de dado atual e você não tiver verificado fonte ao vivo agora, "
            "deixe isso claro e trate sua resposta como leitura provisória."
        )
    return base


def _looks_like_echo(user_input: str, response: str) -> bool:
    user = _normalize_for_compare(user_input)
    answer = _normalize_for_compare(response)

    if not user or not answer:
        return False

    filler_prefixes = (
        "estou lendo",
        "voce disse",
        "você disse",
        "entao",
        "então",
        "sobre isso",
    )
    for prefix in filler_prefixes:
        if answer.startswith(prefix):
            answer = answer[len(prefix):].strip()

    if user in answer and len(answer) <= len(user) + 20:
        return True

    return False


def _looks_incomplete_response(response: str) -> bool:
    text = re.sub(r"\s+", " ", str(response or "")).strip()
    if not text:
        return True

    normalized = _normalize_for_compare(text)
    if normalized in {"e", "é", "o projeto que estamos discutindo atualmente e"}:
        return True

    if text.count("`") % 2 == 1:
        return True

    dangling_phrases = (
        "atualmente e",
        "atualmente é",
        "se chama",
        "foi chamado",
        "foi chamada",
        "e chamado",
        "e chamada",
    )
    if normalized.endswith(dangling_phrases):
        return True

    if len(normalized.split()) >= 5 and not re.search(r"[.!?)]$", text):
        last_word = normalized.rsplit(" ", 1)[-1]
        if last_word in {"e", "de", "do", "da", "para", "com", "sobre", "chama", "chamado", "chamada"}:
            return True
        if len(text) >= 25:
            return True

    return False


def chat_response(user_input: str):
    if not chat_enabled():
        return None

    model = str(PREFERENCES.get("chat_model", "qwen2.5:0.5b")).strip() or "qwen2.5:0.5b"
    complex_request = _looks_like_complex_request(user_input)
    decision_plan = _chat_decision_plan(user_input, complex_request=complex_request)
    cloud_model = _cloud_model_for_policy(decision_plan.model_policy)
    route = select_chat_model_route(
        user_input,
        preferences=PREFERENCES,
        local_model=model,
        cloud_model=cloud_model,
        cloud_available=bool(GEMINI_COMPLEX_CHAT_ENABLED and (GEMINI_API_KEY or NVIDIA_API_KEY)),
        complex_request=complex_request,
        model_policy=decision_plan.model_policy,
    )
    use_gemini = route.uses_cloud
    try:
        timeout = int(PREFERENCES.get("chat_timeout_seconds", 8))
    except (TypeError, ValueError):
        timeout = 8

    opinion_mode = _looks_like_opinion_request(user_input)
    docs_mode = docs_context_relevant(user_input)

    prompt = f"""{build_chat_prompt()}

Historico recente:
{_history_text()}

Perfil do operador:
{_profile_text()}

Memoria curta curada:
{format_curated_memory()}

Contexto operacional:
{_operational_context_text()}

Assunto atual:
{_current_topic_text()}

Memoria semantica do vault:
{_vault_context_text()}

Trechos mais relevantes do vault para esta pergunta:
{_targeted_vault_context_text(user_input)}

Memoria longa relevante:
{format_relevant_long_memory(user_input)}

Sessoes antigas relevantes:
{format_relevant_session_memory(user_input)}

Recall de memoria em camadas:
{format_layered_memory_recall(user_input)}

Skills procedurais relevantes:
{format_relevant_skills(user_input)}

Toolsets relevantes:
{format_relevant_toolsets(user_input)}

Agentes especialistas relevantes:
{format_relevant_agents(user_input)}

Briefing do AxelBrain para esta resposta:
{format_conversation_brief(user_input, complex_request=complex_request)}

Politica de modelo do AxelBrain:
{decision_plan.model_policy}; rota escolhida: {route.provider}/{route.model}; motivo: {route.reason}

Trechos mais relevantes dos documentos de plano e arquitetura:
{_targeted_docs_context_text(user_input)}

Camada inicial de pesquisa com fontes:
{format_research_sources(user_input)}

Diretrizes:
{_directives_text()}

Modo desta resposta:
{_response_mode_prompt(user_input)}

Mensagem atual do usuario:
{user_input}

Resposta curta do Axel:"""

    model_started_at = time.time()
    prompt_tokens = _estimate_tokens(prompt)
    _log_model_call(
        "model_call_start",
        provider=route.provider,
        model=route.model,
        model_policy=decision_plan.model_policy,
        route_reason=route.reason,
        fallback_provider=getattr(route, "fallback_provider", ""),
        prompt_tokens_estimate=prompt_tokens,
        complex_request=complex_request,
    )
    attempted_provider = route.provider
    attempted_model = route.model
    used_fallback = False

    try:
        if use_gemini:
            response = ask_model(
                prompt,
                model=route.model,
                timeout_seconds=max(4, min(timeout + 8, 40)),
                num_predict=210 if docs_mode else (165 if opinion_mode else 135),
                temperature=min(0.8, _chat_temperature() + 0.05),
                provider="cloud",
            )
        else:
            response = ask_model(
                prompt,
                model=route.model,
                timeout_seconds=max(2, min(timeout, 30)),
                num_predict=160 if docs_mode else (120 if opinion_mode else 90),
                temperature=min(0.85, _chat_temperature() + (0.08 if opinion_mode else 0.0)),
                provider="local",
            )
    except Exception:
        if use_gemini:
            try:
                used_fallback = True
                attempted_provider = "local"
                attempted_model = model
                response = ask_model(
                    prompt,
                    model=model,
                    timeout_seconds=max(2, min(timeout, 30)),
                    num_predict=160 if docs_mode else (120 if opinion_mode else 90),
                    temperature=min(0.85, _chat_temperature() + (0.08 if opinion_mode else 0.0)),
                    provider="local",
                )
            except Exception:
                _log_model_call(
                    "model_call_end",
                    provider=attempted_provider,
                    model=attempted_model,
                    requested_provider=route.provider,
                    requested_model=route.model,
                    model_policy=decision_plan.model_policy,
                    fallback_used=used_fallback,
                    success=False,
                    error="cloud_and_local_failed",
                    duration_ms=round((time.time() - model_started_at) * 1000, 2),
                    prompt_tokens_estimate=prompt_tokens,
                    completion_tokens_estimate=0,
                    total_tokens_estimate=prompt_tokens,
                    estimated_cost_usd=0.0,
                    cost_basis="failed",
                )
                return None
        else:
            _log_model_call(
                "model_call_end",
                provider=route.provider,
                model=route.model,
                requested_provider=route.provider,
                requested_model=route.model,
                model_policy=decision_plan.model_policy,
                fallback_used=False,
                success=False,
                error="local_failed",
                duration_ms=round((time.time() - model_started_at) * 1000, 2),
                prompt_tokens_estimate=prompt_tokens,
                completion_tokens_estimate=0,
                total_tokens_estimate=prompt_tokens,
                estimated_cost_usd=0.0,
                cost_basis="failed",
            )
            return None

    response = (response or "").strip()
    if not response:
        _record_rejected_model_attempt(attempted_provider, attempted_model, decision_plan.model_policy, fallback_used=used_fallback)
        return None

    response = _clean_response(response)
    if not response:
        _record_rejected_model_attempt(attempted_provider, attempted_model, decision_plan.model_policy, fallback_used=used_fallback)
        return None

    lower = response.lower()
    if _looks_generic_or_wrong(response):
        _record_rejected_model_attempt(attempted_provider, attempted_model, decision_plan.model_policy, fallback_used=used_fallback)
        return None

    if _looks_like_echo(user_input, response):
        _record_rejected_model_attempt(attempted_provider, attempted_model, decision_plan.model_policy, fallback_used=used_fallback)
        return None

    if _looks_incomplete_response(response):
        _record_rejected_model_attempt(attempted_provider, attempted_model, decision_plan.model_policy, fallback_used=used_fallback)
        return None

    if "meu nome e qwen" in lower or "meu nome é qwen" in lower or "sou qwen" in lower or "sou uma ia local" in lower:
        response = "Sou o Axel. Estou aqui para conversar e ajudar a controlar o PC."

    confused_markers = {
        "nao consigo entender",
        "não consigo entender",
        "nao entendi",
        "não entendi",
        "diga mais sobre",
        "estou esperando sua resposta",
        "aguardo sua resposta",
    }
    if any(marker in lower for marker in confused_markers):
        response = "Posso conversar sim. Me puxa por um assunto simples ou me conta o que voce quer pensar agora."

    max_len = 520 if docs_mode else 350
    if len(response) > max_len:
        response = response[: max_len - 3].rstrip() + "..."

    completion_tokens = _estimate_tokens(response)
    total_tokens = prompt_tokens + completion_tokens
    estimated_cost, cost_basis = _estimated_model_cost_usd(attempted_provider, attempted_model, total_tokens)
    _log_model_call(
        "model_call_end",
        provider=attempted_provider,
        model=attempted_model,
        requested_provider=route.provider,
        requested_model=route.model,
        model_policy=decision_plan.model_policy,
        route_reason=route.reason,
        fallback_provider=getattr(route, "fallback_provider", ""),
        fallback_used=used_fallback,
        success=True,
        duration_ms=round((time.time() - model_started_at) * 1000, 2),
        prompt_tokens_estimate=prompt_tokens,
        completion_tokens_estimate=completion_tokens,
        total_tokens_estimate=total_tokens,
        estimated_cost_usd=estimated_cost,
        cost_basis=cost_basis,
    )

    update_current_topic_from_conversation(
        user_input=user_input,
        assistant_response=response,
        topic=_derive_topic_name(user_input, response),
        source="conversation",
        related_summary="",
        keywords=_derive_topic_keywords(user_input, response),
    )
    CHAT_HISTORY.append(("Usuario", user_input))
    CHAT_HISTORY.append(("Axel", response))
    try:
        index_exchange(user_input, response)
    except Exception:
        pass
    return response
