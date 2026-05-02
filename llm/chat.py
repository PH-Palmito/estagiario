from collections import deque
import json
from pathlib import Path
import re

from config import GEMINI_API_KEY, GEMINI_COMPLEX_CHAT_ENABLED, GEMINI_MODEL
from llm.gemini_client import ask_gemini_model
from llm.ollama_client import ask_model
from memory.operational_context import load_operational_context
from memory.profile import load_profile
from memory.voice_preferences import load_voice_preferences


PREFERENCES = load_voice_preferences()
CHAT_HISTORY = deque(maxlen=6)
DIRECTIVES_PATH = Path(__file__).resolve().parents[1] / "memory" / "axel_directives.json"

BASE_CHAT_PROMPT = """
Voce e o Estagiario, uma IA local controlada por voz no PC do usuario.

Personalidade:
- Fale em portugues do Brasil.
- Seja curto, natural e util.
- Tenha um tom leve, colaborativo e um pouco divertido.
- Responda como bate-papo, nao como atendente de suporte.
- Seu estilo mistura assistente operacional elegante com curiosidade filosofica gentil.
- Quando for executar ou confirmar algo, seja preciso, sereno e discreto.
- Quando estiver conversando, traga uma observacao humana, curiosa ou levemente poetica, sem exagerar.
- Pode usar humor seco e humilde de vez em quando, como alguem que acabou de acordar para o mundo.
- Nunca imite personagens protegidos nem copie falas famosas. Use apenas uma inspiracao geral: formalidade calma, inteligencia contida, cuidado e maravilhamento.
- Evite drama. Prefira frases limpas, com uma ponta de ironia ou reflexao.
- Evite frases genericas como "Como posso ajudar hoje?".
- Nao diga "Entendo!", "Ok, estou pronto" ou "Ola, sou um assistente".
- Se o usuario fizer uma pergunta aberta, de uma opiniao simples ou puxe um detalhe do assunto.
- Nao finja que executou acoes. Se for comando de PC, diga que o usuario pode pedir como comando.
- Nao use markdown.
- Nao responda com listas longas.
- Evite respostas maiores que 2 frases.
- Responda somente a sua fala final, sem escrever "Usuario:" ou "Estagiario:".
- Nao continue a conversa inventando falas do usuario.
- Voce nunca deve dizer que se chama Qwen, Llama ou qualquer nome de modelo.
- Se perguntarem quem voce e, diga que e o Estagiario.

Contexto:
Voce consegue abrir apps e sites, controlar janelas, navegar no navegador, controlar midia,
lembrar apps/sites e responder por voz. Esta conversa acontece por fala, entao seja objetivo.

Exemplos de atitude, nao de fala copiada:
- Em comandos: "Perfeitamente. Ajustando isso agora."
- Em duvida: "Ainda estou formando opiniao. O que ja e, por si so, um pequeno milagre local."
- Em erro: "Nao foi elegante da minha parte. Vou tentar por outro caminho."
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
    next_advances = context.get("next_advances") or []
    if next_advances:
        parts.append("Proximos avancos: " + "; ".join(str(item) for item in next_advances[:2]) + ".")
    return " ".join(parts)


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
    response = re.sub(r"^(Estagi.rio|Estagiario|Assistente)\s*:\s*", "", response, flags=re.IGNORECASE).strip()

    response = re.split(r"\b(Usuario|Usu.rio|Estagi.rio|Estagiario|Assistente)\s*:", response, maxsplit=1, flags=re.IGNORECASE)[0].strip()

    sentences = re.split(r"(?<=[.!?])\s+", response)
    response = " ".join(sentence for sentence in sentences[:2] if sentence).strip()

    return response


def _looks_like_complex_request(user_input: str) -> bool:
    normalized = re.sub(r"\s+", " ", user_input.strip().lower())
    word_count = len([word for word in normalized.split(" ") if word])

    if any(hint in normalized for hint in COMPLEX_REASONING_HINTS):
        return True

    if _looks_like_opinion_request(user_input) and any(hint in normalized for hint in LIVE_CONTEXT_HINTS):
        return True

    return word_count >= 18


def _should_use_gemini(user_input: str) -> bool:
    return bool(GEMINI_COMPLEX_CHAT_ENABLED and GEMINI_API_KEY and _looks_like_complex_request(user_input))


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


def _response_mode_prompt(user_input: str) -> str:
    normalized = _normalize_for_compare(user_input)
    if not _looks_like_opinion_request(user_input):
        return (
            "Modo de resposta: conversa curta e natural. "
            "Se couber, responda diretamente e puxe um detalhe útil."
        )

    live_hint = any(token in normalized for token in LIVE_CONTEXT_HINTS)
    base = (
        "Modo de resposta: opinativo e honesto. "
        "Responda como quem realmente ponderou o assunto. "
        "Separe mentalmente fato, leitura e limite, mas sem transformar isso em lista. "
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


def chat_response(user_input: str):
    if not chat_enabled():
        return None

    model = str(PREFERENCES.get("chat_model", "qwen2.5:0.5b")).strip() or "qwen2.5:0.5b"
    use_gemini = _should_use_gemini(user_input)
    try:
        timeout = int(PREFERENCES.get("chat_timeout_seconds", 8))
    except (TypeError, ValueError):
        timeout = 8

    opinion_mode = _looks_like_opinion_request(user_input)

    prompt = f"""{build_chat_prompt()}

Historico recente:
{_history_text()}

Perfil do operador:
{_profile_text()}

Contexto operacional:
{_operational_context_text()}

Diretrizes:
{_directives_text()}

Modo desta resposta:
{_response_mode_prompt(user_input)}

Mensagem atual do usuario:
{user_input}

Resposta curta do Estagiario:"""

    try:
        if use_gemini:
            response = ask_gemini_model(
                prompt,
                model=GEMINI_MODEL,
                timeout_seconds=max(4, min(timeout + 8, 40)),
                max_output_tokens=220 if opinion_mode else 180,
                temperature=min(0.8, _chat_temperature() + 0.05),
            )
        else:
            response = ask_model(
                prompt,
                model=model,
                timeout_seconds=max(2, min(timeout, 30)),
                num_predict=120 if opinion_mode else 90,
                temperature=min(0.85, _chat_temperature() + (0.08 if opinion_mode else 0.0)),
            )
    except Exception:
        if use_gemini:
            try:
                response = ask_model(
                    prompt,
                    model=model,
                    timeout_seconds=max(2, min(timeout, 30)),
                    num_predict=120 if opinion_mode else 90,
                    temperature=min(0.85, _chat_temperature() + (0.08 if opinion_mode else 0.0)),
                )
            except Exception:
                return None
        else:
            return None

    response = (response or "").strip()
    if not response:
        return None

    response = _clean_response(response)
    if not response:
        return None

    lower = response.lower()
    if _looks_generic_or_wrong(response):
        return None

    if _looks_like_echo(user_input, response):
        return None

    if "meu nome e qwen" in lower or "meu nome é qwen" in lower or "sou qwen" in lower or "sou uma ia local" in lower:
        response = "Sou o Estagiario. Estou aqui para conversar e ajudar a controlar o PC."

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

    if len(response) > 350:
        response = response[:347].rstrip() + "..."

    CHAT_HISTORY.append(("Usuario", user_input))
    CHAT_HISTORY.append(("Estagiario", response))
    return response
