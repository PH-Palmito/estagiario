from __future__ import annotations

from itertools import count


_PHRASE_COUNTERS: dict[str, count] = {}


def next_phrase(key: str, options: tuple[str, ...], default: str = "") -> str:
    if not options:
        return default
    counter = _PHRASE_COUNTERS.setdefault(key, count())
    index = next(counter) % len(options)
    return options[index]


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
