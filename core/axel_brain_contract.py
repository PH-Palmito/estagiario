from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

REMOTE_SOURCES = {"telegram", "telegram_bot", "whatsapp", "discord", "remote"}
REMOTE_LIGHT_CONFIRM_ACTIONS = {
    "browser_search_music",
    "browser_queue_music",
    "browser_surprise_music",
    "browser_music_session",
    "spotify_like_current_track",
    "spotify_dislike_current_track",
    "spotify_more_like_current_track",
    "spotify_less_music_vibe",
    "media_play_pause",
    "media_next",
    "media_previous",
    "media_play_pause_target",
    "media_play_target",
    "media_pause_target",
    "media_next_target",
    "media_previous_target",
    "volume_up",
    "volume_down",
    "volume_mute",
}
REMOTE_SAFE_WRITE_ACTIONS = {
    "reminder_add",
}
REMOTE_PERMISSION_TIERS = (
    {
        "tier": "read_only",
        "can_execute": True,
        "can_confirm_remotely": False,
        "summary": "Leitura e respostas sem escrita podem rodar no canal remoto.",
    },
    {
        "tier": "light_media",
        "can_execute": False,
        "can_confirm_remotely": True,
        "summary": "Midia e volume leves exigem confirmacao no proprio chat.",
    },
    {
        "tier": "safe_write",
        "can_execute": True,
        "can_confirm_remotely": False,
        "summary": "Escritas locais de baixo risco, como lembretes, podem rodar no canal remoto autorizado.",
    },
    {
        "tier": "sensitive_or_write",
        "can_execute": False,
        "can_confirm_remotely": False,
        "summary": "Acoes sensiveis, escrita, apps, arquivos e automacoes continuam exigindo confirmacao local no PC.",
    },
)


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict"):
        try:
            payload = value.to_dict()
            return dict(payload) if isinstance(payload, dict) else {}
        except Exception:
            return {}
    return {}


def channel_kind(source: str) -> str:
    normalized = str(source or "").strip().lower()
    if normalized in REMOTE_SOURCES:
        return "remote"
    return "local"


def remote_permission_summary() -> dict:
    return {
        "status": "remote_limited",
        "remote_mode": "expanded_disabled",
        "confirmable_actions": sorted(REMOTE_LIGHT_CONFIRM_ACTIONS),
        "safe_write_actions": sorted(REMOTE_SAFE_WRITE_ACTIONS),
        "tiers": [dict(item) for item in REMOTE_PERMISSION_TIERS],
        "next_review_gate": (
            "Somente ampliar permissoes remotas depois de auditoria, escopo por action, "
            "expiracao curta, allowlist forte e confirmacao local para risco medio/alto."
        ),
    }


def remote_execution_policy(plan: dict, *, source: str, action_name: str = "") -> dict:
    channel = channel_kind(source)
    if channel != "remote":
        return {
            "channel": channel,
            "can_execute": True,
            "can_confirm_remotely": False,
            "decision": "local_flow",
            "safety_profile": "local_normal",
            "execution_guidance": "seguir fluxo local normal com confirmacao quando necessario",
            "reason": "canal local usa confirmacao normal do Axel",
        }

    risk = str(plan.get("risk_level") or "").strip().lower()
    needs_confirmation = bool(plan.get("needs_confirmation"))
    response_mode = str(plan.get("response_mode") or "").strip()
    action = str(action_name or plan.get("intent") or "").strip()
    if action in REMOTE_LIGHT_CONFIRM_ACTIONS:
        return {
            "channel": channel,
            "can_execute": False,
            "can_confirm_remotely": True,
            "decision": "confirm_remote_light",
            "safety_profile": "remote_light_media_confirmation",
            "execution_guidance": "pedir confirmacao no chat antes de executar midia leve",
            "reason": "canal remoto permite apenas midia leve com confirmacao no proprio chat",
        }
    if risk == "read" and not needs_confirmation and response_mode != "confirm_then_act":
        return {
            "channel": channel,
            "can_execute": True,
            "can_confirm_remotely": False,
            "decision": "allow_remote_safe",
            "safety_profile": "remote_read_only",
            "execution_guidance": "responder no canal remoto sem acao de escrita",
            "reason": "canal remoto limitado a leitura nesta fase",
        }
    if action in REMOTE_SAFE_WRITE_ACTIONS and not needs_confirmation:
        return {
            "channel": channel,
            "can_execute": True,
            "can_confirm_remotely": False,
            "decision": "allow_remote_safe_write",
            "safety_profile": "remote_safe_write",
            "execution_guidance": "executar escrita local de baixo risco no canal remoto autorizado",
            "reason": "canal remoto permite lembretes sem confirmacao local",
        }
    return {
        "channel": channel,
        "can_execute": False,
        "can_confirm_remotely": False,
        "decision": "block_remote_confirm_on_pc",
        "safety_profile": "remote_blocked",
        "execution_guidance": "bloquear no canal remoto e orientar uso do PC se necessario",
        "reason": "canal remoto nao executa acao sensivel sem confirmacao local",
    }


def build_axel_brain_contract(
    *,
    source: str,
    user_input: str,
    raw_action: dict | None,
    plan: Any,
    brief: Any,
    route_trace: dict | None = None,
) -> dict:
    plan_payload = _as_dict(plan)
    brief_payload = _as_dict(brief)
    action = raw_action if isinstance(raw_action, dict) else {}
    layers = brief_payload.get("memory_layers") if isinstance(brief_payload.get("memory_layers"), list) else []
    layer_names = [
        str(item.get("name") or "").strip()
        for item in layers
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    ]
    memory_influences = []
    for layer in layers:
        if not isinstance(layer, dict):
            continue
        layer_name = str(layer.get("name") or "").strip()
        for influence in layer.get("influences") or []:
            if not isinstance(influence, dict):
                continue
            memory_influences.append(
                {
                    "layer": layer_name,
                    "domain": str(influence.get("domain") or ""),
                    "section": str(influence.get("section") or ""),
                    "source": str(influence.get("source") or ""),
                    "scope": str(influence.get("scope") or ""),
                    "confidence": influence.get("confidence"),
                    "priority": str(influence.get("priority") or ""),
                    "reason": str(influence.get("reason") or "")[:180],
                    "text": str(influence.get("text") or "")[:180],
                }
            )
    action_name = str(action.get("intent") or plan_payload.get("intent") or "respond")
    policy = remote_execution_policy(plan_payload, source=source, action_name=action_name)
    return {
        "version": str(brief_payload.get("brain_version") or "2.0"),
        "source": str(source or "turn"),
        "channel": policy["channel"],
        "user_input": str(user_input or "")[:500],
        "intent": action_name,
        "target": action.get("target"),
        "decision_type": str(plan_payload.get("decision_type") or action.get("__decision_type") or ""),
        "capability": str(plan_payload.get("capability") or action.get("__capability") or ""),
        "capability_source": str(plan_payload.get("capability_source") or action.get("__capability_source") or ""),
        "semantic_fallback": dict(action.get("__semantic_fallback") or {}) if isinstance(action.get("__semantic_fallback"), dict) else {},
        "agent": str(plan_payload.get("agent") or brief_payload.get("agent") or ""),
        "toolset": str(plan_payload.get("toolset") or brief_payload.get("toolset") or ""),
        "risk_level": str(plan_payload.get("risk_level") or ""),
        "needs_confirmation": bool(plan_payload.get("needs_confirmation")),
        "response_mode": str(plan_payload.get("response_mode") or ""),
        "model_policy": str(plan_payload.get("model_policy") or brief_payload.get("model_policy") or ""),
        "coordination_mode": str(plan_payload.get("coordination_mode") or brief_payload.get("coordination_mode") or "single_agent"),
        "next_step": str(brief_payload.get("next_step") or ""),
        "execution_guidance": str(policy.get("execution_guidance") or ""),
        "memory_layers": layer_names[:6],
        "memory_influences": memory_influences[:8],
        "success_criteria": [str(item) for item in (brief_payload.get("success_criteria") or [])[:5]],
        "post_task_signals": [str(item) for item in (brief_payload.get("post_task_signals") or [])[:5]],
        "remote_policy": policy,
        "route": dict(route_trace or {}),
    }
