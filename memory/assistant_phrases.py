from __future__ import annotations

import random
import re
import time
from itertools import count
from pathlib import Path

from memory.json_store import read_json_file, update_json_file, write_json_atomic

_PHRASE_COUNTERS: dict[str, count] = {}
PHRASE_STATE_PATH = Path("memory") / "assistant_phrase_state.json"
STARTUP_PHRASES_PATH = Path("memory") / "startup_phrases.json"
MAX_RECENT_PHRASES = 5
MAX_LEARNED_STARTUP_PHRASES = 60
ASSISTANT_PHRASE_PATH = STARTUP_PHRASES_PATH

ASSISTANT_PHRASE_CATEGORIES: dict[str, dict[str, str]] = {
    "computer_startup": {
        "title": "inicialização",
        "purpose": "frases curtas para quando o Axel abre junto com voz e painel",
    },
    "short_ready": {
        "title": "prontidão curta",
        "purpose": "frases muito curtas para avisar que o Axel está ouvindo",
    },
    "study_code": {
        "title": "estudo e código",
        "purpose": "frases curtas para sessões de estudo, arquivos e programação",
    },
    "night_sleep_prompt": {
        "title": "aviso noturno",
        "purpose": "frases discretas para lembrar o usuário de salvar o progresso e descansar tarde da noite",
    },
}


def _load_phrase_state() -> dict:
    return read_json_file(PHRASE_STATE_PATH, {}, validator=lambda value: isinstance(value, dict))


def _save_phrase_state(state: dict) -> None:
    try:
        write_json_atomic(PHRASE_STATE_PATH, state, indent=2, trailing_newline=True)
    except Exception:
        pass


OBSOLETE_STARTUP_MARKERS = (
    "Sistema est",
    "Rotinas operacionais",
    "Pronto para consultas",
    "Monitoramento de agenda",
    "proximo avanco",
    "prÃ³ximo avan",
    "progresso concreto",
    "tarefa pequena",
    "Briefing",
    "Resumo do dia",
    "Panorama de hoje",
)

STARTUP_PHRASE_BLOCKLIST = (
    *OBSOLETE_STARTUP_MARKERS,
    "Como posso ajudar",
    "Aguardando instru",
    "modo operacional",
    "sistemas online",
    "sistemas prontos",
    "assistente pronto",
    "pronto para comando",
    "pronto para comandos",
    "pronto para consulta",
    "pronto para consultas",
    "pronto para comecar",
    "pronto para começar",
    "pronto para o que",
    "aqui estou",
    "aqui estou eu",
    "inteligencia adaptativa",
)

STARTUP_PHRASE_WEAK_ENDINGS = (
    " para o que",
    " pra o que",
    " para que",
    " pra que",
)

INCOMPLETE_TRAILING_WORDS = {
    "a",
    "as",
    "com",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "mas",
    "no",
    "nos",
    "o",
    "os",
    "para",
    "por",
    "que",
    "se",
}

INCOMPLETE_TRAILING_CONTEXT_WORDS = {
    "boa",
    "bom",
    "grande",
    "melhor",
    "nova",
    "novo",
    "primeira",
    "primeiro",
    "próxima",
    "próximo",
    "ultima",
    "última",
    "ultimo",
    "último",
}


def _startup_recent_is_obsolete(text: str) -> bool:
    return any(marker.lower() in str(text or "").lower() for marker in OBSOLETE_STARTUP_MARKERS)


def _plain_startup_phrase(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip(" \t\r\n\"'`*-")


def _normalize_learned_startup_phrase(text: str) -> str:
    phrase = _plain_startup_phrase(text)
    try:
        from voice.tts_text import _repair_mojibake, _restore_common_ptbr_accents

        phrase = _restore_common_ptbr_accents(_repair_mojibake(phrase))
    except Exception:
        pass
    phrase = re.sub(r"\bja esta\b", "já está", phrase, flags=re.IGNORECASE)
    phrase = re.sub(r"\bja estou\b", "já estou", phrase, flags=re.IGNORECASE)
    phrase = re.sub(r"\bta\b", "tá", phrase, flags=re.IGNORECASE)
    phrase = re.sub(r"\bmao\b", "mão", phrase, flags=re.IGNORECASE)
    phrase = re.sub(r"\bpe\b", "pé", phrase, flags=re.IGNORECASE)
    phrase = re.sub(r"\s+([.!?])", r"\1", phrase).strip()
    phrase = phrase.rstrip(",:;")
    if phrase and phrase[-1] not in ".!?":
        phrase += "."
    return phrase


def _startup_phrase_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _plain_startup_phrase(text).lower()).strip()


def is_valid_startup_phrase(text: str) -> bool:
    phrase = _normalize_learned_startup_phrase(text)
    if not phrase:
        return False
    if len(phrase) < 4 or len(phrase) > 110:
        return False
    words = phrase.split()
    if len(words) < 4 or len(words) > 16:
        return False
    lowered = phrase.lower()
    if any(marker.lower() in lowered for marker in STARTUP_PHRASE_BLOCKLIST):
        return False
    if lowered.rstrip(".!?").endswith(STARTUP_PHRASE_WEAK_ENDINGS):
        return False
    last_word_match = re.search(r"([a-zà-ÿ]+)[.!?]?$", lowered, flags=re.IGNORECASE)
    if last_word_match and last_word_match.group(1) in INCOMPLETE_TRAILING_WORDS:
        return False
    if last_word_match and last_word_match.group(1) in INCOMPLETE_TRAILING_CONTEXT_WORDS:
        return False
    if re.search(r"\b(estou|pronto|ok|beleza)\.?$", lowered):
        return False
    if phrase.count(".") > 2 or phrase.count("!") > 1 or phrase.count("?") > 1:
        return False
    return True


def load_learned_startup_phrases(category: str | None = None) -> tuple[str, ...]:
    data = read_json_file(STARTUP_PHRASES_PATH, {"items": []}, validator=lambda value: isinstance(value, dict))
    items = data.get("items") if isinstance(data.get("items"), list) else []
    category_filter = str(category or "").strip()
    phrases: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        if category_filter and str(item.get("category") or "") != category_filter:
            continue
        phrase = _normalize_learned_startup_phrase(item.get("text", ""))
        key = _startup_phrase_key(phrase)
        if key in seen or not is_valid_startup_phrase(phrase):
            continue
        phrases.append(phrase)
        seen.add(key)
    return tuple(phrases)


def save_learned_startup_phrases(category: str, phrases: list[str], *, source: str = "generated") -> list[str]:
    category = str(category or "computer_startup").strip() or "computer_startup"
    accepted: list[str] = []
    seen_new: set[str] = set()
    for phrase in phrases:
        cleaned = _normalize_learned_startup_phrase(phrase)
        key = _startup_phrase_key(cleaned)
        if key in seen_new or not is_valid_startup_phrase(cleaned):
            continue
        if category == "night_sleep_prompt":
            lowered = cleaned.lower()
            if lowered.startswith("já está tarde.") or lowered.count(".") > 1:
                continue
        accepted.append(cleaned)
        seen_new.add(key)

    if not accepted:
        return []

    def update(data: dict) -> dict:
        items = [item for item in (data.get("items") or []) if isinstance(item, dict)]
        existing_keys = {_startup_phrase_key(str(item.get("text") or "")) for item in items}
        now = time.time()
        for phrase in accepted:
            key = _startup_phrase_key(phrase)
            if key in existing_keys:
                continue
            items.append(
                {
                    "text": phrase,
                    "category": category,
                    "source": str(source or "generated"),
                    "created_at": now,
                    "uses": 0,
                }
            )
            existing_keys.add(key)
        return {"items": items[-MAX_LEARNED_STARTUP_PHRASES:]}

    update_json_file(
        STARTUP_PHRASES_PATH,
        {"items": []},
        update,
        validator=lambda value: isinstance(value, dict),
        indent=2,
        trailing_newline=True,
    )
    return accepted


def _record_learned_startup_phrase_use(text: str) -> None:
    key = _startup_phrase_key(text)
    if not key:
        return

    def update(data: dict) -> dict:
        items = [item for item in (data.get("items") or []) if isinstance(item, dict)]
        for item in items:
            if _startup_phrase_key(str(item.get("text") or "")) == key:
                item["uses"] = int(item.get("uses") or 0) + 1
                item["last_used_at"] = time.time()
                break
        return {"items": items}

    update_json_file(
        STARTUP_PHRASES_PATH,
        {"items": []},
        update,
        validator=lambda value: isinstance(value, dict),
        indent=2,
        trailing_newline=True,
    )


def _extract_generated_startup_lines(raw_text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in str(raw_text or "").splitlines():
        line = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", raw_line).strip()
        if not line:
            continue
        if line.startswith("{") or line.startswith("["):
            continue
        lines.append(line)
    if len(lines) <= 1:
        parts = re.split(r"(?<=[.!?])\s+", str(raw_text or ""))
        lines = [part.strip() for part in parts if part.strip()]
    return lines


def generate_startup_phrase_candidates(
    category: str = "computer_startup",
    *,
    ask_model_fn=None,
    count: int = 8,
) -> list[str]:
    if ask_model_fn is None:
        from llm.ollama_client import ask_model as ask_model_fn

    category = str(category or "computer_startup").strip() or "computer_startup"
    category_info = ASSISTANT_PHRASE_CATEGORIES.get(category, ASSISTANT_PHRASE_CATEGORIES["computer_startup"])
    existing = list(default_phrases_for_category(category)) + list(load_learned_startup_phrases(category))
    category_rules = (
        "Regras extras:\n- Para aviso noturno, use uma única sentença e não comece com \"Já está tarde.\"\n"
        if category == "night_sleep_prompt"
        else ""
    )
    prompt = f"""
Crie {max(3, int(count))} frases curtas para o Axel.

Contexto:
- Axel e um assistente local de voz no Windows.
- Categoria: {category_info["title"]}.
- Uso: {category_info["purpose"]}.
- O usuário não gosta de frases genéricas, prontas ou solenes.

Regras:
- Português do Brasil.
- Use acentuação e pontuação corretas.
- Uma frase por linha.
- Máximo 14 palavras por frase.
- Natural, discreta, um pouco viva.
- Frases completas, sem parecer resposta cortada.
- Não use: sistema pronto, rotinas operacionais, monitoramento ativo, como posso ajudar, aguardando instruções.
- N?o gere fragmentos curtos demais como "Estou", "Aqui estou" ou "Pronto para o que".
{category_rules}
- Não copie estas frases existentes: {existing[:16]}

Responda apenas as frases, uma por linha.
""".strip()
    try:
        raw = ask_model_fn(prompt, timeout_seconds=8, num_predict=180, temperature=0.9)
    except Exception:
        return []
    return _extract_generated_startup_lines(raw)


def generate_and_save_startup_phrases(
    category: str = "computer_startup",
    *,
    ask_model_fn=None,
    count: int = 8,
) -> list[str]:
    candidates = generate_startup_phrase_candidates(category, ask_model_fn=ask_model_fn, count=count)
    return save_learned_startup_phrases(category, candidates, source="llm")


def next_phrase(key: str, options: tuple[str, ...], default: str = "") -> str:
    if not options:
        return default
    if len(options) == 1:
        return options[0]

    state = _load_phrase_state()
    recent_by_key = state.get("recent") if isinstance(state.get("recent"), dict) else {}
    recent = [str(item) for item in recent_by_key.get(key, []) if str(item)]
    if key.startswith(("contextual_startup:", "contextual_phrase:", "startup_fragment_", "startup_greeting_", "startup_briefing_")):
        recent = [item for item in recent if not _startup_recent_is_obsolete(item)]

    candidates = [option for option in options if option not in recent]
    if not candidates:
        counter = _PHRASE_COUNTERS.setdefault(key, count())
        offset = next(counter) % len(options)
        candidates = list(options[offset:] + options[:offset])

    choice = random.choice(candidates)
    recent.append(choice)
    keep = min(MAX_RECENT_PHRASES, max(1, len(options) - 1))
    recent_by_key[key] = recent[-keep:]
    state["recent"] = recent_by_key
    _save_phrase_state(state)
    return choice


STARTUP_GREETING_FRAGMENTS: dict[str, tuple[str, ...]] = {
    "openers": (
        "{greeting}, {address_user}.",
        "Axel online, {address_user}.",
        "Bem-vindo de volta, {address_user}.",
        "Sistema iniciado, {address_user}.",
        "Retomando operações, {address_user}.",
    ),
    "study_focus": (
        "Ambiente pronto para estudo e desenvolvimento.",
        "Seu espaço de código está pronto.",
        "Modo desenvolvimento disponível.",
        "Rotina de estudos carregada.",
        "Sessão técnica iniciada.",
    ),
    "operations": (
        "Escuta disponível pelo F8.",
        "Rotinas operacionais carregadas.",
        "Monitoramento de agenda, carteira e lembretes ativo.",
        "Sistema estável e pronto para comandos.",
        "Pronto para consultas rápidas, código e automações.",
    ),
    "nudges": (
        "Podemos começar por uma tarefa pequena e fechar com progresso real.",
        "O próximo avanço está a um comando de distância.",
        "Me diga o alvo de hoje e eu acompanho a execução.",
        "Podemos revisar, construir ou corrigir.",
        "Vamos transformar pendências em progresso concreto.",
    ),
}

STARTUP_GREETING_FRAGMENTS.update(
    {
        "openers": (
            "{greeting}, {address_user}.",
            "Axel online, {address_user}.",
            "Bem-vindo de volta, {address_user}.",
            "Estou por aqui, {address_user}.",
            "Sessão aberta, {address_user}.",
        ),
        "operations": (
            "Escuta disponível pelo F8.",
            "Painel e voz prontos.",
            "Agenda, carteira e lembretes no radar.",
            "Pode mandar o comando.",
            "Tudo certo para seguir.",
        ),
        "nudges": (
            "Me diga o alvo e eu acompanho.",
            "Podemos revisar, construir ou testar.",
            "Se quiser, começamos pelo mais urgente.",
            "Estou pronto para a próxima tarefa.",
            "Seguimos no seu ritmo.",
        ),
    }
)

CONTEXTUAL_STARTUP_LINES: dict[str, tuple[str, ...]] = {
    "short_ready": (
        "Estou aqui.",
        "Pode mandar.",
        "F8 na mão.",
        "Pronto, sem cerimônia.",
        "Tô ouvindo.",
        "Painel no ar.",
        "Seguimos.",
        "Chama.",
        "Axel acordado.",
        "Voz pronta.",
        "Estou em espera.",
        "Pode abrir a primeira frente.",
    ),
    "computer_startup": (
        "{greeting}, {address_user}. Deixei voz e painel de pé.",
        "{greeting}, {address_user}. Hoje eu fico mais quieto e mais útil.",
        "Voltei. Se o PC colaborar, eu também colaboro.",
        "Estou no ar. Pode começar pequeno ou jogar uma tarefa grande.",
        "Axel ativo. Vou poupar discurso e esperar o alvo.",
        "{greeting}. Agenda e lembretes estão no canto do olho.",
        "Sessão aberta. Me chama quando quiser mover alguma coisa.",
        "Estou aqui, {address_user}. Sem fanfarra.",
        "Painel pronto. Voz pronta. O resto a gente descobre fazendo.",
        "Bom retorno. Vou acompanhar sem ficar narrando tudo.",
        "Estou de pé. Pode mandar o primeiro comando.",
        "Tudo carregado. Vamos no que importa.",
    ),
    "study_code": (
        "Abri a bancada. Qual arquivo ou ideia vem primeiro?",
        "Se for código, a gente corta pelo erro mais concreto.",
        "Se for estudo, posso resumir, perguntar ou corrigir.",
        "Pode jogar o problema inteiro; eu separo em partes.",
        "Estou pronto para ler, testar ou organizar.",
        "Vamos pelo menor passo que destrava o resto.",
        "Tenho contexto suficiente para começar. Manda o alvo.",
        "Hoje vale fechar uma coisa bem feita.",
    ),
}


ASSISTANT_CONTEXT_LINES: dict[str, tuple[str, ...]] = {
    "night_sleep_prompt": (
        "Salva o progresso antes de encerrar por hoje.",
        "Relógio avançou, melhor salvar tudo antes de dormir.",
        "Se não for urgente, vale fechar o ciclo por hoje.",
        "Passou do horário, salva o que importa e descansa.",
        "Ainda por aqui, guarda o progresso antes de desligar.",
        "Boa hora para salvar o trabalho e descansar.",
    ),
}


def default_phrases_for_category(category: str) -> tuple[str, ...]:
    category = str(category or "").strip()
    return CONTEXTUAL_STARTUP_LINES.get(category) or ASSISTANT_CONTEXT_LINES.get(category) or ()


def contextual_assistant_phrase(category: str) -> str:
    category = str(category or "").strip()
    learned_options = load_learned_startup_phrases(category)
    direct_options = ASSISTANT_CONTEXT_LINES.get(category, ())
    options = tuple(dict.fromkeys((*learned_options, *direct_options)))
    phrase = next_phrase(f"contextual_phrase:{category}", options)
    if phrase in learned_options:
        _record_learned_startup_phrase_use(phrase)
    return phrase


def contextual_startup_phrase(category: str, address_user: str = "chefe", greeting: str = "Bom dia") -> str:
    category = str(category or "").strip() or "study_code"
    state_key = f"contextual_startup:{category}"
    state = _load_phrase_state()
    recent_by_key = state.get("recent") if isinstance(state.get("recent"), dict) else {}
    recent = [
        str(item)
        for item in recent_by_key.get(state_key, [])
        if str(item) and not _startup_recent_is_obsolete(str(item))
    ]

    direct_options = CONTEXTUAL_STARTUP_LINES.get(category)
    if direct_options:
        learned_options = load_learned_startup_phrases(category)
        options = tuple(dict.fromkeys((*learned_options, *direct_options)))
        phrase_template = next_phrase(state_key, options)
        phrase = phrase_template.format(
            greeting=greeting,
            address_user=address_user,
        )
        if phrase_template in learned_options:
            _record_learned_startup_phrase_use(phrase_template)
        recent.append(phrase)
        recent_by_key[state_key] = recent[-20:]
        state["recent"] = recent_by_key
        _save_phrase_state(state)
        return phrase

    phrase = ""
    for _attempt in range(8):
        opener = next_phrase("startup_fragment_openers", STARTUP_GREETING_FRAGMENTS["openers"]).format(
            greeting=greeting,
            address_user=address_user,
        )

        if category in {"short_ready", "computer_startup"}:
            operation = next_phrase("startup_fragment_operations_short", STARTUP_GREETING_FRAGMENTS["operations"])
            phrase = f"{opener} {operation}"
        else:
            focus_key = "startup_fragment_operations" if category == "computer_startup" else "startup_fragment_study_focus"
            focus_options = (
                STARTUP_GREETING_FRAGMENTS["operations"]
                if category == "computer_startup"
                else STARTUP_GREETING_FRAGMENTS["study_focus"]
            )
            focus = next_phrase(focus_key, focus_options)
            nudge = next_phrase("startup_fragment_nudges", STARTUP_GREETING_FRAGMENTS["nudges"])
            phrase = f"{opener} {focus} {nudge}"

        if phrase not in recent:
            break

    if phrase:
        recent.append(phrase)
        recent_by_key[state_key] = recent[-20:]
        state["recent"] = recent_by_key
        _save_phrase_state(state)

    return phrase


STARTUP_GREETING_VARIANTS: dict[str, tuple[str, ...]] = {
    "study_code": (
        "Bom dia, chefe. Ambiente pronto para estudo, desenvolvimento e execução de ideias.",
        "Axel online. Hoje podemos avançar em mobile, front-end ou automação local.",
        "Seu ambiente de código está pronto. Posso ajudar com estrutura, revisão ou próxima etapa.",
        "Sessão iniciada. Recomendo começar por uma tarefa pequena e fechar com progresso real.",
        "Modo desenvolvimento disponível. Vamos transformar pendências em commits.",
        "Tudo pronto para programar. Só preciso do alvo de hoje.",
        "Rotina de estudos carregada. Podemos revisar, construir ou corrigir.",
        "Chefe, o ambiente está pronto. Quebre o problema em partes e eu acompanho.",
    ),
    "computer_startup": (
        "Bom dia, chefe. Sistemas ativos. Estou verificando clima, agenda, carteira e próximas prioridades.",
        "Inicialização concluída. Axel online. Pronto para apoiar seus estudos, projetos e automações.",
        "Bem-vindo de volta, chefe. Ambiente carregado, escuta pronta no F8 e rotinas operacionais disponíveis.",
        "Sistema iniciado com sucesso. Hoje é um bom dia para avançar um pouco mais do que ontem.",
        "Axel online. Monitorando clima, agenda, carteira e tarefas importantes. Aguardando instruções.",
        "Boa noite, chefe. Computador ativo, assistente pronto e modo operacional iniciado.",
        "Retomando operações. Seu ambiente de desenvolvimento está pronto para mais uma sessão.",
        "Inicialização finalizada. Já estou de prontidão para comandos, estudos, código e consultas rápidas.",
        "Bom retorno, chefe. Nada como um sistema limpo e uma mente focada para começar.",
        "Axel em execução. Escuta por F8 ativada. Podemos começar quando quiser.",
    ),
    "short_ready": (
        "Axel online. À sua disposição, chefe.",
        "Sistemas prontos. Pode chamar pelo F8.",
        "Pronto para operar.",
        "Ambiente carregado. Vamos avançar.",
        "Tudo pronto, chefe.",
        "Escuta ativa. Aguardando comando.",
        "Modo assistente iniciado.",
        "Rotinas carregadas. Sistema estável.",
        "Bom retorno. Estou em prontidão.",
        "Axel ativo. Vamos trabalhar.",
    ),
    "briefing_already_delivered": (
        "Briefing de hoje já foi entregue. Estou em escuta e monitorando seus lembretes.",
        "Resumo do dia já entregue, chefe. Escuta disponível pelo F8.",
        "Briefing diário já concluído. Continuo monitorando agenda, carteira e lembretes.",
        "Panorama de hoje já foi enviado. Estou pronto para comandos, estudos e código.",
        "Briefing já registrado para hoje. Seguimos em modo operacional.",
    ),
}

STARTUP_GREETING_VARIANTS.update(
    {
        "computer_startup": (
            "Estou no ar. Pode mandar o alvo.",
            "Voltei quieto. F8 quando quiser.",
            "Painel no ar. Vamos no que importa.",
            "Pode começar pequeno ou jogar a tarefa grande.",
            "Estou aqui. Sem discurso de abertura.",
            "Bom retorno. Vou acompanhar sem narrar tudo.",
            "Axel acordado. O primeiro comando é seu.",
            "Voz e painel de pé.",
            "Tudo carregado. Seguimos.",
            "Pode chamar quando quiser mover alguma coisa.",
        ),
        "short_ready": (
            "Estou aqui.",
            "Pode mandar.",
            "F8 na mão.",
            "Sem cerimônia.",
            "Tô ouvindo.",
            "Painel no ar.",
            "Seguimos.",
            "Chama.",
            "Axel acordado.",
            "Voz pronta.",
        ),
        "briefing_already_delivered": (
            "",
        ),
    }
)


ACTION_PROGRESS_VARIANTS: dict[str, tuple[str, ...]] = {
    "vision_answer_question": (
        "Consultando a última análise salva...",
        "Retomando a última leitura...",
        "Puxando o contexto visual salvo...",
    ),
    "browser_describe_screen": (
        "Lendo a tela...",
        "Fazendo uma leitura rápida da tela...",
        "Captando o que está visível...",
    ),
    "browser_explain_screen": (
        "Analisando o conteúdo principal...",
        "Entrando no ponto central da página...",
        "Separando o que realmente importa nessa tela...",
    ),
    "browser_summarize_screen": (
        "Resumindo a tela...",
        "Montando um panorama da tela...",
        "Condensando o que aparece na página...",
    ),
    "browser_investment_snapshot": (
        "Analisando seus investimentos...",
        "Lendo o panorama da sua carteira...",
        "Conferindo os sinais principais da carteira...",
    ),
    "browser_open_wallet_and_summarize": (
        "Abrindo e analisando sua carteira...",
        "Abrindo sua carteira e organizando os pontos principais...",
        "Entrando na sua carteira para montar um resumo útil...",
    ),
    "investment_refresh_public_wallet": (
        "Atualizando sua carteira...",
        "Sincronizando a memória da carteira...",
        "Renovando os dados da sua carteira...",
    ),
    "investment_memory_summary": (
        "Verificando sua carteira...",
        "Consultando sua carteira...",
        "Conferindo sua carteira...",
    ),
    "investment_memory_answer": (
        "Verificando sua carteira...",
        "Consultando sua carteira...",
        "Cruzando sua carteira com a memória salva...",
    ),
    "investment_memory_status": (
        "Verificando sua carteira...",
        "Conferindo o estado da sua carteira...",
        "Checando a atualização da sua carteira...",
    ),
    "browser_read_selection": (
        "Lendo o texto selecionado...",
        "Abrindo o trecho selecionado...",
        "Conferindo o texto marcado...",
    ),
    "browser_read_selected_products": (
        "Lendo os produtos selecionados...",
        "Conferindo os itens destacados...",
        "Separando os produtos marcados...",
    ),
    "browser_translate_last_selection": (
        "Traduzindo o último texto selecionado...",
        "Traduzindo o último trecho marcado...",
        "Convertendo o último texto para você...",
    ),
    "browser_translate_selection": (
        "Traduzindo o texto selecionado...",
        "Traduzindo o trecho marcado...",
        "Convertendo o texto da seleção...",
    ),
    "browser_read_more": (
        "Lendo mais conteúdo da página...",
        "Buscando mais contexto nessa página...",
        "Puxando mais conteúdo útil da tela...",
    ),
    "browser_find": (
        "Procurando na página...",
        "Buscando esse ponto na página...",
        "Varrendo a página por esse trecho...",
    ),
    "browser_search_site": (
        "Pesquisando no site...",
        "Rodando a busca nesse site...",
        "Fazendo a pesquisa dentro da página...",
    ),
    "code_inspect_workspace": (
        "Inspecionando o código do projeto...",
        "Varrendo o código do workspace...",
        "Conferindo o estado do código...",
    ),
    "code_inspect_target": (
        "Inspecionando o arquivo solicitado...",
        "Lendo o arquivo que você pediu...",
        "Conferindo o trecho solicitado...",
    ),
    "code_inspect_selection": (
        "Inspecionando o código selecionado...",
        "Conferindo o trecho selecionado...",
        "Lendo o bloco de código marcado...",
    ),
    "weather_summary": (
        "Consultando o clima...",
        "Verificando a previsão...",
        "Lendo as condições do tempo...",
    ),
    "daily_briefing": (
        "Preparando seu briefing...",
        "Montando seu panorama do dia...",
        "Organizando seu briefing agora...",
    ),
    "agenda_list": (
        "Consultando sua agenda...",
        "Conferindo seus compromissos...",
        "Abrindo sua agenda...",
    ),
}


STYLE_VARIANTS: dict[str, tuple[str, ...]] = {
    "ready_prompt": (
        "Estou ouvindo.",
        "Pode prosseguir.",
        "Pode mandar.",
    ),
    "ready_prompt_addressed": (
        "Estou ouvindo, {address_user}.",
        "Pode prosseguir, {address_user}.",
        "Pode falar, {address_user}.",
    ),
    "repeat_prompt": (
        "Pode repetir com calma?",
        "Repita para mim com mais clareza.",
        "Vamos tentar de novo. Pode repetir?",
    ),
    "unclear_command": (
        "Não captei com precisão.",
        "Esse comando não ficou claro para mim.",
        "Não consegui entender o comando com segurança.",
    ),
    "action_prefix": (
        "Certamente. {message}",
        "Perfeitamente. {message}",
        "Como desejar, {address_user}. {message}",
    ),
}
