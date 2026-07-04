from __future__ import annotations

from core.response_polish import polish_assistant_response


def apply_plan_to_command(command, plan: dict | None) -> dict:
    payload = plan if isinstance(plan, dict) else {}
    effects = {
        "confirmation_applied": False,
        "confidence_applied": False,
        "agent": str(payload.get("agent") or ""),
        "toolset": str(payload.get("toolset") or ""),
    }
    if bool(payload.get("needs_confirmation")):
        command.requires_confirmation = True
        effects["confirmation_applied"] = True

    confidence = payload.get("confidence")
    if isinstance(confidence, (int, float)):
        command.confidence = min(float(getattr(command, "confidence", 1.0)), max(0.0, min(1.0, float(confidence))))
        effects["confidence_applied"] = True
    return effects


def personality_allowed_for_plan(plan: dict | None) -> bool:
    payload = plan if isinstance(plan, dict) else {}
    response_mode = str(payload.get("response_mode") or "").strip()
    risk_level = str(payload.get("risk_level") or "").strip()
    if response_mode in {"execute_short", "confirm_then_act"}:
        return False
    return risk_level not in {"high", "critical"}


def format_axel_brain_effects(plan: dict | None, brief: dict | None, contract: dict | None) -> str:
    payload = plan if isinstance(plan, dict) else {}
    specialist = brief if isinstance(brief, dict) else {}
    agreement = contract if isinstance(contract, dict) else {}
    if not payload:
        return "Ainda nao ha uma decisao do AxelBrain para auditar."

    layers = specialist.get("memory_layers") if isinstance(specialist.get("memory_layers"), list) else []
    layer_names = [
        str(item.get("name") or "")
        for item in layers
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    ]
    raw_libraries = payload.get("tool_libraries")
    libraries = list(raw_libraries) if isinstance(raw_libraries, (list, tuple)) else []
    action_count = sum(
        len(item.get("actions") or [])
        for item in libraries
        if isinstance(item, dict) and isinstance(item.get("actions"), (list, tuple))
    )
    personality = "liberada" if personality_allowed_for_plan(payload) else "suprimida"
    return polish_assistant_response(
        "Efeitos reais do AxelBrain nesta decisao: "
        f"roteamento seleciona agente {payload.get('agent', '--')} e toolset {payload.get('toolset', '--')} "
        f"com {action_count} actions candidatas; "
        f"modelo segue {payload.get('model_policy', '--')}; "
        f"memoria selecionada: {', '.join(layer_names) or 'nenhuma camada'}; "
        f"confirmacao {'obrigatoria' if payload.get('needs_confirmation') else 'nao exigida'}; "
        f"resposta usa modo {payload.get('response_mode', '--')} com personalidade {personality}; "
        f"canal {agreement.get('channel', 'local')}."
    )
