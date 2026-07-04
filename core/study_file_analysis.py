from __future__ import annotations

import json
import re
import shlex
import unicodedata
from pathlib import Path

from file_processor.detector import TEXT_EXTENSIONS
from file_processor.processor import process_file
from memory.study_context import load_study_context, save_study_context

SUPPORTED_STUDY_EXTENSIONS = {
    *TEXT_EXTENSIONS,
    ".pdf",
    ".pptx",
    ".docx",
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".xlsx",
}
MAX_FILES_PER_DIRECTORY_ANALYSIS = 12
MAX_PARTIAL_FILE_SEARCH_ITEMS = 2500
STUDY_ANALYSIS_CACHE_VERSION = 2


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").replace("\x00", "")).strip()


def _clean_readable_text(text: str) -> str:
    cleaned = _compact(text)
    if not cleaned:
        return ""
    headings = (
        "Objetivo",
        "Perfil Profissional",
        "Tecnologias",
        "Experiência",
        "Experiencia",
        "Projetos",
        "Formação",
        "Formacao",
        "Educação",
        "Educacao",
        "Idiomas",
        "Contato",
    )
    for heading in headings:
        cleaned = re.sub(rf"(?<!^)(?<![.:\n]\s)(?<!\s)({re.escape(heading)})(?=\b)", rf". \1", cleaned)
    cleaned = re.sub(r"(\d+\s+anos)\s*([A-ZÁ-Ú])", r"\1. \2", cleaned)
    cleaned = re.sub(r"([.!?])([A-ZÁ-Ú])", r"\1 \2", cleaned)
    cleaned = re.sub(r",(?=\S)", ", ", cleaned)
    cleaned = re.sub(r"\s+([,.!?;:])", r"\1", cleaned)
    cleaned = re.sub(r"\.{2,}", ".", cleaned)
    return _compact(cleaned)


def _plain(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", _compact(text))
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def _candidate_file_search_roots() -> list[Path]:
    roots: list[Path] = []
    for root in (
        Path.cwd(),
        Path.home() / "Downloads",
        Path.home() / "Documents" / "Downloads",
        Path.home() / "Documents",
        Path.home() / "Desktop",
        Path.home() / "OneDrive" / "Área de Trabalho",
        Path.home(),
    ):
        try:
            resolved = root.expanduser().resolve()
        except Exception:
            continue
        if resolved.exists() and resolved.is_dir() and resolved not in roots:
            roots.append(resolved)
    return roots


def _resolve_file_reference_by_name(reference: str) -> str | None:
    query = _plain(reference)
    tokens = [token for token in re.findall(r"\w+", query) if len(token) >= 2]
    if not tokens:
        return None

    reference_path = Path(str(reference or "").strip().strip('"'))
    requested_name = _plain(reference_path.name) if reference_path.name else ""
    if requested_name:
        for root in _candidate_file_search_roots():
            try:
                direct = root / reference_path.name
                if direct.is_file() and direct.suffix.lower() in SUPPORTED_STUDY_EXTENSIONS:
                    return str(direct)
            except Exception:
                continue

    best: tuple[int, float, Path] | None = None
    for root in _candidate_file_search_roots():
        seen = 0
        try:
            iterator = root.rglob("*")
            for candidate in iterator:
                if seen >= MAX_PARTIAL_FILE_SEARCH_ITEMS:
                    break
                if not candidate.is_file():
                    continue
                seen += 1
                if candidate.suffix.lower() not in SUPPORTED_STUDY_EXTENSIONS:
                    continue
                haystack = _plain(f"{candidate.stem} {candidate.name} {candidate.parent.name}")
                if not all(token in haystack for token in tokens):
                    continue
                score = sum(3 if token in _plain(candidate.stem) else 1 for token in tokens)
                if query in haystack:
                    score += 4
                try:
                    modified = candidate.stat().st_mtime
                except Exception:
                    modified = 0.0
                current = (score, modified, candidate)
                if best is None or (current[0], current[1]) > (best[0], best[1]):
                    best = current
        except Exception:
            continue
    return str(best[2]) if best else None


def polish_study_response(text: str) -> str:
    polished = str(text or "").replace("\x00", "")
    replacements = [
        ("Analise de estudo dos arquivos:", "Análise de estudo dos arquivos:"),
        ("Analise dos arquivos:", "Análise dos arquivos:"),
        ("Questoes para praticar:", "Questões para praticar:"),
        ("Perguntas para praticar:", "Perguntas para praticar:"),
        ("Gabarito curto:", "Gabarito curto:"),
        ("Pedido considerado:", "Pedido considerado:"),
        ("Arquivos com problema:", "Arquivos com problema:"),
        ("arquivos analisaveis", "arquivos analisáveis"),
        ("arquivo(s)", "arquivo(s)"),
        ("Nao consegui analisar os arquivos.", "Não consegui analisar os arquivos."),
        ("Nao vou resumir esse arquivo ainda:", "Não vou resumir esse arquivo ainda:"),
        ("nao consegui ler", "não consegui ler"),
        ("nao consegui separar", "não consegui separar"),
        ("nao encontrei", "não encontrei"),
        ("nao passou", "não passou"),
        ("nao so", "não só"),
        ("nao foi", "não foi"),
        ("nao ha", "não há"),
        ("ha uma", "há uma"),
        ("ha 3", "há 3"),
        ("ha vaga", "há vaga"),
        ("voce", "você"),
        ("proprio", "próprio"),
        ("conteudo", "conteúdo"),
        ("extracao", "extração"),
        ("codificacao", "codificação"),
        ("versao", "versão"),
        ("seguranca", "segurança"),
        ("confianca", "confiança"),
        ("verificacao", "verificação"),
        ("Questoes", "Questões"),
        ("questoes", "questões"),
        ("Questao", "Questão"),
        ("questao", "questão"),
        ("exercicios", "exercícios"),
        ("exercicio", "exercício"),
        ("explicito", "explícito"),
        ("tecnicas", "técnicas"),
        ("tecnica", "técnica"),
        ("equivalencia", "equivalência"),
        ("Analise de valor limite", "Análise de valor limite"),
        ("analise de valor limite", "análise de valor limite"),
        ("analise", "análise"),
        ("decisao", "decisão"),
        ("ciclomatica", "ciclomática"),
        ("Complexidade Ciclomatica", "Complexidade Ciclomática"),
        ("Complexidade ciclomatica", "Complexidade ciclomática"),
        ("validas", "válidas"),
        ("valida", "válida"),
        ("invalidas", "inválidas"),
        ("invalido", "inválido"),
        ("minimos", "mínimos"),
        ("basica", "básica"),
        ("codigo", "código"),
        ("eletronico", "eletrônico"),
        ("bancario", "bancário"),
        ("transferencias", "transferências"),
        ("observavel", "observável"),
        ("condicoes", "condições"),
        ("combinacoes", "combinações"),
        ("comparacao", "comparação"),
        ("repeticao", "repetição"),
        ("informacao", "informação"),
        ("implementacao", "implementação"),
        ("diferenca", "diferença"),
        ("raciocinio", "raciocínio"),
        ("revisao", "revisão"),
        ("arguicao", "arguição"),
        ("pendencia", "pendência"),
        ("pre-requisito", "pré-requisito"),
        ("tambem", "também"),
        ("rapido", "rápido"),
        ("maximo", "máximo"),
        ("minimo", "mínimo"),
        ("numero", "número"),
        ("apos", "após"),
        ("materia", "matéria"),
        ("celula", "célula"),
        ("celulas", "células"),
        ("identicas", "idênticas"),
        ("varias", "várias"),
        ("esta no caminho", "está no caminho"),
        ("esta incompleta", "está incompleta"),
        ("Pontos que apareceram", "Pontos que apareceram"),
    ]
    for old, new in replacements:
        if re.match(r"^\w", old) and re.search(r"\w$", old):
            polished = re.sub(rf"\b{re.escape(old)}\b", new, polished)
        else:
            polished = re.sub(re.escape(old), new, polished)

    phrase_replacements = [
        (r"\bO ([\w .-]+) e uma lista\b", r"O \1 é uma lista"),
        (r"\bA questão (\d+) e de\b", r"A questão \1 é de"),
        (r"\bA regra de maior prioridade e\b", "A regra de maior prioridade é"),
        (r"\bSua resposta esta\b", "Sua resposta está"),
        (r"\bEle trabalha tecnicas\b", "Ele trabalha técnicas"),
        (r"\bA resposta correta e\b", "A resposta correta é"),
        (r"\bEntao a alternativa correta e\b", "Então a alternativa correta é"),
        (r"\bEntao\b", "Então"),
        (r"\bQual e a ideia central\b", "Qual é a ideia central"),
        (r"\bqual e\b", "qual é"),
        (r"\b e uma lista de exercícios\b", " é uma lista de exercícios"),
        (r"\b e duas inválidas\b", " e duas inválidas"),
    ]
    for pattern, replacement in phrase_replacements:
        polished = re.sub(pattern, replacement, polished, flags=re.I)

    polished = re.sub(r"(\d+)\s+nos\b", r"\1 nós", polished, flags=re.I)
    polished = re.sub(r"\bnos e arestas\b", "nós e arestas", polished, flags=re.I)
    polished = re.sub(r"\bnos de predicado\b", "nós de predicado", polished, flags=re.I)
    polished = re.sub(r"\bconta nos\b", "conta nós", polished, flags=re.I)
    polished = re.sub(r"\bcomo texto pesquisavel\b", "como texto pesquisável", polished, flags=re.I)
    polished = re.sub(r"\btexto suficiente para estudar\b", "texto suficiente para estudar", polished, flags=re.I)

    polished = re.sub(r"\s+([,.!?;:])", r"\1", polished)
    polished = re.sub(r"([.!?]){2,}", r"\1", polished)
    return polished.strip()


def _contains_any(text: str, needles: set[str]) -> bool:
    plain = _plain(text)
    return any(needle in plain for needle in needles)


def _is_page_only_reference(reference: str) -> bool:
    plain = _plain(reference).strip(" .,:;!?")
    page_words = (
        "primeira",
        "primeiro",
        "segunda",
        "segundo",
        "terceira",
        "terceiro",
        "quarta",
        "quarto",
        "quinta",
        "quinto",
        "sexta",
        "sexto",
        "setima",
        "setimo",
        "oitava",
        "oitavo",
        "nona",
        "nono",
        "decima",
        "decimo",
    )
    page_word_pattern = "|".join(page_words)
    return bool(
        re.fullmatch(r"(?:na|no|a|o)?\s*(?:pagina|pag|p)\s*\d+", plain)
        or re.fullmatch(rf"(?:na|no|a|o)?\s*(?:{page_word_pattern})\s+pagina", plain)
        or re.fullmatch(rf"(?:na|no|a|o)?\s*pagina\s+(?:{page_word_pattern})", plain)
    )


def _strip_study_payload_tail(payload: str) -> tuple[str, str | None]:
    raw = str(payload or "").strip()
    normalized = _plain(raw)
    for pattern, request in (
        (r"\s+(?:e\s+depois|e|ai|aí|depois)\s+(?:me\s+)?(?:explique|explica|fala|fale)\b", "explique"),
        (r"\s+(?:e\s+depois|e|ai|aí|depois)\s+(?:me\s+)?(?:resuma|resume)\b", "resuma"),
        (r"\s+(?:e\s+depois|e|ai|aí|depois)\s+(?:me\s+)?(?:crie|cria|gere|gera|faca|faça)\s+(?:perguntas|questoes|questões)\b", "gere questoes"),
        (r"\s+(?:e\s+depois|e|ai|aí|depois)\s+(?:me\s+)?(?:da|dá|de|dê|recomenda|recomende|avisa|avise)\b", None),
    ):
        match = re.search(pattern, normalized)
        if match:
            return raw[: match.start()].strip(" .,:;-"), request
    return raw, None


def parse_study_file_command(user_input: str) -> tuple[list[str], str] | None:
    raw = str(user_input or "").strip()
    if re.match(r"^(?:ler|leia|ver|veja)\s+(?:o\s+)?arquivo\b", raw, flags=re.I):
        return None
    command_match = re.match(
        r"^(?P<verb>analisar|analise|analisa|ler|leia|resumir|resuma|estudar|estude|explicar|explique|falar sobre|fale sobre|ver|veja|gerar questoes de|fazer questoes de)\b",
        raw,
        flags=re.I,
    )
    inferred_request = ""
    if command_match:
        verb = _plain(command_match.group("verb"))
        if verb in {"explicar", "explique", "falar sobre", "fale sobre"}:
            inferred_request = "explique"
        elif verb in {"resumir", "resuma"}:
            inferred_request = "resuma"
        elif "questoes" in verb:
            inferred_request = "gere questoes"
        elif verb in {"estudar", "estude"}:
            inferred_request = "estude"
        elif verb in {"ler", "leia", "ver", "veja", "analisar", "analise", "analisa"}:
            inferred_request = "o que tem nesse arquivo"

    flexible_natural_match = re.match(
        r"^(?:o\s*que|oque|oq)\s+(?:tem|ha|há)\s+"
        r"(?:(?:no|nesse|neste|naquele|em)\s+)?"
        r"(?:(?:arquivo|documento|pdf|docx|txt|md)\s+)?(.+?)\s*$",
        raw,
        flags=re.I,
    )
    if flexible_natural_match:
        reference = flexible_natural_match.group(1).strip(" .,:;-\"'?!")
        reference, tail_request = _strip_study_payload_tail(reference)
        if _plain(reference) in {"tela", "a tela", "na tela", "isso", "ai", "aqui"}:
            return None
        if _is_page_only_reference(reference):
            return None
        resolved = _resolve_file_reference_by_name(reference)
        if resolved:
            return [resolved], tail_request or f"o que tem no arquivo {reference}"
        if _plain(reference) in {"arquivo", "documento", "pdf", "slide", "slides"}:
            return None
        return [reference], tail_request or f"o que tem no arquivo {reference}"

    natural_match = re.match(
        r"^(?:o\s*que|oque|oq)\s+(?:tem|ha|há)\s+(?:no|nesse|neste|naquele)?\s*arquivo\s+(.+?)\s*$",
        raw,
        flags=re.I,
    )
    if natural_match:
        reference = natural_match.group(1).strip(" .,:;-\"'")
        reference, tail_request = _strip_study_payload_tail(reference)
        resolved = _resolve_file_reference_by_name(reference)
        if resolved:
            return [resolved], tail_request or f"o que tem no arquivo {reference}"
        return [reference], tail_request or f"o que tem no arquivo {reference}"

    match = re.match(
        r"^(?:analisar|analise|analisa|ler|leia|resumir|resuma|estudar|estude|explicar|explique|falar sobre|fale sobre|ver|veja|gerar questoes de|fazer questoes de)\s+"
        r"(?:(?:os?|as?|estes?|essas?|esses?)\s+)?"
        r"(?:(?:arquivos?|anexos?|slides?|materiais?|documentos?|pasta|diretorio|diretório)\s*)?"
        r"(?:anexados?)?\s*[:,-]?\s*(.+)$",
        raw,
        flags=re.I,
    )
    if not match:
        return None

    payload = match.group(1).strip()
    payload_plain = _plain(payload)
    generic_non_file_targets = {
        "tela",
        "a tela",
        "na tela",
        "grafico",
        "grafico em segundo plano",
        "tela em segundo plano",
        "codigo",
        "o codigo",
        "em segundo plano",
    }
    if payload_plain in generic_non_file_targets:
        return None
    request = inferred_request
    for separator in (" :: ", " pedido: ", " tarefa: "):
        if separator in payload:
            payload, request = payload.split(separator, 1)
            break
    else:
        payload, tail_request = _strip_study_payload_tail(payload)
        if tail_request:
            request = tail_request

    paths: list[str] = []
    if payload.startswith("["):
        try:
            data = json.loads(payload)
            paths = [str(item).strip() for item in data if str(item).strip()] if isinstance(data, list) else []
        except Exception:
            paths = []
    else:
        payload = re.sub(
            r"^(?:em|no caminho|na pasta|no diretorio|no diretório|o arquivo|a pasta)\s+",
            "",
            payload.strip(),
            flags=re.I,
        )
        if Path(payload.strip().strip('"')).expanduser().exists():
            paths = [payload.strip()]
        else:
            resolved = _resolve_file_reference_by_name(payload.strip().strip('"'))
            if resolved:
                paths = [resolved]
            else:
                try:
                    paths = [item.strip() for item in shlex.split(payload, posix=False) if item.strip()]
                except ValueError:
                    paths = [item.strip() for item in re.split(r"\s*\|\s*", payload) if item.strip()]

    cleaned_paths = []
    for path in paths:
        cleaned = path.strip().strip('"')
        candidate = Path(cleaned).expanduser()
        if cleaned and (candidate.is_dir() or candidate.suffix.lower() in SUPPORTED_STUDY_EXTENSIONS):
            if not candidate.exists() and not candidate.is_absolute():
                resolved = _resolve_file_reference_by_name(cleaned)
                if resolved:
                    cleaned = resolved
            cleaned_paths.append(cleaned)
    if not cleaned_paths and paths:
        explicit_file_reference = bool(
            re.search(r"[\\/]", payload)
            or re.search(r"\.(?:pdf|docx?|pptx?|xlsx?|csv|txt|md|html?|py|js|ts|tsx|jsx|json)\b", payload, flags=re.I)
            or re.search(r"\b(?:arquivos?|anexos?|slides?|materiais?|documentos?|pasta|diretorio|diretório)\b", raw, flags=re.I)
        )
        if not explicit_file_reference or re.search(r"\b(?:segundo plano|tela|grafico|gráfico|codigo|código)\b", payload, flags=re.I):
            return None
        fallback = payload.strip().strip('"') if "payload" in locals() else str(paths[0]).strip().strip('"')
        return [fallback], _compact(request)
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
        line = _clean_readable_text(raw_line)
        if len(line) < 24:
            continue
        if _plain(line).startswith("professor"):
            continue
        candidates.append(line)
    if not candidates:
        sentences = re.split(r"(?<=[.!?])\s+", _clean_readable_text(text))
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
        "modulao",
        "ncia",
        "professor",
        "marco",
        "antonio",
        "camara",
        "antnio",
        "cmara",
    }
    counts: dict[str, int] = {}
    for token in re.findall(r"\b[\wÀ-ÿ]{4,}\b", _plain(text)):
        if token in stopwords or token.isdigit():
            continue
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, _count in ranked[:limit]]


def _page_quality_warning(page_text: str) -> str:
    text = _clean_readable_text(page_text)
    plain = _plain(text)
    compact = re.sub(r"\s+", "", text)
    words = re.findall(r"\b\w{3,}\b", text)
    hard_symbols = len(re.findall(r"[#%&*+<=>@\\^_`{|}~]", text))
    suspicious_agenda = bool(re.search(r"\bagenda\s+[a-z]\b$", plain))

    if not text:
        return "sem texto legivel"
    if hard_symbols >= 3:
        return "texto com sinais de extracao ruim"
    if suspicious_agenda or ("agenda" in plain and len(compact) < 90 and len(words) <= 8):
        return "leitura parcial: a pagina parece ser uma agenda/indice, mas a extracao veio incompleta"
    if len(compact) < 45 and len(words) <= 5 and "pagina" not in plain:
        return "leitura curta: pode ser capa/titulo ou extracao incompleta"
    return ""


def _study_request_kind(request: str) -> str:
    plain = _plain(request)
    if any(phrase in plain for phrase in {"sobre o que", "o que tem", "do que se trata", "qual o assunto", "que assunto", "tema"}):
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


def request_is_study_or_practice(request: str) -> bool:
    plain = _plain(request)
    if "nome do projeto" in plain or "qual o projeto" in plain or "qual era o projeto" in plain or "projeto do arquivo" in plain:
        return False
    return any(
        word in plain
        for word in {
            "estudar",
            "estude",
            "estudo",
            "slides",
            "aula",
            "questoes",
            "perguntas",
            "exercicios",
            "simulado",
            "quiz",
            "gabarito",
            "responder",
            "responda",
            "resolver",
            "resolva",
            "plano",
            "revisao",
        }
    )


def _material_profile(text: str) -> dict:
    plain = _plain(text)
    if _looks_like_cv_text(text) or _looks_like_project_readme(text):
        return {
            "topics": [],
            "keywords": _keywords(text),
        }
    topics = []
    if "redes de computadores" in plain:
        topics.append("Redes de Computadores")
    if "comunicacao digital" in plain:
        topics.append("Comunicação Digital")
    if "conceitos basicos" in plain or "conceitos basicos hw" in plain:
        topics.append("Conceitos Básicos de hardware e software")
    if "meios fisicos" in plain:
        topics.append("Meios Físicos")
    if "informacoes digitais" in plain or "informacao digital" in plain:
        topics.append("Informações Digitais e Binárias")
    project_readme_markers = any(
        marker in plain
        for marker in {
            "sobre o projeto",
            "como executar o projeto",
            "estrutura do projeto",
            "tecnologias utilizadas",
            "integrantes",
        }
    )
    if "teste" in plain and "software" in plain and not project_readme_markers:
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


def _looks_like_study_material(text: str) -> bool:
    plain = _plain(text)
    if _looks_like_cv_text(text) or _looks_like_project_readme(text):
        return False
    if _material_profile(text).get("topics"):
        return True
    if _question_sections(text):
        return True
    return any(
        phrase in plain
        for phrase in {
            "lista de exercicios",
            "responda as questoes",
            "questoes para praticar",
            "atividade avaliativa",
            "plano de aula",
            "conteudo programatico",
        }
    )


def _looks_like_slide_deck_text(text: str) -> bool:
    raw_lines = [str(line or "").strip() for line in str(text or "").splitlines()]
    lines = [_clean_readable_text(line) for line in raw_lines if str(line or "").strip()]
    plain = _plain("\n".join(lines))
    if not plain:
        return False

    markers = {
        "agenda",
        "professor",
        "slide",
        "aula",
        "topicos",
        "topicos da aula",
        "objetivos",
        "conteudo programatico",
        "referencias",
    }
    marker_hits = sum(1 for marker in markers if marker in plain)
    short_heading_lines = [
        line
        for line in lines
        if 4 <= len(line) <= 80
        and not line.endswith(".")
        and len(re.findall(r"\w+", line)) <= 8
    ]
    repeated_teaching_terms = sum(1 for term in {"professor", "agenda", "aula"} if term in plain)
    return marker_hits >= 2 or (repeated_teaching_terms >= 1 and len(short_heading_lines) >= 5)


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


def _dedupe_focus(lines: list[str], limit: int = 4) -> list[str]:
    unique = []
    seen = set()
    for line in lines:
        compact = _clean_readable_text(line)
        if not compact:
            continue
        key = _plain(compact[:180])
        if key in seen:
            continue
        seen.add(key)
        unique.append(compact)
        if len(unique) >= limit:
            break
    return unique


def _looks_like_cv_text(text: str) -> bool:
    plain = _plain(text)
    markers = {
        "curriculo",
        "currículo",
        "objetivo",
        "perfil profissional",
        "formacao academica",
        "formação acadêmica",
        "experiencia profissional",
        "experiência profissional",
        "experiencia pratica",
        "experiência prática",
        "habilidades",
        "linkedin",
        "github",
    }
    markers.update(
        {
            "objetivo profissional",
            "objetivo academico",
            "resumo profissional",
            "formacao",
            "educacao",
            "competencias",
            "tecnologias",
            "certificacoes",
            "cursos",
            "idiomas",
            "portfolio",
        }
    )
    contact_score = 0
    if re.search(r"[\w.+-]+@[\w.-]+\.\w+", text):
        contact_score += 2
    if re.search(r"(?:\+?\d{2}\s*)?(?:\(?\d{2}\)?\s*)?\d{4,5}[-\s]?\d{4}", text):
        contact_score += 2
    if any(word in plain for word in {"linkedin", "github", "portfolio"}):
        contact_score += 1
    marker_hits = sum(1 for marker in markers if marker in plain)
    if "objetivo" in plain and "perfil profissional" in plain:
        return True
    if contact_score >= 2 and marker_hits >= 2:
        return True
    return marker_hits >= 3


def _looks_like_project_readme(text: str) -> bool:
    plain = _plain(text)
    markers = {
        "sobre o projeto",
        "como executar o projeto",
        "estrutura do projeto",
        "tecnologias utilizadas",
        "integrantes",
        "principais classes",
        "regras de filtragem",
        "como rodar os testes",
        "cobertura de testes",
    }
    if sum(1 for marker in markers if marker in plain) < 2:
        return False
    return not _looks_like_cv_text(text)


def _cv_profile(text: str) -> dict[str, str]:
    compact = _clean_readable_text(text)
    plain = _plain(compact)
    if not _looks_like_cv_text(compact):
        return {}

    name_match = re.match(r"^\s*([A-ZÁ-Ú][\wÀ-ÿ]+(?:\s+[A-ZÁ-Ú][\wÀ-ÿ]+){1,5})", compact)
    name = name_match.group(1).strip() if name_match else ""
    if name:
        name = re.split(r"\b(?:Objetivo|Perfil|Tecnologias|Experiencia)\b", name, maxsplit=1)[0].strip()
    objective = ""
    objective_match = re.search(
        r"Objetivo\s+(.+?)(?:\s+Perfil Profissional\b|\s+Tecnologias\b|\s+Experiência\b|\s+Experiencia\b|$)",
        compact,
        flags=re.I,
    )
    if objective_match:
        objective = _compact(objective_match.group(1))[:260]

    technologies = []
    known_technologies = (
        ("TypeScript", "typescript"),
        ("React Native", "react native"),
        ("React.js", "react.js"),
        ("React", "react"),
        ("Supabase", "supabase"),
        ("MySQL", "mysql"),
        ("JavaScript", "javascript"),
        ("Java", "java"),
        ("HTML5", "html5"),
        ("CSS3", "css3"),
        ("APIs", "apis"),
        ("Git", "git"),
    )
    for label, needle in known_technologies:
        if needle in plain and label not in technologies:
            technologies.append(label)
        if len(technologies) >= 7:
            break
    if "React" in technologies and ("React Native" in technologies or "React.js" in technologies):
        technologies = [technology for technology in technologies if technology != "React"]

    return {
        "name": name,
        "objective": objective,
        "technologies": ", ".join(dict.fromkeys(technologies)),
    }


def _project_readme_profile(text: str) -> dict[str, str]:
    if not _looks_like_project_readme(text):
        return {}
    sections = _markdown_sections(text)
    projects = _project_names_from_text(text)
    about_match = _section_by_keywords(sections, {"sobre", "sobre o projeto"})
    tech_match = _section_by_keywords(sections, {"tecnologias", "ferramentas", "stack", "linguagens"})
    return {
        "name": projects[0] if projects else "",
        "about": about_match[1] if about_match else sections.get("inicio", ""),
        "technologies": tech_match[1] if tech_match else "",
    }


def _article_profile(text: str, focus: list[str]) -> dict[str, str]:
    if _looks_like_cv_text(text) or _looks_like_project_readme(text) or _looks_like_study_material(text):
        return {}
    plain = _plain(text)
    markers = {
        "resumo",
        "abstract",
        "introducao",
        "introdução",
        "metodologia",
        "metodo",
        "método",
        "resultados",
        "discussao",
        "discussão",
        "conclusao",
        "conclusão",
        "referencias",
        "referências",
        "palavras-chave",
        "doi",
    }
    marker_hits = sum(1 for marker in markers if marker in plain)
    if marker_hits < 2:
        return {}
    keywords = _keywords(text, limit=6)
    topic = ", ".join(keywords[:4]) if keywords else _topic_from_text(text)
    useful = _dedupe_focus(focus, limit=2)
    return {
        "topic": topic,
        "summary": " ".join(useful),
    }


def _format_general_file_response(name: str, text: str, focus: list[str], request: str) -> list[str]:
    direct_answer = _answer_specific_file_request(name, text, request)
    if direct_answer:
        return [direct_answer]

    profile = _cv_profile(text)
    if profile:
        subject = profile.get("name") or Path(name).stem
        lines = [f"1. {name}: é um currículo de {subject}."]
        if profile.get("objective"):
            lines.append(f"Objetivo: {profile['objective']}.")
        if profile.get("technologies"):
            lines.append(f"Tecnologias citadas: {profile['technologies']}.")
        return lines

    project = _project_readme_profile(text)
    if project:
        subject = f" chamado {project['name']}" if project.get("name") else ""
        lines = [f"1. {name}: e um README de projeto{subject}."]
        if project.get("about"):
            lines.append(_short_section_answer("Sobre", project["about"], max_chars=300))
        if project.get("technologies"):
            lines.append(_short_section_answer("Tecnologias", project["technologies"], max_chars=220))
        return lines

    article = _article_profile(text, focus)
    if article:
        topic = article.get("topic") or "o tema do arquivo"
        lines = [f"1. {name}: parece um artigo ou texto tecnico sobre {topic}."]
        if article.get("summary"):
            lines.append(_short_section_answer("Resumo", article["summary"], max_chars=360))
        return lines

    useful = _dedupe_focus(focus, limit=3)
    if useful:
        return [f"1. {name}: " + " ".join(useful)]
    topic = _topic_from_text(text)
    return [f"1. {name}: contém {topic or 'informações do arquivo anexado'}."]


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
        for fallback in _questions_from_lines(_focus_lines(text, limit=limit), limit=limit - len(questions)):
            questions.append(re.sub(r"^\d+\.\s*", "", fallback))
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
    if not request_is_study_or_practice(request) and not _looks_like_study_material(text):
        return _format_general_file_response(name, text, focus, request), []

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


def _project_names_from_text(text: str) -> list[str]:
    compact = _clean_readable_text(text)
    if not compact:
        return []

    candidates: list[str] = []
    markdown_title = re.search(r"(?:^|\s)#\s+([A-ZÁ-Ú][\wÀ-ÿ0-9]*(?:\s+[A-ZÁ-Ú0-9][\wÀ-ÿ0-9]*){0,5})", compact)
    if markdown_title:
        candidates.append(markdown_title.group(1).strip(" .,:;-"))

    bold_definition = re.search(r"\*\*([^*]{3,80})\*\*\s+(?:e|é)\s+", compact, flags=re.I)
    if bold_definition:
        candidates.append(bold_definition.group(1).strip(" .,:;-"))

    project_section = re.search(
        r"(?:^|[.;]\s*)Projetos?\s*[:.-]?\s*(.+?)(?:\s+(?:Formação|Formacao|Educação|Educacao|Experiência|Experiencia|Tecnologias|Idiomas|Contato)\b|$)",
        compact,
        flags=re.I,
    )
    if project_section:
        section = project_section.group(1)
        for item in re.split(r"\s*(?:[•\n]|;\s+|\.\s+)\s*", section):
            item = _compact(item)
            if not item:
                continue
            name = re.split(r"\s+(?:-|–|—|:)\s+|\s{2,}", item, maxsplit=1)[0].strip(" .,:;-")
            if 3 <= len(name) <= 80:
                candidates.append(name)

    for match in re.finditer(r"\bprojeto\s+([A-ZÁ-Ú][\wÀ-ÿ0-9]*(?:\s+[A-ZÁ-Ú0-9][\wÀ-ÿ0-9]*){0,5})", compact):
        candidates.append(match.group(1).strip(" .,:;-"))

    blocked = {
        "Projetos",
        "Projeto",
        "Projetos em React Native e APIs",
        "em React Native e APIs",
    }
    unique = []
    for candidate in candidates:
        cleaned = _compact(candidate)
        if len(cleaned) < 3:
            continue
        if cleaned in blocked:
            continue
        plain = _plain(cleaned)
        if plain in {"projetos", "projeto", "portfolio", "github"}:
            continue
        if plain not in {_plain(item) for item in unique}:
            unique.append(cleaned)
    return unique[:5]


def _answer_project_name_from_file(name: str, text: str, topic: str = "") -> str:
    projects = _project_names_from_text(text)
    if projects:
        if len(projects) == 1:
            return f"O projeto do arquivo {name} se chama {projects[0]}."
        return f"No arquivo {name}, encontrei estes projetos citados: {', '.join(projects)}."
    return f"No arquivo {name}, nao encontrei um nome de projeto explicito. Ele parece descrever {topic or 'o conteudo do arquivo'}."


def _markdown_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = "inicio"
    prepared = re.sub(r"\s+(#{1,6}\s+)", r"\n\1", str(text or ""))
    for raw_line in prepared.splitlines():
        line = _compact(raw_line)
        if not line:
            continue
        heading = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if heading:
            current = _plain(heading.group(1).strip(" .,:;-"))
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {key: _clean_readable_text(" ".join(value)) for key, value in sections.items() if value}


def _section_by_keywords(sections: dict[str, str], keywords: set[str]) -> tuple[str, str] | None:
    for title, content in sections.items():
        title_plain = _plain(title)
        if any(keyword in title_plain for keyword in keywords):
            return title, content
    return None


def _short_section_answer(label: str, content: str, *, max_chars: int = 520) -> str:
    compact = _clean_readable_text(content)
    compact = re.sub(r"(?:^|\s)[-•]\s+", "; ", compact).strip(" ;")
    if len(compact) > max_chars:
        compact = compact[: max_chars - 3].rstrip(" ,;") + "..."
    return f"{label}: {compact}."


def _answer_specific_file_request(name: str, text: str, request: str) -> str | None:
    plain = _plain(request)
    if not plain:
        return None

    sections = _markdown_sections(text)

    if "nome do projeto" in plain or "qual o projeto" in plain or "qual era o projeto" in plain or "projeto do arquivo" in plain:
        return _answer_project_name_from_file(name, text, _topic_from_text(text))

    if any(phrase in plain for phrase in {"conceitos principais", "principais conceitos", "topicos principais", "tópicos principais"}):
        profile = _material_profile(text)
        topics = [str(topic) for topic in (profile.get("topics") or [])]
        keywords = [str(keyword) for keyword in (profile.get("keywords") or [])]
        concepts = list(dict.fromkeys([*topics, *keywords]))[:8]
        if concepts:
            return f"Conceitos principais em {name}: {', '.join(concepts)}."
        focus = _dedupe_focus(_focus_lines(text, limit=4), limit=4)
        if focus:
            return f"Conceitos principais em {name}: " + " ".join(focus[:3])

    section_queries = [
        ({"integrantes", "equipe", "membros", "autores"}, "Integrantes"),
        ({"tecnologias", "ferramentas", "stack", "linguagens"}, "Tecnologias utilizadas"),
        ({"executar", "rodar aplicacao", "rodar a aplicacao", "iniciar"}, "Como executar"),
        ({"rodar os testes", "testes", "testar"}, "Como rodar os testes"),
        ({"estrutura", "pastas", "arquivos"}, "Estrutura do projeto"),
        ({"principais classes", "classes", "interfaces"}, "Principais classes"),
        ({"regras", "filtragem"}, "Regras de filtragem"),
        ({"formula", "fórmula", "score", "pontuacao", "pontuação"}, "Fórmula de score"),
        ({"bugs", "corrigidos", "erros encontrados"}, "Bugs encontrados e corrigidos"),
        ({"status", "estado atual"}, "Status atual"),
        ({"cobertura", "jacoco"}, "Cobertura de testes"),
        ({"mockito", "mocks", "mockadas"}, "Uso de Mockito"),
        ({"diagramas", "diagrama"}, "Diagramas"),
    ]
    for keywords, label in section_queries:
        if any(keyword in plain for keyword in keywords):
            match = _section_by_keywords(sections, keywords)
            if match:
                return _short_section_answer(label, match[1])

    if "slogan" in plain:
        slogan_match = re.search(r"Slogan:\*\*\s*(.+?)(?:---|##|$)", text, flags=re.I | re.S)
        if slogan_match:
            return f"Slogan: {_clean_readable_text(slogan_match.group(1)).strip(' .')}."

    if any(phrase in plain for phrase in {"sobre o que", "o que tem", "do que se trata", "qual assunto"}):
        return None

    request_keywords = [token for token in re.findall(r"\w+", plain) if len(token) >= 4]
    best: tuple[int, str, str] | None = None
    for title, content in sections.items():
        haystack = _plain(f"{title} {content}")
        score = sum(1 for keyword in request_keywords if keyword in haystack)
        if score > 0 and (best is None or score > best[0]):
            best = (score, title, content)
    if best and best[0] >= max(1, min(2, len(request_keywords))):
        title = best[1].replace("_", " ").strip().capitalize()
        return _short_section_answer(title, best[2])

    technical_terms = (
        "protocolo",
        "tcp",
        "udp",
        "osi",
        "camadas",
        "rede",
        "redes",
        "ip",
        "pacotes",
        "roteador",
        "switch",
        "hardware",
        "software",
        "meios",
        "fisicos",
        "físicos",
    )
    asks_about_file = any(phrase in plain for phrase in {"nesse arquivo", "neste arquivo", "no arquivo", "tem algo sobre"})
    if asks_about_file or any(term in plain for term in technical_terms):
        technical_hits = [term.upper() if term in {"tcp", "udp", "osi", "ip"} else term for term in technical_terms if term in plain]
        topic_words = technical_hits or [
            token
            for token in request_keywords
            if token not in {"nesse", "neste", "arquivo", "qual", "diferenca", "diferença", "sobre", "algo", "entre"}
        ]
        subject = " ".join(topic_words[:4]) or "isso"
        return f"Não encontrei uma resposta clara sobre {subject} no trecho extraído de {name}."

    return None


def _content_subject_from_request(request: str) -> str:
    if _requested_page_number(request) is not None:
        return ""
    plain = _plain(request)
    patterns = (
        r"(?:fala|falam|trata|tratam|tem|cita|menciona)\s+(?:sobre\s+)?(.+?)(?:\?|$)",
        r"sobre\s+(.+?)(?:\?|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, plain)
        if not match:
            continue
        subject = match.group(1).strip(" .,:;!?")
        subject = re.sub(r"^(?:o|a|os|as|um|uma)\s+", "", subject)
        if subject and subject not in {
            "que",
            "o que",
            "arquivo",
            "esse arquivo",
            "nesse arquivo",
            "neste arquivo",
            "slide",
            "slides",
            "pdf",
            "esse pdf",
            "nesse pdf",
            "neste pdf",
            "documento",
            "esse documento",
            "nesse documento",
            "material",
            "esse material",
            "nesse material",
            "conteudo",
            "esse conteudo",
            "nesse conteudo",
        }:
            return subject
    return ""


def _requested_page_number(request: str, current_page_number: int | None = None) -> int | None:
    plain = _plain(request)
    digit_match = re.search(r"(?:pagina|pag|p)\s*(\d+)|(\d+)\s*(?:pagina|pag)", plain)
    if digit_match:
        return int(next(group for group in digit_match.groups() if group))

    number_words = {
        "primeira": 1,
        "primeiro": 1,
        "uma": 1,
        "um": 1,
        "segunda": 2,
        "segundo": 2,
        "duas": 2,
        "dois": 2,
        "terceira": 3,
        "terceiro": 3,
        "tres": 3,
        "quarta": 4,
        "quarto": 4,
        "quatro": 4,
        "quinta": 5,
        "quinto": 5,
        "cinco": 5,
        "sexta": 6,
        "sexto": 6,
        "seis": 6,
        "setima": 7,
        "setimo": 7,
        "sete": 7,
        "oitava": 8,
        "oitavo": 8,
        "oito": 8,
        "nona": 9,
        "nono": 9,
        "nove": 9,
        "decima": 10,
        "decimo": 10,
        "dez": 10,
    }
    for word, number in number_words.items():
        if re.search(rf"\b(?:pagina\s+{word}|{word}\s+pagina)\b", plain):
            return number
    current = int(current_page_number or 0)
    if current > 0:
        next_phrases = {
            "proxima pagina",
            "pagina proxima",
            "pagina seguinte",
            "seguinte pagina",
            "proximo slide",
            "slide seguinte",
            "e a proxima",
            "e a seguinte",
        }
        previous_phrases = {
            "pagina anterior",
            "anterior pagina",
            "slide anterior",
            "e a anterior",
        }
        if any(phrase in plain for phrase in next_phrases):
            return current + 1
        if any(phrase in plain for phrase in previous_phrases):
            return max(1, current - 1)
    return None


def _context_current_page_number(context: dict) -> int | None:
    try:
        stored = int(context.get("last_page_number") or 0)
    except Exception:
        stored = 0
    if stored > 0:
        return stored
    return _requested_page_number(str(context.get("request") or ""))


def _current_study_file_context(context: dict) -> dict:
    files = context.get("files") if isinstance(context, dict) else []
    if not isinstance(files, list) or not files:
        return {}
    clean_files = [item for item in files if isinstance(item, dict)]
    if not clean_files:
        return {}

    preferred_paths = [
        str(context.get("current_file_path") or "").strip(),
        str(context.get("last_file_path") or "").strip(),
    ]
    for preferred in [path for path in preferred_paths if path]:
        preferred_identity = _analysis_path_identity(preferred)
        for item in reversed(clean_files):
            item_identity = _analysis_path_identity(str(item.get("path") or ""))
            if item_identity and item_identity == preferred_identity:
                return item
    return clean_files[-1]


def current_study_context_matches_study_panel(context: dict | None = None, request: str = "") -> bool:
    if request_is_study_or_practice(request):
        return True
    if context is None:
        try:
            context = load_study_context()
        except Exception:
            context = {}
    first = _current_study_file_context(context or {})
    if not first:
        return False
    text = str(first.get("raw_text") or first.get("text") or "")
    return _looks_like_study_material(text)


def _remember_study_followup_response(
    context: dict,
    request: str,
    response: str,
    *,
    page_number: int | None = None,
) -> None:
    if not isinstance(context, dict):
        return
    updated = dict(context)
    updated["request"] = request
    updated["last_response"] = response
    if page_number is not None:
        updated["last_page_number"] = page_number
    try:
        save_study_context(updated)
    except Exception:
        pass


def _cached_study_followup_response(
    context: dict,
    request: str,
    *,
    current_page_number: int | None = None,
) -> str | None:
    if not isinstance(context, dict):
        return None
    if _requested_page_number(request) is None and _requested_page_number(request, current_page_number=current_page_number) is not None:
        return None
    if _plain(str(context.get("request") or "")) != _plain(request):
        return None
    cached = str(context.get("last_response") or "").strip()
    return cached or None


def _answer_content_subject(name: str, text: str, request: str, topic: str = "") -> str | None:
    subject = _content_subject_from_request(request)
    if not subject:
        return None
    text_plain = _plain(text)
    subject_plain = _plain(subject)
    if subject_plain and subject_plain in text_plain:
        return f"Sim. No {name}, encontrei menção a {subject}. O tema geral parece ser {topic or _topic_from_text(text) or 'o conteúdo extraído'}."
    return f"Não. No trecho extraído de {name}, não encontrei menção clara a {subject}. O material parece falar sobre {topic or _topic_from_text(text) or 'outro assunto'}."


def _answer_page_request(name: str, pages: list, request: str, current_page_number: int | None = None) -> str | None:
    number = _requested_page_number(request, current_page_number=current_page_number)
    if number is None:
        return None
    clean_pages = [page for page in pages if isinstance(page, dict)]
    for page in clean_pages:
        try:
            page_index = int(page.get("index") or 0)
        except Exception:
            continue
        if page_index == number:
            page_text = _clean_readable_text(str(page.get("text") or ""))
            if page_text:
                warning = _page_quality_warning(page_text)
                if warning and "parcial" in warning:
                    return (
                        f"Na página {number} de {name}, consigo ler parcialmente: {page_text[:700]}. "
                        "A extracao dessa pagina parece incompleta; use a leitura por imagem/OCR para confirmar todos os itens."
                    )
                return f"Na página {number} de {name}: {page_text[:700]}"
    if clean_pages:
        available = ", ".join(str(page.get("index")) for page in clean_pages[:6] if page.get("index"))
        return f"Não encontrei texto separado da página {number} em {name}. Páginas disponíveis no contexto: {available or 'nenhuma com texto'}."
    return f"Eu lembro do arquivo {name}, mas o texto salvo no contexto não veio separado por páginas. Para responder a página {number}, preciso reanalisar o PDF com extração por página."


def _format_file_type_answer(
    *,
    name: str,
    kind: str,
    suffix: str,
    topic: str,
    text: str,
    presentation_like: bool = False,
) -> str:
    topic_text = topic or "o conteudo extraido dele"
    kind_normalized = str(kind or "").lower()
    suffix_normalized = str(suffix or "").lower()
    looks_like_presentation = bool(presentation_like) or _looks_like_slide_deck_text(text)
    is_presentation = kind_normalized == "presentation" or suffix_normalized in {".ppt", ".pptx", ".odp"}
    if is_presentation:
        return f"{name}: sim, e uma apresentação/slide. O tema parece ser {topic_text}."
    if suffix_normalized == ".pdf" and looks_like_presentation:
        return (
            f"{name}: sim, o conteudo parece material em formato de slides ou aula. "
            f"Tecnicamente, o arquivo e um PDF, provavelmente exportado de uma apresentação. "
            f"O tema parece ser {topic_text}."
        )
    if suffix_normalized == ".pdf":
        return (
            f"{name}: e um PDF, nao um arquivo de slide nativo. "
            f"Ele pode ter sido exportado de slides, mas pelo conteudo extraido eu nao confirmaria formato de apresentação. "
            f"O tema parece ser {topic_text}."
        )
    if suffix_normalized in {".doc", ".docx"}:
        return f"{name}: e um documento de texto. O tema parece ser {topic_text}."
    return f"{name}: pelo conteudo, parece tratar de {topic_text}."


def _asks_for_file_type_answer(normalized: str) -> bool:
    content_intent_terms = {
        "fala sobre",
        "falas sobre",
        "fale sobre",
        "falam sobre",
        "trata de",
        "tratam de",
        "tem sobre",
        "menciona",
        "cita",
    }
    if any(term in normalized for term in content_intent_terms):
        return False

    asks_slide_identity = "slide" in normalized and any(
        phrase in normalized
        for phrase in {
            "e slide",
            "um slide",
            "e um slide",
            "isso e slide",
            "arquivo e slide",
            "formato de slide",
        }
    )
    file_reference_terms = {
        "arquivo",
        "documento",
        "material",
        "anexo",
        "pdf",
        "slide",
        "slides",
        "conteudo",
        "conteúdo",
        "apresentacao",
        "powerpoint",
        "pptx",
    }
    identity_question_terms = {
        "consegue ver",
        "voce ve",
        "isso e",
        "e um",
        "parece",
        "tipo",
        "formato",
    }
    return asks_slide_identity or (
        any(term in normalized for term in file_reference_terms)
        and any(term in normalized for term in identity_question_terms)
    )


def _should_answer_study_followup(normalized: str) -> bool:
    if not normalized:
        return False

    file_reference_terms = {
        "arquivo",
        "documento",
        "material",
        "anexo",
        "pdf",
        "slide",
        "slides",
        "apresentacao",
        "apresentação",
        "powerpoint",
        "pptx",
    }
    has_file_reference = any(term in normalized for term in file_reference_terms)

    if _requested_page_number(normalized) is not None:
        return True

    if (
        "nome do projeto" in normalized
        or "qual o projeto" in normalized
        or "qual era o projeto" in normalized
        or "projeto do arquivo" in normalized
    ):
        return True

    if has_file_reference:
        return True

    if re.search(r"(?:questao|questão|pergunta|exercicio|exercício)\s*\d+", normalized):
        return True

    if any(word in normalized for word in {"questoes", "questões", "exercicios", "exercícios", "quiz", "simulado", "arguir", "arguicao", "arguição"}):
        return True

    if any(phrase in normalized for phrase in {"conceitos principais", "principais conceitos", "topicos principais", "tópicos principais"}):
        return True

    if normalized in {"resuma", "resumir", "resumo", "explique", "explica", "analise", "analisar"}:
        return True

    if normalized in {"plano de estudo", "plano para estudar", "como estudar", "roteiro de estudo"}:
        return True

    blocked_general_domains = {
        "segundo plano",
        "carteira",
        "financeiro",
        "noticias",
        "notícias",
        "tela",
        "grafico",
        "gráfico",
        "codigo",
        "código",
        "interface",
        "hud",
        "volume",
        "musica",
        "música",
        "spotify",
    }
    if any(term in normalized for term in blocked_general_domains):
        return False

    technical_terms = {
        "protocolo",
        "tcp",
        "udp",
        "osi",
        "camadas",
        "rede",
        "redes",
        "ip",
        "pacotes",
        "roteador",
        "switch",
        "hardware",
        "software",
        "meios fisicos",
        "meios físicos",
    }
    if any(term in normalized for term in technical_terms) and ("?" in normalized or any(word in normalized for word in {"qual", "quais", "explique", "explica", "diferenca", "diferença"})):
        return True

    return False


def _answer_study_followup_raw(user_input: str) -> str | None:
    raw = _compact(user_input)
    normalized = _plain(raw)
    context = load_study_context()
    files = context.get("files") if isinstance(context, dict) else []
    if not isinstance(files, list) or not files:
        return None
    forced_study_followup = (
        ("conceit" in normalized and "principal" in normalized)
        or any(term in normalized for term in {"tcp", "udp", "osi", "protocolo", "camadas", "roteador", "switch"})
    )
    current_page_number = _context_current_page_number(context if isinstance(context, dict) else {})
    relative_page_followup = _requested_page_number(normalized, current_page_number=current_page_number) is not None
    if not _should_answer_study_followup(normalized) and not forced_study_followup and not relative_page_followup:
        return None

    cached_followup = _cached_study_followup_response(context, raw, current_page_number=current_page_number)
    if cached_followup:
        return cached_followup

    if (
        "nome do projeto" in normalized
        or "qual o projeto" in normalized
        or "qual era o projeto" in normalized
        or "projeto do arquivo" in normalized
    ):
        first = _current_study_file_context(context)
        name = str(first.get("name") or "arquivo")
        text = str(first.get("raw_text") or first.get("text") or "")
        answer = _answer_project_name_from_file(name, text, str(first.get("topic") or ""))
        _remember_study_followup_response(context, raw, answer)
        return answer

    first = _current_study_file_context(context)
    first_name = str(first.get("name") or "arquivo")
    first_text = str(first.get("raw_text") or first.get("text") or "")
    first_topic = str(first.get("topic") or "").strip()

    page_number = _requested_page_number(raw, current_page_number=current_page_number)
    page_answer = _answer_page_request(
        first_name,
        first.get("pages") if isinstance(first.get("pages"), list) else [],
        raw,
        current_page_number=current_page_number,
    )
    if page_answer:
        _remember_study_followup_response(context, raw, page_answer, page_number=page_number)
        return page_answer

    content_answer = _answer_content_subject(first_name, first_text, raw, first_topic)
    if content_answer:
        _remember_study_followup_response(context, raw, content_answer)
        return content_answer

    file_reference_terms = {
        "arquivo",
        "documento",
        "material",
        "anexo",
        "pdf",
        "slide",
        "slides",
        "conteudo",
        "conteúdo",
        "apresentacao",
        "apresentação",
        "powerpoint",
        "pptx",
    }
    identity_question_terms = {
        "consegue ver",
        "voce ve",
        "você vê",
        "isso e",
        "isso é",
        "e um",
        "é um",
        "parece",
        "tipo",
        "formato",
    }
    asks_if_slide = _asks_for_file_type_answer(normalized)
    if asks_if_slide or (
        any(term in normalized for term in file_reference_terms)
        and any(term in normalized for term in identity_question_terms)
    ):
        name = first_name
        kind = str(first.get("kind") or "").lower()
        suffix = Path(str(first.get("path") or name)).suffix.lower()
        topic = first_topic
        text = first_text
        presentation_like = bool(first.get("presentation_like")) or _looks_like_slide_deck_text(text)
        answer = _format_file_type_answer(
            name=name,
            kind=kind,
            suffix=suffix,
            topic=topic,
            text=text,
            presentation_like=presentation_like,
        )
        _remember_study_followup_response(context, raw, answer)
        return answer

    if "arquivo" in normalized or forced_study_followup or any(word in normalized for word in {"integrantes", "tecnologias", "executar", "testes", "bugs", "status", "slogan", "conceitos", "topicos", "tópicos", "protocolo", "tcp", "udp", "osi", "camadas", "rede", "redes"}):
        specific = _answer_specific_file_request(
            str(first.get("name") or "arquivo"),
            str(first.get("raw_text") or first.get("text") or ""),
            raw,
        )
        if specific:
            _remember_study_followup_response(context, raw, specific)
            return specific

    if any(phrase in normalized for phrase in {"sobre o que", "do que se trata", "qual o assunto", "que assunto"}):
        first = _current_study_file_context(context)
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

    if any(word in normalized for word in {"perguntar", "perguntas", "questoes", "questões", "exercicios", "exercícios", "arguir", "arguicao", "quiz", "simulado"}):
        first = _current_study_file_context(context)
        text = str(first.get("raw_text") or first.get("text") or "")
        questions = _practice_questions_from_material(text, limit=6)
        if questions:
            return "Perguntas para praticar:\n" + "\n".join(questions)

    if any(word in normalized for word in {"resumir", "resuma", "resumo"}):
        first = _current_study_file_context(context)
        name = str(first.get("name") or "arquivo")
        text = str(first.get("text") or "")
        focus = [str(item) for item in first.get("focus", [])] if isinstance(first.get("focus"), list) else []
        return " ".join(_summarize_material(name, text, focus, detailed=True))

    if any(word in normalized for word in {"plano", "revisao", "estudar"}):
        first = _current_study_file_context(context)
        name = str(first.get("name") or "arquivo")
        text = str(first.get("text") or "")
        return "\n".join(_study_plan(name, text))

    return None


def answer_study_followup(user_input: str) -> str | None:
    response = _answer_study_followup_raw(user_input)
    return polish_study_response(response) if response else None


def run_study_file_self_test(user_input: str) -> str | None:
    normalized = _plain(user_input)
    triggers = {
        "testar arquivo atual",
        "teste do arquivo atual",
        "testar leitura do arquivo",
        "rodar teste do arquivo",
        "rodar testes do arquivo",
        "rodar perguntas do arquivo",
        "fazer perguntas do arquivo",
        "perguntas automaticas do arquivo",
        "auto teste do arquivo",
        "autoteste do arquivo",
    }
    if not any(trigger in normalized for trigger in triggers):
        return None

    context = load_study_context()
    files = context.get("files") if isinstance(context, dict) else []
    if not isinstance(files, list) or not files:
        return "Ainda nao tenho um arquivo atual para testar. Analise um arquivo primeiro."

    first = _current_study_file_context(context)
    name = str(first.get("name") or "arquivo")
    text = str(first.get("raw_text") or first.get("text") or "")
    topic = str(first.get("topic") or _topic_from_text(text) or "conteudo extraido")
    pages = first.get("pages") if isinstance(first.get("pages"), list) else []
    kind = str(first.get("kind") or "")
    suffix = Path(str(first.get("path") or name)).suffix.lower()

    lines = [
        f"Auto teste do arquivo atual: {name}",
        f"Assunto provavel: {topic}.",
    ]
    lines.append(
        "Formato: "
        + _format_file_type_answer(
            name=name,
            kind=kind,
            suffix=suffix,
            topic=topic,
            text=text,
            presentation_like=bool(first.get("presentation_like")),
        )
    )

    if pages:
        lines.append("Paginas testadas:")
        for page in [page for page in pages if isinstance(page, dict)][:4]:
            page_index = str(page.get("index") or "?")
            page_text = _clean_readable_text(str(page.get("text") or ""))
            preview = page_text[:180] if page_text else "sem texto legivel"
            warning = _page_quality_warning(page_text)
            if warning:
                lines.append(f"- pagina {page_index}: ATENCAO - {warning}. Trecho: {preview}")
            else:
                lines.append(f"- pagina {page_index}: OK - {preview}")
    else:
        lines.append("Paginas testadas: o contexto atual nao trouxe texto separado por pagina.")

    negative = _answer_content_subject(name, text, "o arquivo fala sobre bananas?", topic)
    if negative:
        lines.append("Pergunta negativa: " + negative)

    concept = _answer_specific_file_request(name, text, "quais conceitos principais aparecem?")
    if concept:
        lines.append("Pergunta de conteudo: " + concept)

    return "\n".join(lines)


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


def _expand_analysis_paths(paths: list[str]) -> tuple[list[str], list[str]]:
    expanded: list[str] = []
    notes: list[str] = []
    for raw_path in paths:
        path = Path(str(raw_path).strip().strip('"')).expanduser()
        if path.is_dir():
            matches = [
                child
                for child in sorted(path.rglob("*"))
                if child.is_file() and child.suffix.lower() in SUPPORTED_STUDY_EXTENSIONS
            ]
            selected = matches[:MAX_FILES_PER_DIRECTORY_ANALYSIS]
            expanded.extend(str(child) for child in selected)
            if len(matches) > len(selected):
                notes.append(
                    f"{path.name}: encontrei {len(matches)} arquivos analisaveis; analisei os primeiros {len(selected)}."
                )
            elif selected:
                notes.append(f"{path.name}: analisei {len(selected)} arquivo(s) da pasta.")
            else:
                notes.append(f"{path.name}: nao encontrei arquivos analisaveis nessa pasta.")
            continue
        expanded.append(str(path))
    return expanded, notes


def _analysis_path_signature(path: str) -> dict:
    try:
        candidate = Path(path)
        stat = candidate.stat()
        return {"path": str(candidate), "size": int(stat.st_size), "mtime": round(float(stat.st_mtime), 3)}
    except Exception:
        return {"path": str(path), "size": 0, "mtime": 0.0}


def _analysis_path_identity(path: str) -> str:
    return _plain(str(path)).replace("\\", "/").rstrip("/")


def _analysis_signatures(paths: list[str]) -> list[dict]:
    return [_analysis_path_signature(path) for path in paths]


def _same_analysis_files(context: dict, paths: list[str]) -> bool:
    expected = _analysis_signatures(paths)
    stored = context.get("file_signatures") if isinstance(context, dict) else None
    if isinstance(stored, list) and stored:
        return stored == expected

    files = context.get("files") if isinstance(context, dict) else []
    if not isinstance(files, list) or len(files) != len(paths):
        return False
    stored_paths = [_analysis_path_identity(str(item.get("path") or "")) for item in files if isinstance(item, dict)]
    return stored_paths == [_analysis_path_identity(str(path)) for path in paths]


def _cached_analysis_response(paths: list[str], request: str) -> str | None:
    context = load_study_context()
    if not isinstance(context, dict) or not _same_analysis_files(context, paths):
        return None
    if int(context.get("analysis_cache_version") or 0) != STUDY_ANALYSIS_CACHE_VERSION:
        return None

    if _plain(str(context.get("request") or "")) == _plain(request):
        cached = str(context.get("last_response") or "").strip()
        if cached:
            return cached

    if _requested_page_number(request) is None:
        return None

    files = context.get("files") if isinstance(context.get("files"), list) else []
    sections: list[str] = []
    for index, file_context in enumerate(files, start=1):
        if not isinstance(file_context, dict):
            continue
        name = str(file_context.get("name") or "arquivo")
        pages = file_context.get("pages") if isinstance(file_context.get("pages"), list) else []
        page_answer = _answer_page_request(name, pages, request)
        if page_answer:
            sections.append(f"{index}. {page_answer}")
    if sections:
        has_study_material = any(
            _looks_like_study_material(str(item.get("raw_text") or item.get("text") or ""))
            for item in files
            if isinstance(item, dict)
        )
        header = "Analise de estudo dos arquivos:" if has_study_material else "Analise dos arquivos:"
        return polish_study_response("\n".join([header, *sections]))
    return None


def analyze_study_files(paths: list[str], request: str = "") -> str:
    clean_paths, path_notes = _expand_analysis_paths([str(path).strip().strip('"') for path in paths if str(path).strip()])
    if not clean_paths:
        return polish_study_response(
            "Me envie ou informe pelo menos um arquivo, ou diga o caminho de uma pasta com arquivos analisaveis."
        )

    cached = _cached_analysis_response(clean_paths, request)
    if cached:
        return cached

    sections = []
    all_focus: list[str] = []
    practice_questions: list[str] = []
    context_files: list[dict] = []
    failures = []
    has_study_material = request_is_study_or_practice(request)
    request_plain = _plain(request)

    for index, path in enumerate(clean_paths, start=1):
        result = process_file(path, max_chars=9000)
        file_info = result.get("file", {}) if isinstance(result, dict) else {}
        name = str(file_info.get("name") or Path(path).name)
        if not result.get("ok"):
            failures.append(f"{name}: {result.get('error', 'nao consegui ler')}")
            continue

        raw_text = _extract_text(result)
        text = _clean_readable_text(raw_text)
        if _study_text_is_untrusted(raw_text):
            sections.append(f"{index}. {name}: {_untrusted_extraction_message(result)}")
            continue

        focus = _focus_lines(text, limit=6)
        all_focus.extend(focus)
        question_sections = _question_sections(raw_text or text)
        has_study_material = has_study_material or _looks_like_study_material(raw_text or text)
        presentation_like = bool(_looks_like_slide_deck_text(raw_text or text))
        extracted = result.get("extracted", {}) if isinstance(result.get("extracted"), dict) else {}
        pages = extracted.get("pages", []) if isinstance(extracted.get("pages"), list) else []
        context_files.append(
            {
                "path": str(path),
                "name": name,
                "kind": str(file_info.get("kind") or ""),
                "presentation_like": presentation_like,
                "text": _compact(text)[:12000],
                "raw_text": str(raw_text or "")[:12000],
                "focus": focus,
                "pages": pages,
                "questions": {str(key): value for key, value in question_sections.items()},
                "topic": _topic_from_text(raw_text or text),
            }
        )
        if not focus:
            note = _extraction_note(result)
            if note:
                sections.append(f"{index}. {name}: {note}")
            else:
                fallback = (
                    "consegui abrir, mas nao encontrei texto suficiente para estudar."
                    if has_study_material
                    else "consegui abrir, mas nao encontrei texto suficiente para resumir."
                )
                sections.append(f"{index}. {name}: {fallback}")
            continue

        page_answer = _answer_page_request(name, pages, request)
        if page_answer:
            sections.append(f"{index}. {page_answer}")
            continue

        content_answer = _answer_content_subject(name, raw_text or text, request, _topic_from_text(raw_text or text))
        if content_answer:
            sections.append(f"{index}. {content_answer}")
            continue

        if _asks_for_file_type_answer(request_plain):
            sections.append(
                f"{index}. "
                + _format_file_type_answer(
                    name=name,
                    kind=str(file_info.get("kind") or ""),
                    suffix=Path(path).suffix.lower(),
                    topic=_topic_from_text(raw_text or text),
                    text=raw_text or text,
                    presentation_like=presentation_like,
                )
            )
            continue

        file_sections, file_questions = _format_study_file_response(name, raw_text or text, focus, request)
        if file_sections and file_sections[0].startswith("1. "):
            file_sections[0] = f"{index}. " + file_sections[0][3:]
        sections.extend(file_sections)
        practice_questions.extend(file_questions)

    if not sections and failures:
        return "Nao consegui analisar os arquivos. " + " ; ".join(failures[:3])

    response = ["Analise de estudo dos arquivos:" if has_study_material else "Analise dos arquivos:"]
    response.extend(sections)

    if failures:
        response.append("Arquivos com problema: " + " ; ".join(failures[:3]))
    if path_notes:
        response.extend(path_notes[:3])

    request_normalized = _plain(request)
    should_generate_questions = has_study_material and (not request_normalized or _study_request_kind(request) == "practice")
    question_count = 6 if len(all_focus) >= 6 else max(2, len(all_focus))
    questions = practice_questions or (_questions_from_lines(all_focus, limit=question_count) if should_generate_questions else [])
    if questions:
        response.append("Questoes para praticar:")
        response.extend(questions)
        response.append("Gabarito curto: responda com base nos pontos-chave acima; eu posso corrigir suas respostas depois.")

    final_response = polish_study_response("\n".join(response))
    if context_files:
        current_file_path = str(context_files[-1].get("path") or clean_paths[-1])
        save_study_context(
            {
                "source": "attached_files",
                "request": request,
                "analysis_cache_version": STUDY_ANALYSIS_CACHE_VERSION,
                "file_signatures": _analysis_signatures(clean_paths),
                "current_file_path": current_file_path,
                "last_file_path": current_file_path,
                "files": context_files,
                "last_response": final_response,
            }
        )

    return final_response
