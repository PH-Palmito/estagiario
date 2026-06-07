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

AXEL_BRAIN_HISTORY_COMMANDS = {
    "historico do axelbrain",
    "historico do axel brain",
    "ultimas decisoes do axelbrain",
    "ultimas decisoes do axel brain",
    "ultimos planos do axelbrain",
    "ultimos planos do axel brain",
}

AXEL_BRAIN_INSIGHT_COMMANDS = {
    "insights do axelbrain",
    "insights do axel brain",
    "resumo do axelbrain",
    "resumo do axel brain",
    "padroes do axelbrain",
    "padroes do axel brain",
}

AXEL_BRAIN_TIMELINE_COMMANDS = {
    "timeline do axelbrain",
    "timeline do axel brain",
    "linha do tempo do axelbrain",
    "linha do tempo do axel brain",
    "auditoria do axelbrain",
    "auditoria do axel brain",
    "ultima auditoria do axelbrain",
    "ultima auditoria do axel brain",
}


def format_axel_brain_runtime_decision(
    plan: dict | None,
    brief: dict | None = None,
    contract: dict | None = None,
) -> str:
    payload = plan if isinstance(plan, dict) else {}
    specialist = brief if isinstance(brief, dict) else {}
    contract_payload = contract if isinstance(contract, dict) else {}
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
    brain_version = str(specialist.get("brain_version") or payload.get("brain_version") or "").strip()
    next_step = str(specialist.get("next_step") or "").strip()
    success_criteria = specialist.get("success_criteria") or []
    post_task_signals = specialist.get("post_task_signals") or []
    memory_layers = specialist.get("memory_layers") or []
    coordination_mode = str(payload.get("coordination_mode") or specialist.get("coordination_mode") or "single_agent")
    remote_policy = contract_payload.get("remote_policy") if isinstance(contract_payload.get("remote_policy"), dict) else {}
    channel = str(contract_payload.get("channel") or remote_policy.get("channel") or "").strip()
    safety_profile = str(remote_policy.get("safety_profile") or "").strip()
    remote_decision = str(remote_policy.get("decision") or "").strip()
    execution_guidance = str(contract_payload.get("execution_guidance") or remote_policy.get("execution_guidance") or "").strip()
    can_confirm_remotely = remote_policy.get("can_confirm_remotely")
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
        f"Ultima decisao do AxelBrain{f' {brain_version}' if brain_version else ''}:",
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
    if channel or safety_profile or remote_decision:
        policy_parts = []
        if channel:
            policy_parts.append(f"canal {channel}")
        if safety_profile:
            policy_parts.append(f"perfil {safety_profile}")
        if remote_decision:
            policy_parts.append(f"decisao {remote_decision}")
        if isinstance(can_confirm_remotely, bool):
            policy_parts.append(f"confirmacao remota {'sim' if can_confirm_remotely else 'nao'}")
        parts.append("politica de canal: " + ", ".join(policy_parts))
    if execution_guidance:
        parts.append(f"guia de execucao: {execution_guidance}")
    if next_step:
        parts.append(f"proximo passo: {next_step}")
    if isinstance(success_criteria, (list, tuple)) and success_criteria:
        parts.append("criterios de sucesso: " + ", ".join(str(item) for item in success_criteria[:3]))
    if isinstance(post_task_signals, (list, tuple)) and post_task_signals:
        parts.append("sinais pos-tarefa: " + ", ".join(str(item) for item in post_task_signals[:3]))
    if isinstance(memory_layers, (list, tuple)) and memory_layers:
        layer_names = []
        for layer in memory_layers[:4]:
            if isinstance(layer, dict):
                name = str(layer.get("name") or "").strip()
                if name:
                    layer_names.append(name)
        if layer_names:
            parts.append("memoria consultada: " + ", ".join(layer_names))
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
    if normalized in AXEL_BRAIN_INSIGHT_COMMANDS:
        return format_axel_brain_insights(getattr(runtime_state, "axel_brain_history", None))

    if normalized in AXEL_BRAIN_TIMELINE_COMMANDS:
        return format_axel_brain_timeline(getattr(runtime_state, "axel_brain_timeline", None))

    if normalized in AXEL_BRAIN_HISTORY_COMMANDS:
        return format_axel_brain_history(getattr(runtime_state, "axel_brain_history", None))

    if normalized in AXEL_ROUTE_TRACE_COMMANDS:
        return format_axel_route_trace(getattr(runtime_state, "last_route_trace", None))

    if normalized not in AXEL_BRAIN_DECISION_COMMANDS:
        return None

    return format_axel_brain_runtime_decision(
        getattr(runtime_state, "axel_brain_plan", None),
        getattr(runtime_state, "axel_brain_brief", None),
        getattr(runtime_state, "axel_brain_contract", None),
    )


def _shorten(value: object, limit: int = 120) -> str:
    text = str(value or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def format_axel_brain_timeline(timeline: list | tuple | None) -> str:
    items = [item for item in list(timeline or []) if isinstance(item, dict)]
    if not items:
        return "Ainda nao tenho timeline auditavel do AxelBrain nesta sessao."

    lines = []
    for index, item in enumerate(items[-5:], start=1):
        decision = item.get("decision") if isinstance(item.get("decision"), dict) else {}
        context = item.get("context") if isinstance(item.get("context"), dict) else {}
        execution = item.get("execution") if isinstance(item.get("execution"), dict) else {}
        response = item.get("response") if isinstance(item.get("response"), dict) else {}

        source = str(context.get("source") or item.get("source") or "--")
        user_input = _shorten(context.get("input") or item.get("input"), 80) or "--"
        route_group = str(context.get("route_group") or item.get("route_group") or "--")
        detector = str(context.get("detector") or item.get("detector") or "--")
        intent = str(decision.get("intent") or item.get("intent") or "--")
        agent = str(decision.get("agent") or item.get("agent") or "--")
        toolset = str(decision.get("toolset") or item.get("toolset") or "--")
        risk = str(decision.get("risk_level") or item.get("risk_level") or "--")
        reason = _shorten(decision.get("reason"), 90)
        memory_layers = context.get("memory_layers") if isinstance(context.get("memory_layers"), list) else []
        memory_text = ", ".join(str(layer) for layer in memory_layers[:3] if str(layer).strip())
        confirmation = "sim" if bool(execution.get("needs_confirmation", item.get("needs_confirmation"))) else "nao"
        action = str(execution.get("action") or item.get("action") or "--")
        result = _shorten(response.get("final") or item.get("result"), 120) or "--"
        decision_text = f"decisao intent {intent}, agente {agent}, toolset {toolset}, risco {risk}"
        if reason:
            decision_text += f", motivo {reason}"
        context_text = f"contexto rota {route_group}/{detector}"
        if memory_text:
            context_text += f", memoria {memory_text}"
        lines.append(
            f"{index}. entrada '{user_input}' via {source}; {decision_text}; "
            f"{context_text}; execucao action {action}, confirmacao {confirmation}; resposta final {result}"
        )
    return "Timeline auditavel do AxelBrain: " + "; ".join(lines) + "."


def format_axel_brain_history(history: list | tuple | None) -> str:
    items = list(history or [])
    if not items:
        return "Ainda nao tenho historico de decisoes do AxelBrain nesta sessao."

    lines = []
    for index, item in enumerate(items[-5:], start=1):
        if not isinstance(item, dict):
            continue
        intent = str(item.get("intent") or "--")
        agent = str(item.get("agent") or "--")
        toolset = str(item.get("toolset") or "--")
        risk = str(item.get("risk_level") or "--")
        channel = str(item.get("channel") or "--")
        safety = str(item.get("safety_profile") or "--")
        route_group = str(item.get("route_group") or "--")
        lines.append(
            f"{index}. {intent}: agente {agent}, toolset {toolset}, risco {risk}, canal {channel}, perfil {safety}, grupo {route_group}"
        )
    if not lines:
        return "Ainda nao tenho historico de decisoes do AxelBrain nesta sessao."
    return "Ultimas decisoes do AxelBrain: " + "; ".join(lines) + "."


def _top_counts(items: list[dict], key: str, limit: int = 3) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "").strip()
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:limit]


def format_axel_brain_insights(history: list | tuple | None) -> str:
    items = [item for item in list(history or []) if isinstance(item, dict)]
    if not items:
        return "Ainda nao tenho decisoes suficientes para gerar insights do AxelBrain nesta sessao."

    total = len(items)
    agents = ", ".join(f"{name} {count}x" for name, count in _top_counts(items, "agent")) or "--"
    toolsets = ", ".join(f"{name} {count}x" for name, count in _top_counts(items, "toolset")) or "--"
    risks = ", ".join(f"{name} {count}x" for name, count in _top_counts(items, "risk_level")) or "--"
    profiles = ", ".join(f"{name} {count}x" for name, count in _top_counts(items, "safety_profile")) or "--"
    blocked = sum(1 for item in items if str(item.get("safety_profile") or "") == "remote_blocked")
    remote = sum(1 for item in items if str(item.get("channel") or "") == "remote")
    return (
        f"Insights do AxelBrain nesta sessao: {total} decisoes; "
        f"agentes mais usados: {agents}; toolsets: {toolsets}; riscos: {risks}; "
        f"perfis de seguranca: {profiles}; remoto {remote}x; bloqueios remotos {blocked}x. "
        f"Recomendacoes: {'; '.join(axel_brain_recommendations(items))}"
    )


def axel_brain_recommendations(history: list | tuple | None) -> list[str]:
    items = [item for item in list(history or []) if isinstance(item, dict)]
    if not items:
        return ["acumular mais decisoes antes de ajustar o comportamento"]

    blocked = sum(1 for item in items if str(item.get("safety_profile") or "") == "remote_blocked")
    remote_light = sum(1 for item in items if str(item.get("safety_profile") or "") == "remote_light_media_confirmation")
    high_risk = sum(1 for item in items if str(item.get("risk_level") or "") in {"high", "critical"})
    read = sum(1 for item in items if str(item.get("risk_level") or "") == "read")
    total = len(items)
    recommendations: list[str] = []

    if blocked:
        recommendations.append("manter bloqueio remoto ampliado e revisar manualmente os comandos bloqueados")
    if remote_light >= 2:
        recommendations.append("preservar confirmacao por botao para midia remota")
    if high_risk:
        recommendations.append("auditar comandos de risco alto antes de ampliar automacao")
    if read >= max(3, total // 2):
        recommendations.append("otimizar respostas de leitura com cache e briefing curto")
    if not recommendations:
        recommendations.append("sessao equilibrada; manter politica atual")
    return recommendations[:3]


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
