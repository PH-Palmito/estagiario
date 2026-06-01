from __future__ import annotations

from dataclasses import asdict, dataclass

from core.decision_orchestrator import DecisionPlan, build_decision_plan
from core.router_registry import INTENT_LEVEL_CONVERSATION, INTENT_LEVEL_QUESTION
from core.specialist_agents import select_agents
from core.toolsets import format_relevant_toolsets
from memory.curated_memory import format_curated_memory
from memory.procedural_skills import format_relevant_skills
from memory.session_index import format_relevant_session_memory


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

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AxelBrainDecision:
    plan: DecisionPlan
    brief: SpecialistBrief

    def to_dict(self) -> dict:
        return {
            "plan": self.plan.to_dict(),
            "brief": self.brief.to_dict(),
        }


def build_specialist_brief(user_input: str, plan: DecisionPlan) -> SpecialistBrief:
    matches = select_agents(user_input, toolset=plan.toolset, limit=1)
    agent = matches[0] if matches else {}
    mission = str(agent.get("mission") or "Executar a tarefa com seguranca e contexto.")
    rules = tuple(str(rule) for rule in (agent.get("handoff_rules") or []) if str(rule).strip())
    context = "\n".join(
        [
            format_curated_memory(),
            format_relevant_session_memory(user_input),
            format_relevant_skills(user_input),
            format_relevant_toolsets(user_input),
        ]
    )
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
    return (
        f"AxelBrain escolheu {brief.agent} com toolset {brief.toolset}. "
        f"Missao: {brief.mission} Regras: {rules}. Politica de modelo: {brief.model_policy}.{handoff}{tools}"
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
