from __future__ import annotations

from dataclasses import asdict, dataclass

from core.decision_orchestrator import DecisionPlan, build_decision_plan
from core.router_registry import INTENT_LEVEL_CONVERSATION, INTENT_LEVEL_QUESTION
from core.specialist_agents import select_agents
from core.toolsets import format_relevant_toolsets
from memory.curated_memory import format_curated_memory
from memory.deep_memory import explain_memory_influence
from memory.procedural_skills import format_relevant_skills
from memory.session_index import format_relevant_session_memory


@dataclass(frozen=True)
class MemoryLayer:
    name: str
    priority: int
    content: str
    sources: tuple[str, ...] = ()
    influences: tuple[dict, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SpecialistBrief:
    agent: str
    toolset: str
    mission: str
    model_policy: str
    handoff_rules: tuple[str, ...]
    handoff_chain: tuple[dict, ...]
    coordination_mode: str
    tool_libraries: tuple[dict, ...]
    context: str
    memory_layers: tuple[MemoryLayer, ...]
    next_step: str
    success_criteria: tuple[str, ...]
    post_task_signals: tuple[str, ...]
    brain_version: str = "2.0"

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["memory_layers"] = [layer.to_dict() for layer in self.memory_layers]
        return payload


@dataclass(frozen=True)
class AxelBrainDecision:
    plan: DecisionPlan
    brief: SpecialistBrief

    def to_dict(self) -> dict:
        return {
            "plan": self.plan.to_dict(),
            "brief": self.brief.to_dict(),
        }


def _memory_layers(user_input: str) -> tuple[MemoryLayer, ...]:
    return (
        MemoryLayer("memoria_curta", 1, format_curated_memory()),
        MemoryLayer("sessoes_relevantes", 2, format_relevant_session_memory(user_input)),
        _deep_memory_layer(user_input),
        MemoryLayer("skills_procedurais", 4, format_relevant_skills(user_input)),
        MemoryLayer("toolsets_relevantes", 5, format_relevant_toolsets(user_input)),
    )


def _deep_memory_layer(user_input: str) -> MemoryLayer:
    explanation = explain_memory_influence(user_input, limit=4)
    items = [item for item in explanation.get("items") or [] if isinstance(item, dict)]
    conflicts = [item for item in explanation.get("conflicts") or [] if isinstance(item, dict)]
    influences = []
    sources = []
    rows = []

    for item in items[:4]:
        meta = item.get("metadados") if isinstance(item.get("metadados"), dict) else {}
        source = str(meta.get("origem") or "").strip()
        if source and source not in sources:
            sources.append(source)
        influence = {
            "id": str(item.get("id") or ""),
            "domain": str(item.get("dominio") or ""),
            "section": str(item.get("secao") or ""),
            "source": source,
            "scope": str(meta.get("escopo") or ""),
            "confidence": meta.get("confianca"),
            "priority": str(meta.get("prioridade") or ""),
            "reason": str(meta.get("motivo") or "")[:180],
            "text": str(item.get("texto") or "")[:180],
        }
        influences.append(influence)
        rows.append(
            f"{influence['domain']}/{influence['section']}: {influence['text']} "
            f"(origem {source or 'sem origem'}, conf {influence['confidence']})"
        )

    if conflicts:
        rows.append(f"conflitos sinalizados: {len(conflicts)}")
    content = "Memoria profunda relevante: " + " ; ".join(rows) + "." if rows else "Memoria profunda: nenhum item especifico relevante."
    return MemoryLayer(
        "memoria_profunda",
        3,
        content,
        sources=tuple(sources[:6]),
        influences=tuple(influences[:4]),
    )


def _next_step_for_plan(plan: DecisionPlan) -> str:
    if plan.decision_type == "CLARIFICATION":
        return "Pedir esclarecimento objetivo antes de escolher capability ou executar."
    if plan.decision_type == "PLANNING":
        return "Planejar primeiro; nao executar etapas automaticamente."
    if plan.decision_type == "UNKNOWN":
        return "Explicar limite e pedir reformulacao ou contexto minimo."
    if plan.decision_type == "INFORMATION":
        return "Responder ou pesquisar usando fontes e memoria relevantes sem acao de sistema."
    if plan.needs_confirmation:
        return "Pedir confirmacao antes de executar a acao."
    if plan.response_mode == "plan_then_execute":
        return "Criar ou atualizar plano de execucao antes de agir."
    if plan.response_mode == "answer_with_context":
        return "Responder usando as camadas de memoria e fontes relevantes."
    if plan.response_mode == "execute_short":
        return "Executar comando local com feedback curto."
    return "Responder de forma curta e manter continuidade da conversa."


def _success_criteria(plan: DecisionPlan) -> tuple[str, ...]:
    base = [
        "resposta curta e coerente com o pedido",
        "contexto relevante usado sem poluir a fala final",
    ]
    if plan.decision_type in {"CLARIFICATION", "UNKNOWN"}:
        base.append("nenhuma action inventada para cobrir incerteza")
    if plan.decision_type == "PLANNING":
        base.append("plano separado de execucao")
    if plan.response_mode == "execute_short":
        base.append("acao executada ou erro explicado")
    if plan.needs_confirmation:
        base.append("confirmacao preserva acao e parametros originais")
    if plan.coordination_mode == "multi_agent_handoff":
        base.append("handoff entre agentes mantem objetivo unico")
    return tuple(base)


def _post_task_signals(plan: DecisionPlan) -> tuple[str, ...]:
    signals = [
        "registrar sucesso, falha ou ajuste na autoavaliacao",
        "observar se o padrao deve virar skill procedural",
    ]
    if plan.decision_type in {"UNKNOWN", "CLARIFICATION"}:
        signals.append("observar se o fallback precisa virar capability ou detector")
    if plan.risk_level in {"high", "critical"}:
        signals.append("registrar auditoria da acao sensivel")
    if plan.model_policy != "local_first":
        signals.append("registrar provedor de modelo, fallback e latencia")
    return tuple(signals)


def build_specialist_brief(user_input: str, plan: DecisionPlan) -> SpecialistBrief:
    matches = select_agents(user_input, toolset=plan.toolset, limit=1)
    agent = matches[0] if matches else {}
    mission = str(agent.get("mission") or "Executar a tarefa com seguranca e contexto.")
    rules = tuple(str(rule) for rule in (agent.get("handoff_rules") or []) if str(rule).strip())
    layers = _memory_layers(user_input)
    context = "\n".join(layer.content for layer in layers)
    return SpecialistBrief(
        agent=plan.agent,
        toolset=plan.toolset,
        mission=mission,
        model_policy=plan.model_policy,
        handoff_rules=rules,
        handoff_chain=tuple(plan.handoff_chain),
        coordination_mode=plan.coordination_mode,
        tool_libraries=tuple(plan.tool_libraries),
        context=context,
        memory_layers=layers,
        next_step=_next_step_for_plan(plan),
        success_criteria=_success_criteria(plan),
        post_task_signals=_post_task_signals(plan),
    )


def build_axel_brain_decision(
    user_input: str,
    raw_action: dict | None,
    *,
    intent_level: str,
    complexity_kind: str = "",
) -> AxelBrainDecision:
    plan = build_decision_plan(
        user_input,
        raw_action,
        intent_level=intent_level,
        complexity_kind=complexity_kind,
    )
    return AxelBrainDecision(
        plan=plan,
        brief=build_specialist_brief(user_input, plan),
    )


def format_specialist_brief(user_input: str, raw_action: dict | None, *, intent_level: str, complexity_kind: str = "") -> str:
    decision = build_axel_brain_decision(
        user_input,
        raw_action,
        intent_level=intent_level,
        complexity_kind=complexity_kind,
    )
    brief = decision.brief
    rules = "; ".join(brief.handoff_rules[:3]) if brief.handoff_rules else "sem regras especificas"
    handoff = ""
    if brief.coordination_mode == "multi_agent_handoff" and brief.handoff_chain:
        chain = " -> ".join(str(item.get("agent", "--")) for item in brief.handoff_chain[:4])
        handoff = f" Handoff: {chain}."
    tools = ""
    if brief.tool_libraries:
        first = brief.tool_libraries[0]
        actions = first.get("actions") or []
        names = ", ".join(str(item.get("name")) for item in actions[:4] if isinstance(item, dict))
        if names:
            tools = f" Ferramentas: {names}."
    next_step = f" Proximo passo: {brief.next_step}"
    return (
        f"AxelBrain escolheu {brief.agent} com toolset {brief.toolset}. "
        f"Missao: {brief.mission} Regras: {rules}. Politica de modelo: {brief.model_policy}.{handoff}{tools}{next_step}"
    )


def format_conversation_brief(user_input: str, *, complex_request: bool = False) -> str:
    intent_level = INTENT_LEVEL_QUESTION if complex_request else INTENT_LEVEL_CONVERSATION
    complexity_kind = "complex_reasoning" if complex_request else "simple_conversation"
    return format_specialist_brief(
        user_input,
        {"intent": "respond", "target": None},
        intent_level=intent_level,
        complexity_kind=complexity_kind,
    )
