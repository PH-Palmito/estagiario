from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SKILLS_DIR = Path("memory/skills")
MAX_SKILL_CHARS = 900


@dataclass(frozen=True)
class ProceduralSkill:
    name: str
    title: str
    triggers: tuple[str, ...]
    risks: tuple[str, ...]
    path: Path
    content: str


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _safe_skill_name(value: str, fallback: str = "procedimento") -> str:
    normalized = re.sub(r"[^a-z0-9_-]+", "-", str(value or "").strip().lower())
    normalized = re.sub(r"-+", "-", normalized).strip("-_")
    return normalized or fallback


def _skill_name_from_request(request: str) -> str:
    cleaned = str(request or "").lower()
    cleaned = re.sub(
        r"^(?:uma\s+)?(?:nova\s+)?skill\s+(?:para|de|sobre)?\s*",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(r"^(?:para|de|sobre)\s+", "", cleaned, flags=re.I)
    stopwords = {
        "uma",
        "com",
        "que",
        "para",
        "sobre",
        "fazer",
        "criar",
        "ajudar",
        "axel",
        "minha",
        "meu",
        "meus",
        "minhas",
    }
    words = [word for word in re.split(r"[^a-z0-9]+", cleaned) if len(word) >= 3 and word not in stopwords]
    return _safe_skill_name("-".join(words[:5]), fallback="procedimento")


def _skill_profile_from_request(request: str) -> dict:
    compact = _compact(request)
    lower = compact.lower()

    if any(term in lower for term in ("estud", "slide", "slides", "quest", "prova", "arquivo", "pdf", "pptx", "docx")):
        return {
            "name": "estudos",
            "title": "Skill Estudos",
            "toolset": "estudos",
            "agent": "study_agent",
            "triggers": [
                "resumir slides",
                "analisar arquivo de estudo",
                "gerar questoes sobre um tema",
                "gerar questoes a partir dos slides",
                "corrigir respostas e montar revisao",
            ],
            "procedure": [
                "Identificar o material de entrada: tema livre, PDF, PPTX, DOCX, TXT, imagem ou texto selecionado.",
                "Extrair ou pedir o conteudo necessario antes de responder; se o arquivo nao estiver acessivel, pedir o caminho.",
                "Resumir por slide, secao ou topico, preservando conceitos, definicoes, formulas e exemplos importantes.",
                "Gerar questoes em niveis facil, medio e dificil, com gabarito separado e explicacao curta.",
                "Quando o usuario responder, corrigir com feedback direto, apontar lacunas e sugerir revisao espaçada.",
                "Montar um plano de estudo curto com proximos passos, revisao e simulados quando o material for grande.",
            ],
            "risks": [
                "Nao inventar conteudo que nao esteja no arquivo ou no tema informado.",
                "Avisar quando o resumo depender de OCR, slides incompletos ou imagens ilegíveis.",
                "Separar resposta de gabarito quando o usuario quiser tentar resolver primeiro.",
            ],
            "examples": [
                "resuma esses slides para mim",
                "analise esse PDF e crie questoes",
                "faça perguntas sobre esse tema",
                "corrija minhas respostas",
            ],
        }

    name = _skill_name_from_request(compact)
    title = f"Skill {name.replace('-', ' ').title()}"
    return {
        "name": name,
        "title": title,
        "toolset": name,
        "agent": "general_agent",
        "triggers": [
            compact,
            f"usar skill {name}",
            f"procedimento de {name.replace('-', ' ')}",
        ],
        "procedure": [
            "Entender o objetivo do usuario e confirmar ambiguidades importantes antes de agir.",
            "Buscar contexto relevante em memoria, arquivos ou tela quando isso melhorar a resposta.",
            "Executar o procedimento em passos pequenos, mostrando resultado e proximos passos.",
            "Registrar aprendizados recorrentes para melhorar a skill depois.",
        ],
        "risks": [
            "Validar contexto atual antes de aplicar a skill.",
            "Confirmar antes de executar qualquer acao destrutiva, envio externo ou mudanca persistente.",
            "Nao transformar uma preferencia temporaria em regra permanente sem sinais repetidos.",
        ],
        "examples": [compact],
    }


def _tokens(text: str) -> set[str]:
    normalized = re.sub(r"[^\w\s/-]", " ", str(text or "").lower())
    return {token for token in normalized.split() if len(token) >= 3}


def _section_list(content: str, heading: str) -> tuple[str, ...]:
    pattern = rf"^##\s+{re.escape(heading)}\s*$"
    lines = str(content or "").splitlines()
    start = None
    for index, line in enumerate(lines):
        if re.match(pattern, line.strip(), flags=re.I):
            start = index + 1
            break
    if start is None:
        return ()

    items = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if stripped.startswith("- "):
            item = _compact(stripped[2:])
            if item:
                items.append(item)
    return tuple(items)


def _title_from_content(content: str, fallback: str) -> str:
    for line in str(content or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or fallback
    return fallback


def load_skills(skills_dir: Path | None = None) -> list[ProceduralSkill]:
    root = skills_dir or SKILLS_DIR
    if not root.exists():
        return []

    skills = []
    for path in sorted(root.glob("*/SKILL.md")):
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        name = path.parent.name
        skills.append(
            ProceduralSkill(
                name=name,
                title=_title_from_content(content, name),
                triggers=_section_list(content, "Gatilhos"),
                risks=_section_list(content, "Riscos"),
                path=path,
                content=content,
            )
        )
    return skills


def search_skills(query: str, limit: int = 3, *, skills_dir: Path | None = None) -> list[dict]:
    query_tokens = _tokens(query)
    if not query_tokens:
        return []

    scored = []
    for skill in load_skills(skills_dir):
        trigger_text = " ".join(skill.triggers)
        haystack = f"{skill.name} {skill.title} {trigger_text} {skill.content}"
        skill_tokens = _tokens(haystack)
        overlap = query_tokens & skill_tokens
        trigger_overlap = query_tokens & _tokens(trigger_text)
        if not overlap:
            continue
        score = len(overlap) + (len(trigger_overlap) * 2)
        scored.append(
            {
                "name": skill.name,
                "title": skill.title,
                "triggers": list(skill.triggers),
                "risks": list(skill.risks),
                "path": str(skill.path),
                "content": skill.content,
                "score": score,
                "matched_terms": sorted(overlap),
            }
        )

    scored.sort(key=lambda item: (int(item["score"]), item["title"]), reverse=True)
    return scored[: max(1, int(limit))]


def _skill_summary(content: str, max_chars: int = MAX_SKILL_CHARS) -> str:
    rows = []
    for raw_line in str(content or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            line = line.lstrip("#").strip()
        rows.append(line)
    summary = _compact(" ".join(rows))
    if len(summary) > max_chars:
        summary = summary[: max_chars - 3].rstrip() + "..."
    return summary


def format_relevant_skills(query: str, limit: int = 2) -> str:
    matches = search_skills(query, limit=limit)
    if not matches:
        return "Nenhuma skill procedural relevante encontrada."

    rows = []
    for item in matches:
        rows.append(f"{item['title']}: {_skill_summary(str(item.get('content', '')))}")
    return "Skills procedurais relevantes: " + " | ".join(rows)


def format_skill_catalog(skills_dir: Path | None = None) -> str:
    skills = load_skills(skills_dir)
    if not skills:
        return "Nenhuma skill procedural cadastrada."
    rows = [f"{skill.name}: {skill.title}" for skill in skills]
    return "Skills procedurais: " + " ; ".join(rows) + "."


def upsert_skill_from_suggestion(suggestion: dict, *, skills_dir: Path | None = None) -> Path:
    root = skills_dir or SKILLS_DIR
    skill_name = _safe_skill_name(suggestion.get("skill_name") or suggestion.get("toolset") or suggestion.get("agent") or suggestion.get("intent"))
    toolset = str(suggestion.get("toolset") or "").strip()
    agent = str(suggestion.get("agent") or "").strip()
    intent = str(suggestion.get("intent") or "").strip()
    examples = [str(item).strip() for item in suggestion.get("examples", []) if str(item).strip()]
    title = f"Skill {skill_name.replace('-', ' ').title()}"
    skill_dir = root / skill_name
    path = skill_dir / "SKILL.md"
    skill_dir.mkdir(parents=True, exist_ok=True)

    trigger_rows = examples[:5] or [intent or skill_name]
    content = [
        f"# {title}",
        "",
        "## Gatilhos",
        *[f"- {item}" for item in trigger_rows],
        "",
        "## Procedimento",
        f"- Usar o agente `{agent or 'indefinido'}` e o toolset `{toolset or 'indefinido'}` como ponto de partida.",
        "- Reaproveitar exemplos recentes antes de criar um fluxo novo.",
        "- Confirmar antes de executar qualquer acao destrutiva, envio externo ou mudanca persistente.",
        "",
        "## Riscos",
        "- Padrao aprendido automaticamente pode precisar de revisao humana.",
        "- Validar contexto atual antes de aplicar o procedimento.",
        "",
        "## Exemplos recentes",
        *[f"- {item}" for item in examples[:5]],
        "",
    ]
    path.write_text("\n".join(content), encoding="utf-8")
    return path


def create_skill_from_request(request: str, *, skills_dir: Path | None = None) -> Path:
    compact = _compact(request)
    if len(compact) < 8:
        raise ValueError("Pedido curto demais para criar uma skill.")

    root = skills_dir or SKILLS_DIR
    profile = _skill_profile_from_request(compact)
    skill_name = _safe_skill_name(profile["name"])
    skill_dir = root / skill_name
    path = skill_dir / "SKILL.md"
    skill_dir.mkdir(parents=True, exist_ok=True)

    content = [
        f"# {profile['title']}",
        "",
        "## Gatilhos",
        *[f"- {item}" for item in profile["triggers"]],
        "",
        "## Procedimento",
        *[f"- {item}" for item in profile["procedure"]],
        "",
        "## Riscos",
        *[f"- {item}" for item in profile["risks"]],
        "",
        "## Exemplos recentes",
        *[f"- {item}" for item in profile["examples"]],
        "",
        "## Origem",
        f"- Criada por comando natural: {compact}",
        f"- Agente sugerido: `{profile['agent']}`",
        f"- Toolset sugerido: `{profile['toolset']}`",
        "",
    ]
    path.write_text("\n".join(content), encoding="utf-8")
    return path
