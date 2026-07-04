from __future__ import annotations

import re

from core.router_utils import normalize_text
from llm.action_selector import select_read_action
from llm.chat import chat_response
from memory.current_topic import load_current_topic, update_current_topic_from_conversation

FACTUAL_QUESTION_PREFIXES = (
    "o que e ",
    "oq e ",
    "oque e ",
    "quem e ",
    "quem foi ",
    "qual e ",
    "qual ",
    "quais sao ",
    "quais ",
    "onde ",
    "quando ",
    "por que ",
    "porque ",
    "como funciona ",
    "como ",
)

GENERAL_EXPLANATION_PREFIXES = (
    "me explica ",
    "me explique ",
    "explica ",
    "explique ",
    "detalha ",
    "detalhe ",
)

REPEAT_PATTERNS = {
    "de novo",
    "denovo",
    "mais uma",
    "outra vez",
    "repete",
    "repita",
}

ENGLISH_PRACTICE_PHRASES = {
    "how are you",
    "are you here",
    "are you there",
    "do you have",
    "hello",
    "hi",
    "good morning",
    "good afternoon",
    "good evening",
    "good night",
    "thank you",
    "thanks",
    "what is your name",
    "can you help me",
    "i want to learn english",
}

HELP_REQUEST_PATTERNS = (
    "pode me ajudar",
    "consegue me ajudar",
    "voce pode me ajudar",
    "vc pode me ajudar",
    "me ajuda",
    "me ajude",
    "me ensina",
    "ensina",
    "quero aprender",
    "quero estudar",
    "preciso aprender",
    "preciso estudar",
)

GIFT_TERMS = {
    "presente",
    "presentes",
    "dar de presente",
    "namorada",
    "namorado",
    "parente",
    "parentes",
    "mae",
    "mãe",
    "pai",
    "irma",
    "irmã",
    "irmao",
    "irmão",
}

WORKOUT_TERMS = {
    "treino",
    "treinar",
    "exercicio",
    "exercício",
    "exercicios",
    "exercícios",
    "academia",
    "calistenia",
    "musculacao",
    "musculação",
    "cardio",
}

FOOD_TERMS = {
    "dieta",
    "alimentacao",
    "alimentação",
    "comer melhor",
    "emagrecer",
    "ganhar massa",
    "proteina",
    "proteína",
    "caloria",
    "calorias",
}

IDEA_TERMS = {
    "ideia",
    "ideias",
    "sugestao",
    "sugestão",
    "dica",
    "dicas",
    "recomenda",
    "recomendacao",
    "recomendação",
}

PRACTICAL_HELP_TERMS = {
    "receita",
    "como fazer",
    "como preparo",
    "como preparar",
    "passo a passo",
    "tutorial",
    "roteiro",
}

FOLLOWUP_PLAN_TERMS = {
    "faz um plano",
    "fazer um plano",
    "monta um plano",
    "monte um plano",
    "cria um plano",
    "crie um plano",
    "plano de estudo",
    "plano pra estudar",
    "plano para estudar",
}

FOLLOWUP_EXAMPLE_TERMS = {
    "me da exemplos",
    "me dá exemplos",
    "me de exemplos",
    "me dê exemplos",
    "da exemplos",
    "dá exemplos",
    "de exemplos",
    "dê exemplos",
    "exemplos",
}

FOLLOWUP_QUESTION_TERMS = {
    "cria perguntas",
    "crie perguntas",
    "gera perguntas",
    "gere perguntas",
    "faz perguntas",
    "fazer perguntas",
    "questoes",
    "questões",
}

FOLLOWUP_EXPLAIN_TERMS = {
    "explica melhor",
    "explique melhor",
    "me explica melhor",
    "me explique melhor",
    "fala mais",
    "me fala mais",
    "detalha isso",
    "detalhe isso",
    "continua",
    "continue",
}


def _current_conversation_topic() -> str:
    try:
        topic = load_current_topic() or {}
    except Exception:
        return ""
    for key in ("topic", "summary", "last_user_question", "page_title"):
        value = str(topic.get(key) or "").strip()
        if value:
            return re.sub(r"\s+", " ", value)[:90]
    return ""


def remember_useful_conversation_topic(user_input: str, response: str) -> None:
    if not str(response or "").strip():
        return
    topic = _learning_topic(user_input)
    if topic in {"esse tema", "isso", "essa", "esse"}:
        topic = _question_topic(user_input)
    try:
        update_current_topic_from_conversation(
            user_input=user_input,
            assistant_response=response,
            topic=topic,
            source="conversation",
            related_summary=response[:260],
            keywords=[word for word in normalize_text(f"{user_input} {response}").split() if len(word) >= 4][:8],
        )
    except Exception:
        pass


def _respond_with_memory(user_input: str, response: str) -> dict:
    remember_useful_conversation_topic(user_input, response)
    return {"intent": "respond", "target": None, "response": response}


def _contextual_followup_response(user_input: str) -> str | None:
    text = normalize_text(user_input)
    topic = _current_conversation_topic()
    if not text or not topic:
        return None

    if any(term in text for term in FOLLOWUP_EXAMPLE_TERMS):
        return (
            f"Exemplos para {topic}: pegue um caso simples, um caso comum e um caso que costuma confundir. "
            "Depois compare o que muda entre eles. Se for estudo, eu posso transformar isso em exercícios com gabarito."
        )
    if any(term in text for term in FOLLOWUP_PLAN_TERMS):
        return (
            f"Plano curto para {topic}: primeiro entenda os conceitos básicos, depois faça exemplos guiados, "
            "em seguida responda perguntas sem olhar e revise só os erros. Trinta minutos bem focados já rendem mais que duas horas meio perdidas."
        )
    if any(term in text for term in FOLLOWUP_QUESTION_TERMS):
        return (
            f"Perguntas para treinar {topic}: 1. Qual é a ideia central? 2. Que exemplo simples mostra isso? "
            "3. Qual erro comum aparece nesse tema? 4. Como você explicaria para alguém em um minuto?"
        )
    if any(term in text for term in FOLLOWUP_EXPLAIN_TERMS):
        return (
            f"Indo um pouco mais fundo em {topic}: separe o tema em definição, motivo de existir, exemplo prático e erro comum. "
            "Essa ordem costuma revelar onde a dúvida está escondida."
        )
    return None


def _learning_topic(user_input: str) -> str:
    raw = re.sub(r"\s+", " ", str(user_input or "")).strip(" .?!")
    text = normalize_text(raw)
    cleaned = text
    for pattern in (
        r"^(?:axel\s+)?(?:pode|consegue|voce pode|vc pode)\s+me\s+ajudar\s+a\s+",
        r"^(?:axel\s+)?(?:me\s+ajuda|me\s+ajude)\s+a\s+",
        r"^(?:axel\s+)?(?:quero|preciso)\s+(?:aprender|estudar|praticar|treinar)\s+",
        r"^(?:axel\s+)?(?:me\s+ensina|ensina)\s+(?:o\s+basico\s+de\s+|o\s+básico\s+de\s+|sobre\s+)?",
    ):
        cleaned = re.sub(pattern, "", cleaned).strip(" .?!")
    return cleaned[:80].strip(" .?!") or "esse tema"


def _question_topic(user_input: str) -> str:
    text = re.sub(r"\s+", " ", str(user_input or "")).strip(" .?!")
    normalized = normalize_text(text)
    for prefix in (*GENERAL_EXPLANATION_PREFIXES, *FACTUAL_QUESTION_PREFIXES):
        if normalized.startswith(prefix):
            return text[len(prefix) :].strip(" .?!") or text
    return text


def _question_fallback_response(user_input: str) -> str:
    topic = _question_topic(user_input)
    topic_hint = f" sobre {topic}" if topic and len(topic) <= 80 else ""
    return (
        f"Não vou inventar{topic_hint} sem uma resposta confiável do chat local. "
        "Posso pesquisar para confirmar, ou você pode mandar mais contexto e eu tento pelo caminho curto."
    )


def _is_english_learning_request(text: str) -> bool:
    return "ingles" in text and any(
        term in text for term in {"aprender", "estudar", "treinar", "praticar", "ajudar", "ajude", "ajuda", "conversar"}
    )


def _looks_like_english_practice(user_input: str, text: str) -> bool:
    raw = str(user_input or "").strip().lower()
    raw_without_name = re.sub(r"^\s*axel[\s,.:;-]+", "", raw).strip()
    if any(phrase in raw_without_name for phrase in ENGLISH_PRACTICE_PHRASES):
        return True
    if "ingles" in text or "english" in raw_without_name:
        return True
    english_words = {
        "i",
        "you",
        "am",
        "are",
        "is",
        "do",
        "have",
        "want",
        "learn",
        "study",
        "english",
        "hello",
        "hi",
        "how",
        "what",
        "where",
        "thanks",
        "thank",
    }
    words = set(re.findall(r"[a-z']+", raw_without_name))
    return len(words & english_words) >= 2


def _extract_meaning_phrase(user_input: str, text: str) -> str | None:
    meaning_terms = {"oq significa", "o que significa", "oque significa", "qual o significado", "significa o que"}
    if not any(term in text for term in meaning_terms):
        return None

    raw = str(user_input or "").strip()
    quoted = re.search(r"[\"“”](.+?)[\"“”]", raw)
    if not quoted:
        quoted = re.search(r"(?<![A-Za-z])[‘'](.+?)[’'](?![A-Za-z])", raw)
    if quoted:
        return quoted.group(1).strip()

    match = re.match(
        r"^\s*(?P<phrase>.+?)\s+(?:oq|o\s+que|oque|qual\s+o)\s+significa\??\s*$",
        raw,
        flags=re.I,
    )
    if match:
        return match.group("phrase").strip(" .,:;-\"'“”‘’")

    match = re.match(
        r"^\s*(?:oq|o\s+que|oque)\s+significa\s+(?P<phrase>.+?)\??\s*$",
        raw,
        flags=re.I,
    )
    if match:
        return match.group("phrase").strip(" .,:;-\"'“”‘’")

    match = re.match(
        r"^\s*(?P<phrase>.+?)\s+significa\s+o\s+que\??\s*$",
        raw,
        flags=re.I,
    )
    if match:
        return match.group("phrase").strip(" .,:;-\"'“”‘’")

    return None


def _english_meaning_response(phrase: str) -> str:
    normalized = re.sub(r"\s+", " ", str(phrase or "").strip().lower())
    translations = {
        "i'm doing well": "'I'm doing well' significa 'Estou bem' ou 'Estou indo bem'. É uma resposta natural para 'How are you?'.",
        "im doing well": "'I'm doing well' significa 'Estou bem' ou 'Estou indo bem'. É uma resposta natural para 'How are you?'.",
        "i am doing well": "'I am doing well' significa 'Estou bem' ou 'Estou indo bem'. A forma com contração, 'I'm', soa mais comum na conversa.",
        "how are you": "'How are you?' significa 'Como você está?'. É uma saudação comum em inglês.",
        "are you here": "'Are you here?' significa 'Você está aqui?'. Para perguntar se alguém está disponível online, 'Are you there?' costuma soar mais natural.",
        "are you there": "'Are you there?' significa 'Você está aí?'. É bem natural para confirmar presença em chamada ou chat.",
    }
    if normalized in translations:
        return translations[normalized]

    if re.search(r"[a-zA-Z]", phrase):
        return (
            f"'{phrase}' parece uma frase em inglês. Posso te ajudar a traduzir e entender pelo contexto; "
            "se quiser, mande a frase completa em uma linha e eu explico palavra por palavra."
        )

    return "Posso explicar o significado, mas preciso que você mande a palavra ou frase que quer traduzir."


def _english_practice_response(user_input: str) -> str:
    raw = str(user_input or "").strip()
    normalized = re.sub(r"^\s*axel[\s,.:;-]+", "", raw, flags=re.IGNORECASE).strip().lower()

    if "do you have" in normalized:
        return (
            "Good mixed sentence. Melhor seria: 'Do you have Telegram?' ou 'Do you have a Telegram bot?'. "
            "Sim, eu tenho integração com Telegram quando ela está configurada."
        )

    if "how are you" in normalized:
        return (
            "I'm doing well. Correção leve: a frase está certa; só fica mais natural com vírgula se chamar pelo nome: "
            "'Axel, how are you?' Agora sua vez: 'I'm fine' ou 'I'm a little tired'."
        )

    if "are you here" in normalized or "are you there" in normalized:
        return (
            "Yes, I'm here. Sua frase funciona. Para chamar alguém à distância, 'Are you there?' costuma soar mais natural. "
            "Pode continuar misturando português e inglês que eu vou corrigindo sem interromper demais."
        )

    if normalized in {"hello", "hi"} or normalized.startswith(("hello ", "hi ")):
        return "Hello. Boa abertura. Se quiser praticar, responda em inglês: 'How was your day?'"

    if "thank you" in normalized or "thanks" in normalized:
        return "You're welcome. Pequeno ajuste: 'thanks' é mais casual; 'thank you' é um pouco mais formal."

    return (
        "Entendi como prática de inglês. Posso conversar misturando os dois idiomas, corrigir suas frases de leve "
        "e ensinar vocabulário pelo contexto. Mande uma frase simples em inglês ou português e eu transformo isso em treino."
    )


def _looks_like_weak_open_response(response: str) -> bool:
    text = normalize_text(response)
    if not text:
        return True
    weak_fragments = {
        "nao consegui confirmar",
        "não consegui confirmar",
        "nao vou inventar",
        "não vou inventar",
        "sem uma resposta confiavel",
        "sem uma resposta confiável",
        "posso pesquisar para confirmar",
        "mande mais contexto",
        "mandar mais contexto",
        "nao entendi",
        "não entendi",
    }
    return any(fragment in text for fragment in weak_fragments)


def _is_help_or_learning_request(text: str) -> bool:
    if any(pattern in text for pattern in HELP_REQUEST_PATTERNS):
        return True
    return bool(
        re.search(
            r"\b(?:aprender|estudar|treinar|praticar)\b.*\b(?:comigo|me|hoje|agora|isso|esse|essa)\b",
            text,
        )
    )


def _contains_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _gift_response(text: str) -> str:
    if "mae" in text or "mãe" in text:
        return (
            "Para sua mãe, eu iria por algo útil com sinal de cuidado: uma experiência simples, um item de conforto bom, "
            "um kit com algo que ela já usa ou algo ligado a uma conversa recente. "
            "O ponto é parecer escolhido, não comprado no modo desespero cinco minutos antes."
        )
    if "pai" in text:
        return (
            "Para seu pai, eu começaria por uso real: algo para rotina, ferramenta, carteira, camiseta boa, café, perfume discreto "
            "ou uma experiência curta. Se ele for difícil de presentear, escolha algo que melhore um hábito que ele já tem."
        )
    if "namorada" in text or "namorado" in text:
        return (
            "Para namorada ou namorado, eu evitaria presente genérico. Boas linhas são: algo ligado a uma conversa recente, "
            "uma experiência pequena, um item de cuidado bem escolhido ou um presente simples com carta curta. "
            "Romântico sem parecer compra automática de shopping, que é onde presentes vão perder personalidade."
        )
    return (
        "Sim. Para presente, eu começaria por três filtros: utilidade real, lembrança pessoal e risco baixo de errar tamanho ou gosto. "
        "Boas opções costumam ser algo ligado a uma conversa recente, um kit simples bem escolhido, uma experiência pequena ou algo que resolva uma dor do dia a dia. "
        "Se você me disser idade, relação e orçamento, eu afunilo sem jogar uma vitrine inteira na sua cara."
    )


def _workout_response(text: str) -> str:
    if any(term in text for term in {"casa", "sem equipamento", "sem equipamentos", "calistenia"}):
        return (
            "Para treino em casa sem equipamento, eu faria 3 dias por semana com flexão, agachamento, remada improvisada se houver apoio seguro, prancha e avanço. "
            "Comece com poucas séries boas e aumente repetição ou dificuldade aos poucos. Dor articular não é medalha, é aviso do sistema."
        )
    if any(term in text for term in {"emagrecer", "perder peso", "secar"}):
        return (
            "Para emagrecer treinando, o melhor começo é combinar caminhada ou cardio leve com força 3 vezes por semana. "
            "O treino ajuda, mas quem manda no resultado é consistência e alimentação minimamente organizada."
        )
    return (
        "Posso ajudar com treino de forma prática. Sem saber seu nível, eu começaria simples: 3 dias por semana, movimentos básicos, progressão pequena e descanso decente. "
        "Um exemplo seguro é alternar empurrar, puxar, pernas e core, sem tentar virar atleta em uma terça-feira aleatória. Se você disser objetivo e equipamentos, eu monto algo mais direto."
    )


def _food_response(text: str) -> str:
    if any(term in text for term in {"sem dieta", "sem fazer dieta", "nao faco dieta", "não faço dieta"}):
        return (
            "Dá para melhorar alimentação sem chamar isso de dieta. Comece por três ajustes: proteína em alguma refeição principal, "
            "água por perto e uma troca óbvia por dia, tipo menos refrigerante ou ultraprocessado. "
            "Pequeno e repetível ganha de plano perfeito que dura dois almoços."
        )
    if any(term in text for term in {"ganhar massa", "massa muscular", "hipertrofia"}):
        return (
            "Para ganhar massa, o básico é treino de força consistente, proteína suficiente e comer um pouco mais do que gasta. "
            "Sem exames e rotina completa eu não cravo números, mas posso montar um esqueleto simples de refeições."
        )
    return (
        "Posso ajudar com alimentação sem transformar isso em dieta militar. O básico útil é: proteína em quase toda refeição, água, menos ultraprocessado, frutas ou legumes no dia e porções que você consiga repetir na rotina. "
        "Se houver condição médica, o caminho certo é nutricionista; para organização comum, eu consigo montar ideias simples."
    )


def useful_conversation_response(user_input: str) -> str | None:
    text = normalize_text(user_input)
    if not text or len(text) <= 4:
        return None

    followup = _contextual_followup_response(user_input)
    if followup:
        return followup

    asks_for_idea = _contains_any(text, IDEA_TERMS) or _is_help_or_learning_request(text)

    if _is_help_or_learning_request(text) and any(
        term in text
        for term in {
            "estudar",
            "estudo",
            "aprender",
            "praticar",
            "treinar",
            "ensina",
            "prova",
            "aula",
            "materia",
            "matéria",
        }
    ):
        topic = _learning_topic(user_input)
        return (
            f"Sim. Para estudar {topic}, eu começaria por um ciclo curto: resumo dos conceitos, exemplos simples, "
            "cinco perguntas de fixação e uma revisão dos erros. "
            "Se você mandar um arquivo ou disser o nível da prova, eu adapto o treino e corrijo suas respostas."
        )

    if _contains_any(text, GIFT_TERMS) and asks_for_idea:
        return _gift_response(text)

    if _contains_any(text, WORKOUT_TERMS):
        return _workout_response(text)

    if _contains_any(text, FOOD_TERMS):
        return _food_response(text)

    if asks_for_idea:
        return (
            "Consigo ajudar. Vou tratar isso como conversa útil: posso te dar opções, comparar caminhos e adaptar ao seu contexto. "
            "Me diga o objetivo, restrições e quanto esforço você quer gastar; se faltar contexto, eu assumo um ponto de partida razoável e ajustamos."
        )

    return None


def practical_question_response(user_input: str) -> str | None:
    text = normalize_text(user_input)
    if not text or len(text) <= 4:
        return None

    if "receita" in text and "bolo de cenoura" in text:
        return (
            "Dá para fazer um bolo de cenoura simples assim: bata 2 cenouras médias, 3 ovos, meia xícara de óleo e 1 xícara e meia de açúcar. "
            "Misture com 2 xícaras de farinha e 1 colher de fermento, asse em forno médio por cerca de 35 a 45 minutos. "
            "Para cobertura, chocolate em pó, leite, açúcar e um pouco de manteiga resolvem sem convocar engenharia pesada."
        )

    if "receita" in text:
        topic = _question_topic(user_input)
        return (
            f"Posso te passar um caminho prático para {topic}. Sem detalhes do que você tem em casa, eu começaria por uma versão simples: "
            "ingredientes básicos, preparo curto e ajuste no final pelo gosto. Se você disser os ingredientes disponíveis, eu monto a receita certinha."
        )

    if any(term in text for term in PRACTICAL_HELP_TERMS):
        topic = _question_topic(user_input)
        return (
            f"Posso te ajudar com {topic}. Vou assumir um ponto de partida simples: separar o objetivo, listar o material necessário, "
            "fazer em passos curtos e revisar o resultado no fim. Se for algo com risco físico, financeiro ou médico, é melhor confirmar com uma fonte especializada."
        )

    return None


def _has_explicit_special_context(text: str) -> bool:
    if any(
        phrase in text
        for phrase in {
            "na tela",
            "a tela",
            "dessa tela",
            "nesta tela",
            "tela atual",
            "visivel",
            "visiveis",
            "selecionado",
            "selecao",
            "pagina atual",
            "nessa pagina",
            "nesta pagina",
            "site atual",
        }
    ):
        return True

    if any(
        phrase in text
        for phrase in {
            "arquivo atual",
            "nesse arquivo",
            "neste arquivo",
            "no arquivo",
            "documento atual",
            "nesse documento",
            "pdf anexado",
            "arquivo anexado",
            "slide atual",
        }
    ):
        return True

    if any(
        phrase in text
        for phrase in {
            "minha carteira",
            "meus investimentos",
            "meu investimento",
            "investimentos",
            "investimento",
            "da carteira",
            "na carteira",
            "carteira desde ontem",
            "dividendos",
            "cotacao",
            "preco teto",
            "watchlist",
            "ativos merecem atencao",
            "merecem atencao",
            "fato relevante",
            "mais barato",
            "menor preco",
            "compare os precos",
            "comparar precos",
            "fii",
            "fiis",
            "fiagro",
            "agronegocio",
            "el nino",
            "la nina",
            "vgia",
            "bbas",
            "bbse",
            "petr",
            "isae",
            "bbdc",
            "xpml",
            "kncr",
            "cpts",
            "ggrc",
            "btci",
            "trbl",
            "pmll",
        }
    ):
        return True

    if "meu nome" in text or "qual meu nome" in text:
        return True

    if re.search(r"\b[a-z]{4}\d{1,2}\b", text):
        return True

    return False


def detect_general_question_early(user_input: str):
    text = normalize_text(user_input)
    if not text or len(text) <= 4:
        return None
    is_general_question = (
        text.startswith(FACTUAL_QUESTION_PREFIXES)
        or text.startswith(GENERAL_EXPLANATION_PREFIXES)
        or "?" in str(user_input or "")
    )
    if not is_general_question or _has_explicit_special_context(text):
        return None

    builtin = detect_builtin_general_answer(user_input)
    if builtin:
        return builtin

    useful = useful_conversation_response(user_input)
    practical = practical_question_response(user_input)
    fallback = useful or practical

    response = chat_response(user_input)
    if response and not (fallback and _looks_like_weak_open_response(response)):
        return {"intent": "respond", "target": None, "response": response}

    if fallback:
        return _respond_with_memory(user_input, fallback)

    return detect_question_fallback(user_input)


def detect_builtin_general_answer(user_input: str):
    text = normalize_text(user_input)
    if not text or len(text) <= 4:
        return None

    meaning_phrase = _extract_meaning_phrase(user_input, text)
    if meaning_phrase:
        return {
            "intent": "respond",
            "target": None,
            "response": _english_meaning_response(meaning_phrase),
        }

    if _is_english_learning_request(text):
        return {
            "intent": "respond",
            "target": None,
            "response": (
                "Sim. Posso te ajudar com inglês de forma prática: conversação curta, vocabulário do seu dia a dia, "
                "correção das suas frases e explicações rápidas de gramática. Podemos misturar português e inglês: "
                "você escreve do jeito que souber, eu respondo, ajusto a frase e puxo a próxima pergunta. Para começar, "
                "mande uma frase simples sobre o seu dia."
            ),
        }

    if _looks_like_english_practice(user_input, text):
        return {
            "intent": "respond",
            "target": None,
            "response": _english_practice_response(user_input),
        }

    if _is_help_or_learning_request(text):
        useful = useful_conversation_response(user_input)
        response = useful or (
            "Posso ajudar. Me diga o objetivo e o material que você tem, se houver. Eu posso explicar, resumir, "
            "montar um plano curto, criar exercícios ou ir te guiando por perguntas. Se quiser começar agora, "
            "me diga o tema em uma frase."
        )
        return _respond_with_memory(user_input, response)

    if "alanzoca" in text:
        return {
            "intent": "respond",
            "target": None,
            "response": "Alanzoca, ou Alan Ferreira, é um streamer brasileiro conhecido por lives de jogos, humor e conteúdo na Twitch/YouTube.",
        }

    if "tesla" in text:
        return {
            "intent": "respond",
            "target": None,
            "response": "Tesla pode ser a empresa de carros elétricos e energia fundada por Elon Musk e outros sócios, ou Nikola Tesla, o inventor associado à corrente alternada. Se quiser, eu diferencio os dois.",
        }

    if "recursao" in text or "recursivo" in text:
        return {
            "intent": "respond",
            "target": None,
            "response": "Recursão em Python é quando uma função chama ela mesma para resolver um problema em partes menores. O ponto principal é ter um caso base para parar; sem isso, a função entra em repetição infinita até estourar o limite de recursão.",
        }

    if "pergunta" in text and "aleatoria" in text and any(word in text for word in {"responde", "responder"}):
        return {
            "intent": "respond",
            "target": None,
            "response": "Sim. Se a pergunta for aleatória, eu tento responder pelo chat geral; se ela parecer sobre arquivo, tela, agenda ou comando, eu tento encaminhar para a função certa.",
        }

    if "estagiario noturno" in text:
        return {
            "intent": "respond",
            "target": None,
            "response": (
                "O estagiário noturno é só um modo de tom mais quieto para a noite: respostas mais curtas, "
                "menos barulho e lembrete amigável para salvar o progresso e dormir quando ficar tarde. "
                "Ele não muda permissões nem executa tarefas sozinho."
            ),
        }

    if any(term in text for term in {"rinite", "espirrando", "espirro", "nariz escorrendo", "nariz entupido", "alergia atacada"}):
        return {
            "intent": "respond",
            "target": None,
            "response": (
                "Parece desconfortável. Não consigo diagnosticar, mas se for algo tipo rinite ou alergia, "
                "pode ajudar se afastar de poeira ou cheiro forte, beber água e lavar o nariz com soro. "
                "Se tiver falta de ar, febre forte, dor no peito ou piora importante, e melhor procurar atendimento."
            ),
        }

    if any(term in text for term in {"dor de barriga", "barriga doendo", "dor no estomago", "enjoo", "enjoado", "nausea"}):
        return {
            "intent": "respond",
            "target": None,
            "response": (
                "Poxa, dor de barriga derruba qualquer foco. Não consigo diagnosticar, mas pode ser boa ideia "
                "beber água, comer leve e descansar um pouco. Se a dor for forte, persistente, vier com febre, "
                "vômitos repetidos, sangue ou piora rápida, procure atendimento."
            ),
        }

    if (
        re.search(r"\b(?:estou|to|tô|tou|estou com|to com|tô com)\s+(?:muito\s+)?sono\b", text)
        or "vontade de dormir" in text
        or "quero dormir" in text
        or "preciso dormir" in text
    ):
        return {
            "intent": "respond",
            "target": None,
            "response": (
                "Seu corpo está pedindo pausa. Se não for algo urgente, vale salvar o que estiver aberto, "
                "reduzir a luz da tela e ir dormir. Posso te lembrar de encerrar quando ficar tarde usando o PC."
            ),
        }

    return None


def detect_short_unclear_text(user_input: str):
    text = normalize_text(user_input)

    if text in REPEAT_PATTERNS:
        return {"intent": "repeat_last", "target": None}

    if text in {"faz aquilo", "faz isso", "faz aquele negocio", "faz esse negocio", "abre aquilo", "resolve isso"}:
        return {
            "intent": "respond",
            "target": None,
            "response": "Esse comando ficou vago. Me diga o alvo ou a ação, por exemplo: abrir Chrome, resumir arquivo ou analisar tela.",
        }

    if len(text) <= 4:
        return {"intent": "respond", "target": None, "response": "Pode repetir?"}
    return None


def detect_light_conversation(user_input: str):
    text = normalize_text(user_input)
    if not text:
        return None

    if any(word in text for word in {"conversavel", "conversar", "bater papo", "inteligente"}):
        return {
            "intent": "respond",
            "target": None,
            "response": "Da para eu ficar mais conversavel sim. Por enquanto eu respondo melhor frases curtas, mas posso aprender respostas e contexto aos poucos.",
        }

    question_prefixes = ("por que ", "porque ", "como ", "qual ", "quando ", "onde ")
    if any(text.startswith(prefix) for prefix in question_prefixes):
        return {
            "intent": "respond",
            "target": None,
            "response": "Essa parte de conversa aberta ainda é limitada. Se você quiser, posso responder perguntas simples e ir aprendendo respostas mais naturais.",
        }

    return None


def detect_llm_action_command(user_input: str):
    text = normalize_text(user_input)
    if text.startswith(FACTUAL_QUESTION_PREFIXES) or "?" in str(user_input or ""):
        return None
    if text.startswith(GENERAL_EXPLANATION_PREFIXES):
        return None
    if useful_conversation_response(user_input):
        return None

    selected = select_read_action(user_input)
    if not selected:
        return None
    return {
        "intent": "action_tool_execute",
        "target": {
            "name": selected["name"],
            "arguments": selected.get("arguments") or {},
        },
    }


def detect_ollama_chat(user_input: str):
    text = normalize_text(user_input)
    if not text or len(text) <= 4:
        return None

    if text.startswith(FACTUAL_QUESTION_PREFIXES):
        response = chat_response(user_input)
        if response:
            return {"intent": "respond", "target": None, "response": response}

    response = chat_response(user_input)
    if response:
        return {"intent": "respond", "target": None, "response": response}

    return None


def detect_useful_conversation(user_input: str):
    useful = useful_conversation_response(user_input)
    if useful:
        return _respond_with_memory(user_input, useful)
    return None


def detect_question_fallback(user_input: str):
    text = normalize_text(user_input)
    if not text or len(text) <= 4:
        return None
    if text.startswith(GENERAL_EXPLANATION_PREFIXES):
        return {
            "intent": "respond",
            "target": None,
            "response": _question_fallback_response(user_input),
        }
    if text.startswith(FACTUAL_QUESTION_PREFIXES) or "?" in str(user_input or ""):
        return {
            "intent": "respond",
            "target": None,
            "response": _question_fallback_response(user_input),
        }
    return None


CONVERSATION_DETECTORS = (
    detect_short_unclear_text,
    detect_builtin_general_answer,
    detect_llm_action_command,
    detect_ollama_chat,
    detect_useful_conversation,
    detect_question_fallback,
    detect_light_conversation,
)

GENERAL_QUESTION_DETECTORS = (
    detect_general_question_early,
)
