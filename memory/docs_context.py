from __future__ import annotations

import re
import unicodedata
from pathlib import Path


DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
DOC_HINTS = {
    "plano",
    "planejamento",
    "roadmap",
    "fase",
    "fases",
    "proximo passo",
    "proximos passos",
    "próximo passo",
    "próximos passos",
    "falta",
    "faltam",
    "status",
    "memoria",
    "memória",
    "obsidian",
    "supabase",
    "arquitetura",
    "openclaw",
    "paperclip",
    "evolucao",
    "evolução",
}


def _normalize(text: str) -> str:
    text = str(text or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _strip_frontmatter(content: str) -> str:
    text = str(content or "")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip()
    return text


def _read_doc(path: Path) -> dict | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return None
    body = _strip_frontmatter(raw)
    title = ""
    for line in body.splitlines():
        clean = line.strip()
        if clean.startswith("# "):
            title = clean[2:].strip()
            break
    return {
        "name": path.stem,
        "title": title or path.stem,
        "content": body,
    }


def _score_doc(query: str, title: str, content: str) -> int:
    normalized_query = _normalize(query)
    normalized_title = _normalize(title)
    normalized_content = _normalize(content)
    if not normalized_query:
        return 0

    score = 0
    for token in normalized_query.split():
        if len(token) < 3:
            continue
        if token in normalized_title:
            score += 8
        if token in normalized_content:
            score += 3
    return score


def docs_context_relevant(user_input: str) -> bool:
    normalized = _normalize(user_input)
    normalized_hints = {_normalize(item) for item in DOC_HINTS}
    if any(hint in normalized for hint in normalized_hints):
        return True
    if re.search(r"\bpr\s*ximo[s]?\s+passo[s]?\b", normalized):
        return True
    return False


def search_docs_context(query: str, limit: int = 2, max_chars: int = 420) -> list[dict]:
    if not DOCS_DIR.exists():
        return []

    matches: list[tuple[int, dict]] = []
    for path in DOCS_DIR.glob("*.md"):
        doc = _read_doc(path)
        if not doc:
            continue
        score = _score_doc(query, doc["title"], doc["content"])
        if score <= 0:
            continue

        excerpt = re.sub(r"\s+", " ", doc["content"]).strip()
        if len(excerpt) > max_chars:
            excerpt = excerpt[: max_chars - 3].rstrip() + "..."
        matches.append(
            (
                score,
                {
                    "name": doc["name"],
                    "title": doc["title"],
                    "excerpt": excerpt,
                    "path": str(path),
                },
            )
        )

    matches.sort(key=lambda item: item[0], reverse=True)
    return [item for _score, item in matches[:limit]]


def _roadmap_content() -> str:
    path = DOCS_DIR / "axel-evolution-roadmap.md"
    doc = _read_doc(path)
    return str((doc or {}).get("content", ""))


def _extract_phase_headings() -> list[str]:
    content = _roadmap_content()
    return re.findall(r"^##\s+Fase\s+\d+:\s+(.+)$", content, flags=re.MULTILINE)


def _extract_priority_list() -> list[str]:
    content = _roadmap_content()
    block_match = re.search(r"### Prioridade real(.*?)### Motivo", content, flags=re.S | re.I)
    if not block_match:
        return []
    return re.findall(r"^\d+\.\s+(.+)$", block_match.group(1), flags=re.MULTILINE)


def _extract_backlog_items() -> list[str]:
    content = _roadmap_content()
    block_match = re.search(r"## Backlog inicial sugerido(.*)", content, flags=re.S | re.I)
    if not block_match:
        return []
    return re.findall(r"^- (.+)$", block_match.group(1), flags=re.MULTILINE)


def docs_plan_answer(user_input: str) -> str | None:
    normalized = _normalize(user_input)
    if not docs_context_relevant(user_input):
        return None

    phases = _extract_phase_headings()
    priority = _extract_priority_list()
    backlog = _extract_backlog_items()

    if any(term in normalized for term in {"qual o plano", "qual e o plano", "plano do axel", "roadmap"}):
        phase_text = ", ".join(phases[:4]) if phases else "base confiável, conversa, pesquisa e investimentos"
        return (
            f"O plano do Axel hoje segue uma trilha em fases: {phase_text}. "
            "A ideia é evoluir primeiro conversa e opinião, depois pesquisa com fundamento, investimentos e persistência mais forte."
        )

    if any(term in normalized for term in {"em que fase estamos", "qual a fase", "fase atual"}):
        current = priority[0] if priority else "Fase 2"
        return (
            f"Pelo roadmap, a frente prioritária agora é {current}. "
            "Na prática, isso significa deixar o Axel conversar melhor, sustentar contexto e dar opiniões mais úteis."
        )

    if any(term in normalized for term in {"o que falta", "o que falta fazer", "faltam", "falta fazer"}):
        items = "; ".join(backlog[:4]) if backlog else "reforçar memória, melhorar pesquisa e evoluir investimentos"
        return f"O que ainda falta, no curto prazo, é isto: {items}."

    mentions_next_step = any(
        term in normalized for term in {"proximo passo", "proximos passos"}
    ) or bool(re.search(r"\bpr\s*ximo[s]?\s+passo[s]?\b", normalized))

    if mentions_next_step:
        next_step = backlog[0] if backlog else "reforçar memória de conversa e resposta opinativa"
        return f"O próximo passo mais coerente no roadmap é {next_step}."

    if any(term in normalized for term in {"supabase", "obsidian", "arquitetura", "openclaw", "paperclip"}):
        matches = search_docs_context(user_input, limit=1, max_chars=260)
        if matches:
            return f"No material de arquitetura, o ponto central é este: {matches[0]['excerpt']}"

    return None
