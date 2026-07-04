from __future__ import annotations

import re

from core.agent_tool_library import tool_library_for_agent
from core.response_polish import polish_assistant_response
from core.router_utils import normalize_text
from memory.procedural_skills import ProceduralSkill, load_skills, search_skills


SKILL_BINDINGS = {
    "briefing": ("system_agent", "briefing", ("briefing", "agenda", "weather", "investments")),
    "carteira": ("investment_agent", "carteira", ("investments", "web")),
    "estudos": ("study_agent", "estudos", ("study", "files")),
    "navegacao": ("browser_agent", "navegador", ("browser", "web")),
    "programacao": ("dev_agent", "programacao", ("code", "files")),
    "sistema": ("system_agent", "sistema", ("telegram", "system")),
    "visao": ("browser_agent", "visao", ("vision",)),
    "voz": ("voice_agent", "voz_rapida", ("conversation", "system", "media")),
}

ROUTING_STOPWORDS = {
    "a",
    "ao",
    "aos",
    "as",
    "com",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "esse",
    "essa",
    "meu",
    "meus",
    "minha",
    "minhas",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "para",
    "por",
    "que",
    "sobre",
    "um",
    "uma",
}


def _section_list(content: str, heading: str) -> list[str]:
    pattern = rf"^##\s+{re.escape(heading)}\s*$"
    lines = str(content or "").splitlines()
    start = None
    for index, line in enumerate(lines):
        if re.match(pattern, line.strip(), flags=re.I):
            start = index + 1
            break
    if start is None:
        return []
    items = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if stripped.startswith("- "):
            items.append(re.sub(r"\s+", " ", stripped[2:]).strip())
    return [item for item in items if item]


def _origin_value(content: str, label: str) -> str:
    pattern = rf"^-\s+{re.escape(label)}:\s+`?(?P<value>[^`\n]+)`?\s*$"
    for line in str(content or "").splitlines():
        match = re.match(pattern, line.strip(), flags=re.I)
        if match:
            return match.group("value").strip()
    return ""


def _find_skill(name_or_query: str) -> ProceduralSkill | None:
    normalized = str(name_or_query or "").strip().lower()
    if not normalized:
        return None
    skills = load_skills()
    for skill in skills:
        if normalized in {skill.name.lower(), skill.title.lower()}:
            return skill
    matches = search_skills(name_or_query, limit=1)
    if not matches:
        return None
    match_name = str(matches[0].get("name") or "").lower()
    return next((skill for skill in skills if skill.name.lower() == match_name), None)


def _skill_origin(skill: ProceduralSkill) -> tuple[str, str]:
    agent = _origin_value(skill.content, "Agente sugerido")
    toolset = _origin_value(skill.content, "Toolset sugerido")
    binding = SKILL_BINDINGS.get(skill.name)
    if binding:
        agent = agent or binding[0]
        toolset = toolset or binding[1]
    return agent or "general_agent", toolset or skill.name


def _actions_for_skill(skill: ProceduralSkill) -> list[dict]:
    agent, _toolset = _skill_origin(skill)
    actions = list(tool_library_for_agent(agent, limit=500).get("actions") or [])
    binding = SKILL_BINDINGS.get(skill.name)
    if not binding:
        return actions
    categories = binding[2]
    category_order = {category: index for index, category in enumerate(categories)}
    related = [item for item in actions if str(item.get("category") or "") in category_order]
    return sorted(
        related,
        key=lambda item: (
            category_order[str(item.get("category") or "")],
            str(item.get("name") or ""),
        ),
    )


def _examples_for_skill(skill: ProceduralSkill) -> list[str]:
    return _section_list(skill.content, "Exemplos recentes") or _section_list(skill.content, "Comandos relacionados")


def _readiness_for_skill(skill: ProceduralSkill) -> tuple[str, str]:
    triggers = list(skill.triggers or [])
    examples = _examples_for_skill(skill)
    actions = _actions_for_skill(skill)
    validated_examples, total_examples = _validated_examples(skill)
    if triggers and examples and actions and validated_examples == total_examples:
        return "pronta", f"tem gatilhos, {validated_examples}/{total_examples} exemplos roteados e actions relacionadas"
    if triggers and (examples or actions):
        return "parcial", f"tem gatilhos, mas apenas {validated_examples}/{total_examples} exemplos roteados ou falta action ligada"
    return "documentada", "existe como procedimento, mas ainda precisa de gatilhos, exemplos e actions"


def match_actionable_skill(query: str) -> dict | None:
    normalized_query = normalize_text(query)
    query_tokens = {token for token in normalized_query.split() if token not in ROUTING_STOPWORDS}
    if not query_tokens:
        return None
    candidates = []
    for skill in load_skills():
        binding = SKILL_BINDINGS.get(skill.name)
        if not binding:
            continue
        best_score = 0
        matched_trigger = ""
        for trigger in skill.triggers:
            normalized_trigger = normalize_text(trigger)
            trigger_tokens = {token for token in normalized_trigger.split() if token not in ROUTING_STOPWORDS}
            overlap = query_tokens & trigger_tokens
            exact = bool(normalized_trigger and normalized_trigger in normalized_query)
            score = (10 if exact else 0) + (len(overlap) * 3)
            if score > best_score:
                best_score = score
                matched_trigger = trigger
        if best_score <= 0:
            continue
        agent, toolset = _skill_origin(skill)
        candidates.append(
            {
                "name": skill.name,
                "agent": agent,
                "toolset": toolset,
                "score": best_score,
                "matched_trigger": matched_trigger,
            }
        )
    candidates.sort(key=lambda item: (int(item["score"]), str(item["name"])), reverse=True)
    return candidates[0] if candidates else None


def _validated_examples(skill: ProceduralSkill) -> tuple[int, int]:
    examples = _examples_for_skill(skill)
    validated = 0
    for example in examples:
        match = match_actionable_skill(example)
        if match and str(match.get("name") or "") == skill.name:
            validated += 1
    return validated, len(examples)


def format_actionable_skills_overview() -> str:
    skills = load_skills()
    if not skills:
        return "Nenhuma skill procedural cadastrada."
    rows = []
    for skill in skills:
        readiness, reason = _readiness_for_skill(skill)
        agent, toolset = _skill_origin(skill)
        rows.append(f"{skill.name}: {readiness}, agente {agent}, toolset {toolset}, {reason}")
    return polish_assistant_response("Skills acionaveis do Axel: " + " | ".join(rows) + ".")


def format_actionable_skill_detail(name_or_query: str) -> str:
    skill = _find_skill(name_or_query)
    if not skill:
        return polish_assistant_response("Nao encontrei essa skill. Use `skills acionaveis` para ver as disponiveis.")
    readiness, reason = _readiness_for_skill(skill)
    agent, toolset = _skill_origin(skill)
    triggers = ", ".join(item.rstrip(" .;") for item in skill.triggers[:6]) or "sem gatilhos"
    examples = ", ".join(item.rstrip(" .;") for item in _examples_for_skill(skill)[:5]) or "sem exemplos testaveis"
    validated_examples, total_examples = _validated_examples(skill)
    risks = ", ".join(item.rstrip(" .;") for item in skill.risks[:4]) or "sem riscos registrados"
    actions = _actions_for_skill(skill)
    action_names = ", ".join(str(item.get("name") or "") for item in actions[:8]) or "sem actions relacionadas"
    return polish_assistant_response(
        f"Skill {skill.name}: status {readiness}. Motivo: {reason}. "
        f"Agente: {agent}. Toolset: {toolset}. Gatilhos: {triggers}. "
        f"Exemplos testaveis: {examples}. Exemplos validados: {validated_examples}/{total_examples} chegaram a propria skill. "
        f"Actions relacionadas: {action_names}. "
        f"Riscos: {risks}. Arquivo: {skill.path}."
    )
