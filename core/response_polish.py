from __future__ import annotations

import re


def polish_assistant_response(message: str) -> str:
    text = str(message or "").replace("\x00", "")
    if not text.strip():
        return ""

    mojibake_replacements = {
        "NÃ£o": "Não",
        "nÃ£o": "não",
        "AÃ§Ã£o": "Ação",
        "aÃ§Ã£o": "ação",
        "sessÃ£o": "sessão",
        "hÃ¡": "há",
        "serÃ¡": "será",
        "entÃ£o": "então",
        "precisÃ£o": "precisão",
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
        ("servico", "serviço"),
        ("conclusao", "conclusão"),
        ("traducao", "tradução"),
        ("correcao", "correção"),
        ("correcoes", "correções"),
        ("pronuncia", "pronúncia"),
        ("pronuncias", "pronúncias"),
        ("memoria", "memória"),
        ("sessao", "sessão"),
        ("revisao", "revisão"),
        ("revisoes", "revisões"),
        ("verificacao", "verificação"),
        ("confianca", "confiança"),
        ("informacao", "informação"),
        ("informacoes", "informações"),
        ("configuracao", "configuração"),
        ("configuracoes", "configurações"),
        ("disponivel", "disponível"),
        ("disponiveis", "disponíveis"),
        ("visivel", "visível"),
        ("pagina", "página"),
        ("midia", "mídia"),
        ("util", "útil"),
        ("evolucao", "evolução"),
        ("apresentacao", "apresentação"),
        ("proximo", "próximo"),
        ("proximos", "próximos"),
        ("apos", "após"),
        ("esta", "está"),
        ("ate", "até"),
        ("tambem", "também"),
        ("ha", "há"),
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
    ]
    for pattern, replacement in phrase_replacements:
        text = re.sub(pattern, replacement, text)

    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"([!?]){2,}", r"\1", text)
    text = re.sub(r"\.{4,}", "...", text)
    return text.strip()
