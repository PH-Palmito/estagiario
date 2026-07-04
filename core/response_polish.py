from __future__ import annotations

import re

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


def trim_incomplete_final_fragment(message: str) -> str:
    text = re.sub(r"\s+", " ", str(message or "")).strip()
    if not text or "\n" in str(message or ""):
        return str(message or "").strip()

    trailing_fragment = re.match(r"^(.+[.!?])\s+([A-Za-zÀ-ÿ]{1,8})$", text)
    if trailing_fragment:
        fragment = trailing_fragment.group(2).lower()
        if fragment in INCOMPLETE_TRAILING_WORDS or len(fragment) <= 2:
            return trailing_fragment.group(1).strip()

    last_word_match = re.search(r"([A-Za-zÀ-ÿ]+)[.!?]?$", text)
    if last_word_match and (
        last_word_match.group(1).lower() in INCOMPLETE_TRAILING_WORDS
        or last_word_match.group(1).lower() in INCOMPLETE_TRAILING_CONTEXT_WORDS
    ):
        previous_sentence = re.match(r"^(.+[.!?])\s+[^.!?]+$", text)
        if previous_sentence:
            return previous_sentence.group(1).strip()
        trimmed = re.sub(r"\s+[A-Za-zÀ-ÿ]+[.!?]?$", "", text).strip()
        if trimmed:
            return trimmed.rstrip(".!?") + "..."
        return text.rstrip(".!?") + "..."

    if text[-1] not in ".!?:;)]}":
        return text + "."
    return text


def polish_assistant_response(message: str) -> str:
    text = str(message or "").replace("\x00", "")
    if not text.strip():
        return ""

    mojibake_replacements = {
        "N\u00c3\u00a3o": "Não",
        "n\u00c3\u00a3o": "não",
        "A\u00c3\u00a7\u00c3\u00a3o": "Ação",
        "a\u00c3\u00a7\u00c3\u00a3o": "ação",
        "sess\u00c3\u00a3o": "sessão",
        "h\u00c3\u00a1": "há",
        "ser\u00c3\u00a1": "será",
        "ent\u00c3\u00a3o": "então",
        "precis\u00c3\u00a3o": "precisão",
    }
    for old, new in mojibake_replacements.items():
        text = text.replace(old, new)

    replacements = [
        ("Nao", "Não"),
        ("nao", "não"),
        ("Voce", "Você"),
        ("voce", "você"),
        ("Acao", "Ação"),
        ("acao", "ação"),
        ("acoes", "ações"),
        ("acionaveis", "acionáveis"),
        ("servico", "serviço"),
        ("catalogo", "catálogo"),
        ("chamaveis", "chamáveis"),
        ("codigo", "código"),
        ("codigos", "códigos"),
        ("Programacao", "Programação"),
        ("programacao", "programação"),
        ("Navegacao", "Navegação"),
        ("navegacao", "navegação"),
        ("mudanca", "mudança"),
        ("mudancas", "mudanças"),
        ("Nucleo", "Núcleo"),
        ("nucleo", "núcleo"),
        ("conclusao", "conclusão"),
        ("decisao", "decisão"),
        ("decisoes", "decisões"),
        ("confirmacao", "confirmação"),
        ("confirmacoes", "confirmações"),
        ("obrigatoria", "obrigatória"),
        ("obrigatorio", "obrigatório"),
        ("traducao", "tradução"),
        ("conteudo", "conteúdo"),
        ("correcao", "correção"),
        ("correcoes", "correções"),
        ("pronuncia", "pronúncia"),
        ("pronuncias", "pronúncias"),
        ("memoria", "memória"),
        ("Memoria", "Memória"),
        ("memorias", "memórias"),
        ("sessao", "sessão"),
        ("revisao", "revisão"),
        ("revisoes", "revisões"),
        ("verificacao", "verificação"),
        ("evidencia", "evidência"),
        ("evidencias", "evidências"),
        ("verificavel", "verificável"),
        ("verificaveis", "verificáveis"),
        ("confianca", "confiança"),
        ("seguranca", "segurança"),
        ("informacao", "informação"),
        ("informacoes", "informações"),
        ("configuracao", "configuração"),
        ("configuracoes", "configurações"),
        ("disponivel", "disponível"),
        ("disponiveis", "disponíveis"),
        ("testaveis", "testáveis"),
        ("visivel", "visível"),
        ("pagina", "página"),
        ("Preco", "Preço"),
        ("preco", "preço"),
        ("relatorio", "relatório"),
        ("relatorios", "relatórios"),
        ("Noticia", "Notícia"),
        ("noticia", "notícia"),
        ("noticias", "notícias"),
        ("provisoria", "provisória"),
        ("provisorio", "provisório"),
        ("diario", "diário"),
        ("questoes", "questões"),
        ("extracao", "extração"),
        ("transcricao", "transcrição"),
        ("diagnostico", "diagnóstico"),
        ("audio", "áudio"),
        ("ambigua", "ambígua"),
        ("ambiguo", "ambíguo"),
        ("execucao", "execução"),
        ("grafico", "gráfico"),
        ("graficos", "gráficos"),
        ("legivel", "legível"),
        ("legiveis", "legíveis"),
        ("rapido", "rápido"),
        ("rapidos", "rápidos"),
        ("propria", "própria"),
        ("proprio", "próprio"),
        ("inferencia", "inferência"),
        ("midia", "mídia"),
        ("util", "útil"),
        ("uteis", "úteis"),
        ("usuario", "usuário"),
        ("usuarios", "usuários"),
        ("tecnico", "técnico"),
        ("tecnicos", "técnicos"),
        ("pratica", "prática"),
        ("praticas", "práticas"),
        ("pratico", "prático"),
        ("praticos", "práticos"),
        ("historico", "histórico"),
        ("ultima", "última"),
        ("ultimas", "últimas"),
        ("parametro", "parâmetro"),
        ("parametros", "parâmetros"),
        ("sensivel", "sensível"),
        ("sensiveis", "sensíveis"),
        ("metricas", "métricas"),
        ("dominio", "domínio"),
        ("dominios", "domínios"),
        ("versao", "versão"),
        ("versoes", "versões"),
        ("fisica", "física"),
        ("critico", "crítico"),
        ("criticos", "críticos"),
        ("medico", "médico"),
        ("medicos", "médicos"),
        ("juridico", "jurídico"),
        ("juridicos", "jurídicos"),
        ("evolucao", "evolução"),
        ("apresentacao", "apresentação"),
        ("implementacao", "implementação"),
        ("implementacoes", "implementações"),
        ("proximo", "próximo"),
        ("proximos", "próximos"),
        ("apos", "após"),
        ("ate", "até"),
        ("tambem", "também"),
        ("ha", "há"),
        ("El Nino", "El Niño"),
        ("el nino", "El Niño"),
        ("tres", "três"),
        ("precos", "preços"),
        ("inflacao", "inflação"),
        ("exposicao", "exposição"),
        ("inadimplencia", "inadimplência"),
        ("renegociacoes", "renegociações"),
        ("negocios", "negócios"),
        ("credito", "crédito"),
        ("recorrencia", "recorrência"),
        ("recomendacao", "recomendação"),
        ("agronegocio", "agronegócio"),
        ("fenomeno", "fenômeno"),
        ("eletricos", "elétricos"),
        ("socios", "sócios"),
        ("Recursao", "Recursão"),
        ("recursao", "recursão"),
        ("Funcao", "Função"),
        ("funcao", "função"),
        ("funcoes", "funções"),
        ("repeticao", "repetição"),
        ("permissoes", "permissões"),
        ("consciencia", "consciência"),
        ("colecao", "coleção"),
    ]
    for old, new in replacements:
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)

    phrase_replacements = [
        (r"\bvoce quer\b", "você quer"),
        (r"\bqual palavra voce\b", "qual palavra você"),
        (r"\bcomo voce\b", "como você"),
        (r"\bo que voce\b", "o que você"),
        (r"\bquem voce\b", "quem você"),
        (r"\bvoce esta\b", "você está"),
        (r"\bvoce e\b", "você é"),
        (r"\be voce\b", "e você"),
        (r"\bMeu nome e\b", "Meu nome é"),
        (r"\bmeu nome e\b", "meu nome é"),
        (r"\bTesla pode ser a empresa de carros elétricos\b", "Tesla pode ser a empresa de carros elétricos"),
        (r"\bé um streamer brasileiro conhecido por lives de jogos, humor e conteúdo\b", "é um streamer brasileiro conhecido por lives de jogos, humor e conteúdo"),
        (r"\bRecursão em Python e quando\b", "Recursão em Python é quando"),
        (r"\bO ponto principal e ter\b", "O ponto principal é ter"),
        (r"\bmodo de tom mais quieto\b", "modo de tom mais quieto"),
        (r"\bEle nao muda\b", "Ele não muda"),
        (r"\bele nao muda\b", "ele não muda"),
        (r"\bSeu corpo está pedindo pausa\. Se não\b", "Seu corpo está pedindo pausa. Se não"),
        (r"\besta pronto\b", "está pronto"),
        (r"\besta pronta\b", "está pronta"),
        (r"\bestou aqui\b", "Estou aqui"),
        (r"\bsera encerrado\b", "será encerrado"),
        (r"\bnao ha\b", "não há"),
        (r"\bNao ha\b", "Não há"),
        (r"\bnao abri\b", "não abri"),
        (r"\bNao abri\b", "Não abri"),
        (r"\bNao entendi\b", "Não entendi"),
        (r"\bNao identifiquei\b", "Não identifiquei"),
        (r"\bNao consegui\b", "Não consegui"),
        (r"\bNao encontrei\b", "Não encontrei"),
        (r"\bNao detectei\b", "Não detectei"),
        (r"\bNao captei\b", "Não captei"),
        (r"\bConcluido\b", "Concluído"),
        (r"\bIsso e leitura\b", "Isso é leitura"),
        (r"\bponto e mapear\b", "ponto é mapear"),
        (r"\bpeso salvo e\b", "peso salvo é"),
        (r"\brisco e relevante\b", "risco é relevante"),
        (r"\bNão e recomendação\b", "Não é recomendação"),
        (r"\bnão e recomendação\b", "não é recomendação"),
    ]
    for pattern, replacement in phrase_replacements:
        text = re.sub(pattern, replacement, text)

    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"([!?]){2,}", r"\1", text)
    text = re.sub(r"\.{4,}", "...", text)
    return trim_incomplete_final_fragment(text)
