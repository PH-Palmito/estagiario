from __future__ import annotations

import random
from itertools import count
from pathlib import Path

from memory.json_store import read_json_file, write_json_atomic

_PHRASE_COUNTERS: dict[str, count] = {}
PHRASE_STATE_PATH = Path("memory") / "assistant_phrase_state.json"
MAX_RECENT_PHRASES = 5


def _load_phrase_state() -> dict:
    return read_json_file(PHRASE_STATE_PATH, {}, validator=lambda value: isinstance(value, dict))


def _save_phrase_state(state: dict) -> None:
    try:
        write_json_atomic(PHRASE_STATE_PATH, state, indent=2, trailing_newline=True)
    except Exception:
        pass


def next_phrase(key: str, options: tuple[str, ...], default: str = "") -> str:
    if not options:
        return default
    if len(options) == 1:
        return options[0]

    state = _load_phrase_state()
    recent_by_key = state.get("recent") if isinstance(state.get("recent"), dict) else {}
    recent = [str(item) for item in recent_by_key.get(key, []) if str(item)]

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


def contextual_startup_phrase(category: str, address_user: str = "chefe", greeting: str = "Bom dia") -> str:
    category = str(category or "").strip() or "study_code"
    state_key = f"contextual_startup:{category}"
    state = _load_phrase_state()
    recent_by_key = state.get("recent") if isinstance(state.get("recent"), dict) else {}
    recent = [str(item) for item in recent_by_key.get(state_key, []) if str(item)]

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
