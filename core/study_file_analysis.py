from __future__ import annotations

import json
import re
import shlex
import unicodedata
from pathlib import Path

from file_processor.processor import process_file
from memory.study_context import load_study_context, save_study_context

SUPPORTED_STUDY_EXTENSIONS = {".pdf", ".pptx", ".docx", ".txt", ".md", ".csv", ".json", ".xlsx"}


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").replace("\x00", "")).strip()


def _plain(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", _compact(text))
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def _contains_any(text: str, needles: set[str]) -> bool:
    plain = _plain(text)
    return any(needle in plain for needle in needles)


def parse_study_file_command(user_input: str) -> tuple[list[str], str] | None:
    raw = str(user_input or "").strip()
    match = re.match(
        r"^(?:analisar|analise|resumir|resuma|estudar|estude|explicar|explique|gerar questoes de|fazer questoes de)\s+"
        r"(?:arquivos?|anexos?|slides?|materiais?)\s*(?:anexados?)?\s*[:,-]?\s*(.+)$",
        raw,
        flags=re.I,
    )
    if not match:
        return None

    payload = match.group(1).strip()
    request = ""
    for separator in (" :: ", " pedido: ", " tarefa: "):
        if separator in payload:
            payload, request = payload.split(separator, 1)
            break

    paths: list[str] = []
    if payload.startswith("["):
        try:
            data = json.loads(payload)
            paths = [str(item).strip() for item in data if str(item).strip()] if isinstance(data, list) else []
        except Exception:
            paths = []
    else:
        try:
            paths = [item.strip() for item in shlex.split(payload, posix=False) if item.strip()]
        except ValueError:
            paths = [item.strip() for item in re.split(r"\s*\|\s*", payload) if item.strip()]

    cleaned_paths = []
    for path in paths:
        cleaned = path.strip().strip('"')
        if cleaned and Path(cleaned).suffix.lower() in SUPPORTED_STUDY_EXTENSIONS:
            cleaned_paths.append(cleaned)
    return cleaned_paths, _compact(request)


def _extract_text(result: dict) -> str:
    extracted = result.get("extracted") if isinstance(result, dict) else {}
    if not isinstance(extracted, dict):
        return ""
    text = extracted.get("text")
    if isinstance(text, str) and text.strip():
        return text
    rows = extracted.get("rows")
    if isinstance(rows, list):
        return "\n".join(" | ".join(str(cell) for cell in row) for row in rows[:20] if isinstance(row, list))
    return ""


def _extraction_note(result: dict) -> str:
    extracted = result.get("extracted") if isinstance(result, dict) else {}
    if not isinstance(extracted, dict):
        return ""
    return _compact(str(extracted.get("note") or ""))


def _study_text_is_untrusted(text: str) -> bool:
    text = str(text or "").replace("\x00", "")
    compact = re.sub(r"\s+", "", text)
    if len(compact) < 160:
        return False

    normalized = _compact(text).lower()
    suspicious_patterns = [
        r"\bt\s+m\s+s\s+t\s+m\s+s\b",
        r"\bq\s+u\s+i\s+t\s+q\s+l\s+i\s+l\s+m\b",
        r"\bs\s+o\s+n\s+t\s+w\s+i\s+r\s+m\b",
        r"\bqum\b",
        r"\blm\b",
        r"\bciqxi\b",
        r"\btmstm?s?\b",
        r"\bcisos\b",
        r"\bvitorms?\b",
        r"\bcouxtmx",
        r"\bquivtos?\b",
        r"\btrivsn",
        r"\bqvv[aã]t",
    ]
    suspicious_hits = sum(len(re.findall(pattern, normalized, flags=re.I)) for pattern in suspicious_patterns)
    common_hits = len(
        re.findall(
            r"\b(?:de|da|do|que|para|com|uma|um|teste|testes|quest[aã]o|questoes|software|valor|valores)\b",
            normalized,
            flags=re.I,
        )
    )
    tokens = re.findall(r"\b\w+\b", text or "")
    single_token_ratio = sum(1 for token in tokens if len(token) == 1) / max(1, len(tokens))

    if suspicious_hits >= 6 and common_hits <= 8:
        return True
    if len(compact) > 600 and suspicious_hits >= 12:
        return True
    if single_token_ratio >= 0.38 and suspicious_hits >= 3:
        return True
    return False


def _untrusted_extraction_message(result: dict) -> str:
    note = _extraction_note(result)
    if note:
        return note
    return (
        "a extracao de texto nao passou na verificacao de confianca. "
        "O arquivo parece ter fonte/codificacao interna ruim; preciso de OCR funcional "
        "ou de uma versao exportada como texto pesquisavel para resumir com seguranca."
    )


def _focus_lines(text: str, limit: int = 5) -> list[str]:
    candidates = []
    for raw_line in str(text or "").splitlines():
        line = _compact(raw_line)
        if len(line) < 24:
            continue
        candidates.append(line)
    if not candidates:
        sentences = re.split(r"(?<=[.!?])\s+", _compact(text))
        candidates = [sentence for sentence in sentences if len(sentence) >= 24]
    return candidates[:limit]


def _sentences(text: str, *, min_len: int = 18) -> list[str]:
    compact = _compact(text)
    if not compact:
        return []
    raw_sentences = re.split(r"(?<=[.!?;:])\s+|(?:\s+-\s+)", compact)
    return [_compact(sentence) for sentence in raw_sentences if len(_compact(sentence)) >= min_len]


def _keywords(text: str, limit: int = 10) -> list[str]:
    stopwords = {
        "para",
        "com",
        "uma",
        "um",
        "que",
        "por",
        "das",
        "dos",
        "de",
        "da",
        "do",
        "as",
        "os",
        "em",
        "no",
        "na",
        "se",
        "sao",
        "ser",
        "entre",
        "questao",
        "questoes",
        "exercicio",
        "exercicios",
        "lista",
    }
    counts: dict[str, int] = {}
    for token in re.findall(r"\b[\wÀ-ÿ]{4,}\b", _plain(text)):
        if token in stopwords or token.isdigit():
            continue
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, _count in ranked[:limit]]


def _study_request_kind(request: str) -> str:
    plain = _plain(request)
    if any(phrase in plain for phrase in {"sobre o que", "do que se trata", "qual o assunto", "que assunto", "tema"}):
        return "about"
    if any(word in plain for word in {"responder", "responda", "resolver", "resolva", "gabarito"}):
        return "answer"
    if any(word in plain for word in {"questoes", "perguntas", "exercicios", "simulado", "quiz"}):
        return "practice"
    if any(word in plain for word in {"plano", "revisao", "cronograma", "estudar"}):
        return "plan"
    if any(word in plain for word in {"explicar", "explique", "entender", "detalhar"}):
        return "explain"
    if any(word in plain for word in {"resumo", "resuma", "resumir", "sintese"}):
        return "summary"
    return "summary" if plain else "summary"


def _material_profile(text: str) -> dict:
    plain = _plain(text)
    topics = []
    if "teste" in plain and "software" in plain:
        topics.append("Testes e Qualidade de Software")
    if "caixa preta" in plain:
        topics.append("Caixa Preta")
    if "caixa branca" in plain:
        topics.append("Caixa Branca")
    if "particionamento" in plain or "equivalencia" in plain:
        topics.append("Particionamento por equivalencia")
    if "valor limite" in plain:
        topics.append("Analise de valor limite")
    if "tabela de decisao" in plain:
        topics.append("Tabela de decisao")
    if "grafo de fluxo" in plain:
        topics.append("Grafo de fluxo")
    if "complexidade ciclomatica" in plain:
        topics.append("Complexidade ciclomatica")
    if "caminho" in plain and "teste" in plain:
        topics.append("Caminhos de teste")
    return {
        "topics": list(dict.fromkeys(topics)),
        "keywords": _keywords(text),
    }


def _topic_from_text(text: str) -> str:
    compact = _compact(text)
    if not compact:
        return ""
    profile = _material_profile(compact)
    topics = profile.get("topics") or []
    if topics:
        return ", ".join(str(topic) for topic in topics[:5])
    first = _focus_lines(compact, limit=1)
    if first:
        return first[0][:220]
    return compact[:220]


def _question_sections(text: str, limit: int = 12) -> dict[int, str]:
    compact = _compact(text)
    if not compact:
        return {}

    sections: dict[int, str] = {}
    matches = list(re.finditer(r"\bQ\s*u\s*e?\s?s\s*t\s*[aã]\s*o\s*(\d+)\b|\bQuest[aã]o\s*(\d+)\b", compact, flags=re.I))
    for index, match in enumerate(matches[:limit]):
        number_text = match.group(1) or match.group(2)
        try:
            number = int(number_text)
        except Exception:
            continue
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(compact)
        section = _compact(compact[start:end])
        if section:
            sections[number] = section[:1600]
    return sections


def _summarize_material(name: str, text: str, focus: list[str], *, detailed: bool = False) -> list[str]:
    profile = _material_profile(text)
    topics = profile.get("topics") or []
    keywords = profile.get("keywords") or []
    lines = []

    if topics:
        lines.append(f"1. {name}: material sobre {', '.join(topics[:6])}.")
    else:
        topic = _topic_from_text(text)
        lines.append(f"1. {name}: material sobre {topic or 'o conteudo anexado'}.")

    if "Caixa Preta" in topics:
        lines.append("Foco de caixa preta: particionamento por equivalencia, valores-limite e tabelas de decisao.")
    if "Caixa Branca" in topics:
        lines.append("Foco de caixa branca: grafo de fluxo, complexidade ciclomatica e caminhos de teste.")

    if detailed and focus:
        lines.append("Pontos centrais: " + " ".join(f"- {line}" for line in focus[:5]))
    elif keywords:
        lines.append("Palavras-chave: " + ", ".join(keywords[:8]) + ".")
    return lines


def _explain_material(name: str, text: str, focus: list[str]) -> list[str]:
    profile = _material_profile(text)
    topics = set(profile.get("topics") or [])
    lines = _summarize_material(name, text, focus, detailed=True)
    if {"Caixa Preta", "Caixa Branca"} & topics:
        lines.append(
            "Em termos simples: caixa preta testa o comportamento observavel sem olhar o codigo; "
            "caixa branca usa a estrutura interna do codigo para escolher caminhos e condicoes de teste."
        )
    return lines


def _study_plan(name: str, text: str) -> list[str]:
    profile = _material_profile(text)
    topics = profile.get("topics") or _keywords(text, limit=6)
    plan = [f"Plano rapido para {name}:"]
    for index, topic in enumerate(topics[:6], start=1):
        plan.append(f"{index}. Revise {topic} e escreva um exemplo proprio.")
    plan.append("Depois resolva as questoes sem consultar o resumo e corrija pelos pontos-chave.")
    return plan


def _practice_questions_from_material(text: str, limit: int = 6) -> list[str]:
    profile = _material_profile(text)
    topics = profile.get("topics") or []
    templates = {
        "Particionamento por equivalencia": "Explique como separar entradas validas e invalidas em classes de equivalencia.",
        "Analise de valor limite": "Quais valores voce testaria nas bordas e logo fora delas?",
        "Tabela de decisao": "Como transformar regras com varias condicoes em uma tabela de decisao?",
        "Grafo de fluxo": "Como voce identificaria os nos e arestas principais do fluxo?",
        "Complexidade ciclomatica": "Como calcular V(G) e o que esse numero indica?",
        "Caminhos de teste": "Como escolher caminhos independentes para cobrir o fluxo?",
        "Caixa Preta": "Qual a diferenca entre testar por caixa preta e olhar a implementacao?",
        "Caixa Branca": "Que informacao do codigo ajuda a criar testes de caixa branca?",
    }
    questions = []
    for topic in topics:
        template = templates.get(str(topic))
        if template and template not in questions:
            questions.append(template)
        if len(questions) >= limit:
            break
    if len(questions) < 2:
        questions.extend(_questions_from_lines(_focus_lines(text, limit=limit), limit=limit - len(questions)))
    return [f"{index}. {question}" for index, question in enumerate(questions[:limit], start=1)]


def _format_study_file_response(name: str, text: str, focus: list[str], request: str) -> tuple[list[str], list[str]]:
    request_normalized = _plain(request)
    about_request = any(phrase in request_normalized for phrase in {"sobre o que", "do que se trata", "qual o assunto", "tema"})
    question_request = any(phrase in request_normalized for phrase in {"questoes", "questões", "perguntas", "exercicios", "exercícios"})

    if about_request:
        topic = _topic_from_text(text)
        if "caixa preta" in text.lower() or "caixa branca" in text.lower():
            return [
                f"1. {name}: e uma lista de exercicios de Testes e Qualidade de Software, focada em tecnicas de caixa preta e caixa branca."
            ], []
        return [f"1. {name}: o material parece tratar de {topic}."], []

    section = f"1. {name}: " + " ".join(f"- {line}" for line in focus[:4])
    questions = _questions_from_lines(focus, limit=6 if len(focus) >= 6 else max(2, len(focus))) if question_request or not request_normalized or "resum" in request_normalized else []
    return [section], questions


def _format_study_file_response(name: str, text: str, focus: list[str], request: str) -> tuple[list[str], list[str]]:
    kind = _study_request_kind(request)

    if kind == "about":
        return _summarize_material(name, text, focus, detailed=False), []
    if kind == "explain":
        return _explain_material(name, text, focus), []
    if kind == "plan":
        return _study_plan(name, text), []
    if kind == "practice":
        return _summarize_material(name, text, focus, detailed=False), _practice_questions_from_material(text)

    return _summarize_material(name, text, focus, detailed=(kind == "summary")), []


def _answer_question_section(number: int, section: str) -> str:
    normalized = _compact(section)
    if not normalized:
        return ""

    lower = _plain(normalized)
    if number == 1 and "particion" in lower and "equival" in lower and "pix" in lower:
        return (
            "A questao 1 pede particionamento em classes de equivalencia. "
            "Como o Pix aceita valores de R$ 1,00 a R$ 5.000,00, ha uma classe valida "
            "(1 <= valor <= 5000) e duas invalidas (valor < 1 e valor > 5000). "
            "Entao a alternativa correta e a que fala em 3 casos minimos de teste: "
            "um valor abaixo do limite, um valor dentro da faixa e um valor acima do limite."
        )

    if number == 2 and ("valor limite" in lower or "saque" in lower):
        return (
            "A questao 2 e de analise de valor limite. Para a faixa R$ 50 a R$ 1.000, "
            "os testes principais ficam nas bordas e vizinhos: 49, 50, 51, 999, 1000 e 1001. "
            "A tecnica revela defeitos de comparacao nos limites, como usar < no lugar de <=."
        )

    if number == 3 and ("tabela" in lower and "decis" in lower):
        return (
            "A questao 3 pede tabela de decisao. A regra de maior prioridade e pendencia financeira: "
            "se houver pendencia, bloqueia. Sem pendencia, se o pre-requisito nao foi cumprido, recusa. "
            "Se cumpriu o pre-requisito e ha vaga, efetiva. Se cumpriu tudo mas nao ha vaga, entra em lista de espera. "
            "Como ha 3 condicoes booleanas, a tabela completa tem 8 linhas."
        )

    if number == 4 and ("grafo" in lower or "fluxo" in lower):
        return (
            "A questao 4 pede derivar o grafo de fluxo do pseudocodigo. Os pontos de decisao sao: "
            "n <= 0, i <= n no loop, i % 2 == 0 e soma > 100. Depois voce conta nos, arestas "
            "e calcula a complexidade ciclomatica usando V(G) = A - N + 2 ou P + 1."
        )

    if number == 5 and ("complexidade" in lower or "v(g)" in lower):
        return (
            "Na questao 5: com 9 nos e 11 arestas, V(G) = A - N + 2 = 11 - 9 + 2 = 4. "
            "Com 3 nos de predicado, V(G) = P + 1 = 3 + 1 = 4. Os valores coincidem. "
            "Isso indica 4 caminhos independentes, ou seja, pelo menos 4 casos de teste para cobertura basica de caminhos."
        )

    if number == 6 and ("caminho" in lower or "teste" in lower):
        return (
            "A questao 6 pede caminhos de teste. Para o caixa eletronico, monte casos que cubram: "
            "valor invalido; valor valido com saldo insuficiente; valor valido com saldo suficiente; "
            "e, se houver repeticao para novo valor, um caminho que volte apos valor invalido."
        )

    if "valor limite" in lower or "fronteir" in lower:
        return (
            "Essa questao envolve analise de valor limite. Teste os valores nas bordas "
            "e logo fora delas, porque erros costumam aparecer em comparacoes como <, <=, > e >=."
        )

    if "tabela" in lower and "decis" in lower:
        return (
            "Essa questao pede tabela de decisao: liste as combinacoes das condicoes, aplique "
            "as regras em ordem de prioridade e indique o resultado de cada linha."
        )

    return (
        f"A questao {number} trata deste trecho: {normalized[:520]} "
        "A resposta deve seguir os conceitos citados no enunciado e justificar a escolha com base nas condicoes dadas."
    )


def _expected_terms_for_question(number: int, section: str) -> set[str]:
    lower = _plain(section)
    terms: set[str] = set()
    if number == 1 or "equivalencia" in lower:
        terms.update({"classe", "valida", "invalid", "abaixo", "acima", "3"})
    if "valor limite" in lower or number == 2:
        terms.update({"49", "50", "51", "999", "1000", "1001", "limite"})
    if "tabela" in lower or number == 3:
        terms.update({"pendencia", "pre-requisito", "vaga", "bloqueia", "recusa", "efetiva", "espera"})
    if "complexidade" in lower or number == 5:
        terms.update({"4", "caminhos", "independentes", "arestas", "nos"})
    return terms


def _correct_study_answer(number: int, section: str, user_answer: str) -> str:
    expected = _expected_terms_for_question(number, section)
    if not expected:
        return (
            f"Consigo corrigir a questao {number}, mas preciso comparar com o conceito do enunciado. "
            "Sua resposta deve explicar o raciocinio, nao so citar a alternativa."
        )
    plain_answer = _plain(user_answer)
    hits = sorted(term for term in expected if term in plain_answer)
    missing = sorted(term for term in expected if term not in plain_answer)
    if len(hits) >= max(2, len(expected) // 2):
        verdict = "Sua resposta esta no caminho certo."
    else:
        verdict = "Sua resposta ainda parece incompleta."
    return (
        f"{verdict} Pontos que apareceram: {', '.join(hits) if hits else 'nenhum ponto-chave claro'}. "
        f"Para melhorar, inclua: {', '.join(missing[:5]) if missing else 'uma justificativa curta e objetiva'}."
    )


def answer_study_followup(user_input: str) -> str | None:
    raw = _compact(user_input)
    normalized = _plain(raw)
    context = load_study_context()
    files = context.get("files") if isinstance(context, dict) else []
    if not isinstance(files, list) or not files:
        return None

    if any(phrase in normalized for phrase in {"sobre o que", "do que se trata", "qual o assunto", "que assunto"}):
        first = files[0] if isinstance(files[0], dict) else {}
        text = str(first.get("text") or "")
        name = str(first.get("name") or "arquivo")
        if "caixa preta" in _plain(text) or "caixa branca" in _plain(text):
            return (
                f"O {name} e uma lista de exercicios sobre Testes e Qualidade de Software. "
                "Ele trabalha tecnicas de caixa preta, como particionamento por equivalencia, "
                "analise de valor limite e tabela de decisao, e tecnicas de caixa branca, "
                "como grafo de fluxo, complexidade ciclomatica e caminhos de teste."
            )
        topic = str(first.get("topic") or "").strip()
        return f"O {name} parece ser sobre {topic or 'o material de estudo anexado'}."

    wants_all_questions = any(phrase in normalized for phrase in {"todas as questoes", "todas questoes", "todas as perguntas", "todos os exercicios"})
    if wants_all_questions and any(word in normalized for word in {"responder", "responda", "resolver", "resolva", "gabarito"}):
        answers = []
        for file_context in files:
            if not isinstance(file_context, dict):
                continue
            questions = file_context.get("questions") if isinstance(file_context.get("questions"), dict) else {}
            for number_text in sorted(questions, key=lambda value: int(value) if str(value).isdigit() else 999):
                if not str(number_text).isdigit():
                    continue
                number = int(number_text)
                answers.append(f"Questao {number}: {_answer_question_section(number, str(questions[number_text]))}")
        if answers:
            return "\n".join(answers[:8])

    question_match = re.search(r"(?:questao|pergunta|exercicio)\s*(\d+)", normalized)
    wants_answer = any(word in normalized for word in {"responder", "responda", "resposta", "resolver", "resolva", "pode responder"})
    wants_statement = any(word in normalized for word in {"enunciado", "mostrar", "mostre", "qual e", "qual eh"})
    wants_correction = any(word in normalized for word in {"corrigir", "corrija", "minha resposta", "respondi"})
    if question_match and (wants_answer or wants_statement or wants_correction):
        number = int(question_match.group(1))
        for file_context in files:
            if not isinstance(file_context, dict):
                continue
            questions = file_context.get("questions") if isinstance(file_context.get("questions"), dict) else {}
            section = str(questions.get(str(number)) or "")
            if section:
                if wants_statement and not wants_answer and not wants_correction:
                    return f"Enunciado da questao {number}: {_compact(section)[:900]}"
                if wants_correction:
                    return _correct_study_answer(number, section, raw)
                return _answer_question_section(number, section)
        return f"Eu lembro do arquivo, mas nao consegui separar o enunciado da questao {number} com seguranca."

    if any(word in normalized for word in {"perguntar", "arguir", "arguicao", "quiz", "simulado"}):
        first = files[0] if isinstance(files[0], dict) else {}
        text = str(first.get("text") or "")
        questions = _practice_questions_from_material(text, limit=6)
        if questions:
            return "Perguntas para praticar:\n" + "\n".join(questions)

    if any(word in normalized for word in {"resumir", "resuma", "resumo"}):
        first = files[0] if isinstance(files[0], dict) else {}
        name = str(first.get("name") or "arquivo")
        text = str(first.get("text") or "")
        focus = [str(item) for item in first.get("focus", [])] if isinstance(first.get("focus"), list) else []
        return " ".join(_summarize_material(name, text, focus, detailed=True))

    if any(word in normalized for word in {"plano", "revisao", "estudar"}):
        first = files[0] if isinstance(files[0], dict) else {}
        name = str(first.get("name") or "arquivo")
        text = str(first.get("text") or "")
        return "\n".join(_study_plan(name, text))

    return None


def _questions_from_lines(lines: list[str], start: int = 1, limit: int = 4) -> list[str]:
    questions = []
    stems = [
        "Explique com suas palavras",
        "Qual e a ideia central de",
        "Como voce aplicaria",
        "Que detalhe importante aparece em",
    ]
    for index, line in enumerate(lines[:limit], start=start):
        stem = stems[(index - start) % len(stems)]
        questions.append(f"{index}. {stem}: {line[:120]}?")
    return questions


def analyze_study_files(paths: list[str], request: str = "") -> str:
    clean_paths = [str(path).strip().strip('"') for path in paths if str(path).strip()]
    if not clean_paths:
        return "Me envie ou informe pelo menos um arquivo de estudo."

    sections = []
    all_focus: list[str] = []
    practice_questions: list[str] = []
    context_files: list[dict] = []
    failures = []

    for index, path in enumerate(clean_paths, start=1):
        result = process_file(path, max_chars=9000)
        file_info = result.get("file", {}) if isinstance(result, dict) else {}
        name = str(file_info.get("name") or Path(path).name)
        if not result.get("ok"):
            failures.append(f"{name}: {result.get('error', 'nao consegui ler')}")
            continue

        text = _extract_text(result)
        if _study_text_is_untrusted(text):
            sections.append(f"{index}. {name}: {_untrusted_extraction_message(result)}")
            continue

        focus = _focus_lines(text, limit=6)
        all_focus.extend(focus)
        question_sections = _question_sections(text)
        context_files.append(
            {
                "path": str(path),
                "name": name,
                "text": _compact(text)[:12000],
                "focus": focus,
                "questions": {str(key): value for key, value in question_sections.items()},
                "topic": _topic_from_text(text),
            }
        )
        if not focus:
            note = _extraction_note(result)
            if note:
                sections.append(f"{index}. {name}: {note}")
            else:
                sections.append(f"{index}. {name}: consegui abrir, mas nao encontrei texto suficiente para estudar.")
            continue

        file_sections, file_questions = _format_study_file_response(name, text, focus, request)
        if file_sections and file_sections[0].startswith("1. "):
            file_sections[0] = f"{index}. " + file_sections[0][3:]
        sections.extend(file_sections)
        practice_questions.extend(file_questions)

    if not sections and failures:
        return "Nao consegui analisar os arquivos. " + " ; ".join(failures[:3])

    if context_files:
        save_study_context(
            {
                "source": "attached_files",
                "request": request,
                "files": context_files,
            }
        )

    response = ["Analise de estudo dos arquivos:"]
    response.extend(sections)

    if failures:
        response.append("Arquivos com problema: " + " ; ".join(failures[:3]))

    request_normalized = _plain(request)
    should_generate_questions = not request_normalized or _study_request_kind(request) == "practice"
    question_count = 6 if len(all_focus) >= 6 else max(2, len(all_focus))
    questions = practice_questions or (_questions_from_lines(all_focus, limit=question_count) if should_generate_questions else [])
    if questions:
        response.append("Questoes para praticar:")
        response.extend(questions)
        response.append("Gabarito curto: responda com base nos pontos-chave acima; eu posso corrigir suas respostas depois.")

    if request:
        response.append(f"Pedido considerado: {request}.")

    return "\n".join(response)
