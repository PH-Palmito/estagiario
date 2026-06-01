from __future__ import annotations

from core.router_utils import normalize_text


AXEL_BRAIN_DECISION_COMMANDS = {
    "decisao do axelbrain",
    "decisao do axel brain",
    "ultima decisao do axelbrain",
    "ultima decisao do axel brain",
    "plano do axelbrain",
    "plano do axel brain",
    "qual o plano do axelbrain",
    "qual o plano do axel brain",
    "qual agente o axel escolheu",
    "qual agente o axelbrain escolheu",
    "qual agente esta ativo",
    "qual toolset esta ativo",
    "por que o axel decidiu isso",
    "por que o axelbrain decidiu isso",
    "por que esse agente",
    "por que esse toolset",
    "handoff do axelbrain",
    "handoff do axel brain",
    "cadeia de agentes",
    "quais agentes vao atuar",
    "ferramentas do agente",
    "ferramentas do axelbrain",
    "biblioteca de ferramentas",
}

AXEL_ROUTE_TRACE_COMMANDS = {
    "ultima rota do axel",
    "rota do axel",
    "por que esse comando caiu assim",
    "por que esse comando foi assim",
    "por que caiu nesse comando",
    "por que caiu na tela",
    "qual detector pegou",
    "qual detector pegou o comando",
    "diagnostico da ultima rota",
    "diagnostico do roteamento",
}


def format_axel_brain_runtime_decision(plan: dict | None, brief: dict | None = None) -> str:
    payload = plan if isinstance(plan, dict) else {}
    specialist = brief if isinstance(brief, dict) else {}
    if not payload:
        return "Ainda nao tenho uma decisao recente do AxelBrain para explicar."

    agent = str(payload.get("agent") or specialist.get("agent") or "--")
    toolset = str(payload.get("toolset") or specialist.get("toolset") or "--")
    intent = str(payload.get("intent") or "--")
    risk = str(payload.get("risk_level") or "--")
    response_mode = str(payload.get("response_mode") or "--")
    model_policy = str(payload.get("model_policy") or specialist.get("model_policy") or "--")
    reason = str(payload.get("reason") or "Sem motivo registrado.")
    mission = str(specialist.get("mission") or "").strip()
    coordination_mode = str(payload.get("coordination_mode") or specialist.get("coordination_mode") or "single_agent")
    handoff_chain = payload.get("handoff_chain") or specialist.get("handoff_chain") or []
    if not isinstance(handoff_chain, list):
        handoff_chain = list(handoff_chain) if isinstance(handoff_chain, tuple) else []
    tool_libraries = payload.get("tool_libraries") or specialist.get("tool_libraries") or []
    if not isinstance(tool_libraries, list):
        tool_libraries = list(tool_libraries) if isinstance(tool_libraries, tuple) else []

    confidence = payload.get("confidence")
    if isinstance(confidence, (int, float)):
        confidence_text = f"{round(float(confidence) * 100)}%"
    else:
        confidence_text = "--"

    parts = [
        "Ultima decisao do AxelBrain:",
        f"agente {agent}",
        f"toolset {toolset}",
        f"intent {intent}",
        f"risco {risk}",
        f"confianca {confidence_text}",
        f"modo {response_mode}",
        f"coordenacao {coordination_mode}",
        f"modelo {model_policy}",
        f"motivo: {reason}",
    ]
    if mission:
        parts.append(f"missao do agente: {mission}")
    if handoff_chain:
        chain = " -> ".join(
            f"{item.get('agent', '--')} via {item.get('toolset', '--')}"
            for item in handoff_chain[:4]
            if isinstance(item, dict)
        )
        if chain:
            parts.append(f"handoff: {chain}")
    if tool_libraries:
        snippets = []
        for library in tool_libraries[:3]:
            if not isinstance(library, dict):
                continue
            actions = library.get("actions") or []
            names = ", ".join(
                str(item.get("name"))
                for item in actions[:4]
                if isinstance(item, dict) and item.get("name")
            )
            if names:
                snippets.append(f"{library.get('agent', '--')}: {names}")
        if snippets:
            parts.append("ferramentas por agente: " + " | ".join(snippets))
    return "; ".join(parts) + "."


def maybe_handle_axel_brain_runtime_command(user_input: str, runtime_state) -> str | None:
    normalized = normalize_text(user_input)
    if normalized in AXEL_ROUTE_TRACE_COMMANDS:
        return format_axel_route_trace(getattr(runtime_state, "last_route_trace", None))

    if normalized not in AXEL_BRAIN_DECISION_COMMANDS:
        return None

    return format_axel_brain_runtime_decision(
        getattr(runtime_state, "axel_brain_plan", None),
        getattr(runtime_state, "axel_brain_brief", None),
    )


def format_axel_route_trace(trace: dict | None) -> str:
    payload = trace if isinstance(trace, dict) else {}
    if not payload:
        return "Ainda nao tenho uma rota recente para explicar."

    group = str(payload.get("group") or "nenhum")
    detector = str(payload.get("detector") or "nenhum")
    intent = str(payload.get("intent") or "--")
    target = payload.get("target")
    intent_level = str(payload.get("intent_level") or "--")
    complexity = str(payload.get("complexity") or "--")
    checked = payload.get("checked_detectors")
    checked_groups = payload.get("checked_groups") if isinstance(payload.get("checked_groups"), list) else []
    reason = str(payload.get("complexity_reason") or "").strip()

    target_text = f"; alvo {target}" if target not in {None, ""} else ""
    checked_text = f"; avaliou {checked} detectores" if checked not in {None, ""} else ""
    groups_text = f"; grupos vistos: {', '.join(str(item) for item in checked_groups[:5])}" if checked_groups else ""
    reason_text = f"; motivo de complexidade: {reason}" if reason else ""
    return (
        "Ultima rota do Axel: "
        f"grupo {group}; detector {detector}; intent {intent}{target_text}; "
        f"nivel {intent_level}; complexidade {complexity}{reason_text}{checked_text}{groups_text}."
    )
