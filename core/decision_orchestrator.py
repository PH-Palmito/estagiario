from __future__ import annotations

from dataclasses import asdict, dataclass

from core.agent_tool_library import tool_library_for_chain
from core.multi_agent_handoff import build_handoff_chain, handoff_needed
from core.router_registry import (
    INTENT_LEVEL_COMPOSITE_TASK,
    INTENT_LEVEL_CONVERSATION,
    INTENT_LEVEL_DIRECT_COMMAND,
    INTENT_LEVEL_QUESTION,
)
from core.skill_operations import match_actionable_skill
from core.specialist_agents import agent_for_toolset, find_agent, select_agents
from core.toolsets import select_toolsets

HIGH_RISK_INTENTS = {
    "close_app",
    "smart_close_app",
    "type_text",
    "run_script",
    "run_macro",
    "browser_click_text",
    "browser_click_center",
    "browser_click_listed_item",
    "investment_add_watchlist",
    "investment_remove_watchlist",
    "investment_set_price_ceiling",
    "investment_set_auto_ceiling_margin",
    "investment_set_thesis",
}
CRITICAL_INTENTS = {
    "file_delete",
    "file_move",
    "file_rename",
    "file_replace",
    "file_write",
    "memory.backup.restore_file",
    "windows_startup_enable",
    "windows_startup_disable",
}


@dataclass(frozen=True)
class DecisionPlan:
    intent: str
    intent_level: str
    confidence: float
    toolset: str
    agent: str
    risk_level: str
    needs_confirmation: bool
    response_mode: str
    model_policy: str
    reason: str
    handoff_chain: tuple[dict, ...] = ()
    coordination_mode: str = "single_agent"
    tool_libraries: tuple[dict, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


def _risk_for_intent(intent: str, intent_level: str) -> str:
    normalized = str(intent or "").strip()
    if normalized in CRITICAL_INTENTS:
        return "critical"
    if normalized in HIGH_RISK_INTENTS:
        return "high"
    if intent_level == INTENT_LEVEL_DIRECT_COMMAND:
        return "low"
    if intent_level in {INTENT_LEVEL_QUESTION, INTENT_LEVEL_CONVERSATION}:
        return "read"
    return "medium"


def _fallback_toolset(intent: str, intent_level: str) -> tuple[str, str]:
    normalized = str(intent or "").strip().lower()
    if "investment" in normalized or "wallet" in normalized:
        return "carteira", "grounded_cloud_when_current"
    if "browser" in normalized or "site" in normalized:
        return "navegador", "local_for_commands_cloud_for_summary"
    if "file" in normalized or "code" in normalized:
        return "programacao", "nvidia_or_gemini_for_reasoning"
    if intent_level == INTENT_LEVEL_DIRECT_COMMAND:
        return "sistema", "local_first"
    if intent_level == INTENT_LEVEL_QUESTION:
        return "pesquisa", "cloud_with_sources"
    return "voz_rapida", "local_first"


def _response_mode(intent_level: str, risk_level: str) -> str:
    if risk_level in {"high", "critical"}:
        return "confirm_then_act"
    if intent_level == INTENT_LEVEL_DIRECT_COMMAND:
        return "execute_short"
    if intent_level == INTENT_LEVEL_COMPOSITE_TASK:
        return "plan_then_execute"
    if intent_level == INTENT_LEVEL_QUESTION:
        return "answer_with_context"
    return "conversational"


def build_decision_plan(
    user_input: str,
    raw_action: dict | None,
    *,
    intent_level: str,
    complexity_kind: str = "",
) -> DecisionPlan:
    action = raw_action or {}
    intent = str(action.get("intent") or "respond").strip() or "respond"
    level = str(intent_level or INTENT_LEVEL_CONVERSATION).strip() or INTENT_LEVEL_CONVERSATION
    skill_match = match_actionable_skill(user_input) if intent == "respond" else None
    selected = select_toolsets(f"{user_input} {intent}", limit=1)
    if skill_match:
        toolset = str(skill_match["toolset"])
        skill_agent = find_agent(str(skill_match["agent"])) or {}
        model_policy = str(skill_agent.get("model_policy") or "local_first")
        toolset_reason = f"skill {skill_match['name']} por gatilho {skill_match['matched_trigger']}"
    elif selected:
        toolset = str(selected[0]["name"])
        model_policy = str(selected[0]["default_model_policy"])
        toolset_reason = "toolset por gatilho"
    else:
        toolset, model_policy = _fallback_toolset(intent, level)
        toolset_reason = "toolset por fallback de intent"
    if skill_match:
        agent = str(skill_match["agent"])
    else:
        selected_agents = select_agents(f"{user_input} {intent}", toolset=toolset, limit=1)
        agent = str((selected_agents[0] if selected_agents else agent_for_toolset(toolset)).get("name") or "dev_agent")
    chain = build_handoff_chain(user_input, intent, primary_toolset=toolset, primary_agent=agent)
    coordination_mode = "multi_agent_handoff" if handoff_needed(
        user_input,
        intent,
        intent_level=level,
        complexity_kind=complexity_kind,
        chain=chain,
    ) else "single_agent"

    risk_level = _risk_for_intent(intent, level)
    needs_confirmation = risk_level in {"high", "critical"}
    confidence = 0.45 if intent == "respond" else 0.78
    if complexity_kind in {"complex_reasoning", "multi_step"}:
        confidence = min(0.92, confidence + 0.08)

    return DecisionPlan(
        intent=intent,
        intent_level=level,
        confidence=round(confidence, 2),
        toolset=toolset,
        agent=agent,
        risk_level=risk_level,
        needs_confirmation=needs_confirmation,
        response_mode=_response_mode(level, risk_level),
        model_policy=model_policy,
        reason=(
            f"{toolset_reason}; agente {agent}; risco {risk_level}; "
            f"complexidade {complexity_kind or 'indefinida'}; coordenacao {coordination_mode}"
        ),
        handoff_chain=tuple(chain),
        coordination_mode=coordination_mode,
        tool_libraries=tuple(tool_library_for_chain(chain, include_write=True, limit_per_agent=12)),
    )
