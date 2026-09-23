from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from memory.json_store import read_json_file, update_json_file, write_json_atomic
from memory.operational_context import remember_operational_preference
from memory.supabase_sync import sync_memory_state_safely

ADAPTIVE_PREFERENCES_PATH = Path("memory") / "adaptive_preferences.json"

TARGET_ALIASES = {
    "agenda": ("agenda", "compromisso", "compromissos"),
    "briefing": ("briefing", "resumo do dia", "panorama do dia", "prepara meu dia", "preparar meu dia"),
    "investments": ("carteira", "investimento", "investimentos", "ativo", "ativos"),
    "identity": ("nome", "chamar", "chame", "apelido", "identidade"),
    "notifications": ("aviso", "avisos", "notificacao", "notificacoes"),
    "reminders": ("lembrete", "lembretes"),
    "response_tone": ("tom", "jeito de responder", "resposta", "respostas", "professor", "professora"),
    "studies": ("estudo", "estudos", "estudando", "estudar", "aula", "prova", "materia"),
    "training": ("treino", "treinos", "exercicio", "exercicios", "academia", "ficha"),
}

BRIEFING_SECTION_ALIASES = {
    "greeting": ("saudacao", "bom dia", "boa tarde", "boa noite"),
    "climate": ("clima", "tempo", "chuva", "temperatura"),
    "agenda": ("agenda", "compromissos", "calendario"),
    "investments": ("carteira", "investimentos", "mercado"),
    "dividends": ("dividendos", "proventos"),
    "radar": ("radar", "radar da carteira", "alertas da carteira"),
    "focus": ("foco", "foco do dia", "prioridade do dia"),
    "reminders": ("lembretes", "lembrete"),
}

BRIEFING_SECTION_LABELS = {
    "greeting": "saudacao",
    "climate": "clima",
    "agenda": "agenda",
    "investments": "carteira",
    "dividends": "dividendos",
    "radar": "radar da carteira",
    "focus": "foco do dia",
    "reminders": "lembretes",
}

TARGET_LABELS = {
    "agenda": "agenda",
    "briefing": "briefing",
    "investments": "investimentos",
    "identity": "identidade",
    "notifications": "avisos",
    "reminders": "lembretes",
    "response_tone": "tom de resposta",
    "studies": "estudos",
    "training": "treino",
}

DOMAIN_TARGETS = {
    "briefing": {"briefing"},
    "identity": {"identity"},
    "training": {"training"},
    "studies": {"studies"},
    "response_tone": {"response_tone", "studies"},
    "notifications": {"notifications", "briefing", "training", "reminders"},
}

SUPPRESS_MARKERS = (
    "nao quero",
    "nao precisa",
    "nao me avise",
    "nao avise",
    "nao me informe",
    "nao informe",
    "pode parar",
    "pare de",
    "parar de",
    "para de",
    "sem ",
    "dispensa",
    "desliga",
    "desligar",
    "evite",
    "nao faz",
    "nao faca",
    "nao fazer",
)

RESTORE_MARKERS = (
    "volta como era",
    "voltar como era",
    "esquece essa regra",
    "esqueca essa regra",
    "desfaz essa regra",
    "desfazer essa regra",
    "volte a",
    "voltar a",
    "pode voltar",
    "pode me avisar",
    "me avise",
    "reativa",
    "reativar",
    "liga",
    "ligar",
)

EXPLAIN_MARKERS = (
    "por que voce se adaptou assim",
    "porque voce se adaptou assim",
    "por que se adaptou assim",
    "porque se adaptou assim",
    "qual regra voce usou",
    "que regra voce usou",
)

IMPORTANT_CHANGE_MARKERS = (
    "novo plano",
    "nova ficha",
    "substituir plano",
    "trocar plano",
    "mudar plano",
    "use ela como meu novo plano",
    "usar ela como meu novo plano",
    "usar isso como meu novo plano",
    "foto da ficha",
    "ficha de treino",
)

IDENTITY_CHANGE_MARKERS = (
    "muda seu nome",
    "mudar seu nome",
    "troca seu nome",
    "trocar seu nome",
    "seu nome agora",
    "teu nome agora",
    "a partir de agora voce se chama",
    "a partir de agora seu nome",
    "quero te chamar de",
    "vou te chamar de",
)

CONFIRM_YES = {"sim", "confirmo", "pode aplicar", "aplica", "aplicar", "ok pode", "isso"}
CONFIRM_NO = {"nao", "cancela", "cancelar", "deixa", "deixa quieto", "agora nao"}

ACTION_HINTS = {
    "announce": ("avis", "notific", "falar", "lembr", "alert"),
    "run": ("faz", "fazer", "gerar", "preparar", "rodar", "executar", "mostrar"),
}


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.lower()
    normalized = re.sub(r"[^\w\s/:-]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip(" .,:;-")


def _payload_from(data: dict | None) -> dict:
    data = data if isinstance(data, dict) else {}
    return {
        "rules": [rule for rule in data.get("rules") or [] if isinstance(rule, dict)],
        "pending_candidates": [item for item in data.get("pending_candidates") or [] if isinstance(item, dict)],
        "last_applied": data.get("last_applied") if isinstance(data.get("last_applied"), dict) else {},
        "current_context": data.get("current_context") if isinstance(data.get("current_context"), dict) else {},
    }


def _load() -> dict:
    data = read_json_file(ADAPTIVE_PREFERENCES_PATH, {}, validator=lambda value: isinstance(value, dict))
    return _payload_from(data)


def save_adaptive_preferences(data: dict) -> dict:
    payload = _payload_from(data)
    write_json_atomic(ADAPTIVE_PREFERENCES_PATH, payload, indent=2, trailing_newline=True)
    sync_memory_state_safely("adaptive_preferences", payload, category="preferences")
    return payload


def _update(updater) -> dict:
    def apply_once(data: dict | None) -> dict:
        updated = updater(_payload_from(data))
        return _payload_from(updated)

    payload = update_json_file(
        ADAPTIVE_PREFERENCES_PATH,
        {"rules": [], "pending_candidates": [], "last_applied": {}, "current_context": {}},
        apply_once,
        validator=lambda value: isinstance(value, dict),
        indent=2,
        trailing_newline=True,
    )
    sync_memory_state_safely("adaptive_preferences", payload, category="preferences")
    return payload


def _target_from_text(normalized: str) -> tuple[str, str]:
    if "professor" in normalized or "professora" in normalized or "tom" in normalized:
        return "response_tone", TARGET_LABELS["response_tone"]
    for target, aliases in TARGET_ALIASES.items():
        if any(re.search(rf"\b{re.escape(_normalize(alias))}\b", normalized) for alias in aliases):
            return target, TARGET_LABELS.get(target, target)

    match = re.search(r"\b(?:sobre|do|da|de|dos|das|com)\s+(.+)$", normalized)
    raw = _compact(match.group(1) if match else normalized)
    raw = re.sub(r"\b(?:hoje|amanha|por hoje|por enquanto|temporariamente)\b", " ", raw)
    raw = re.sub(r"\b(?:me|voce|voces|axel|avisar|avise|fazer|faca|precisa|quero)\b", " ", raw)
    label = _compact(raw)[:48] or "isso"
    target = re.sub(r"[^a-z0-9]+", "_", label).strip("_") or "custom"
    return target, label


def _domain_from_target(target: str) -> str:
    for domain, targets in DOMAIN_TARGETS.items():
        if target in targets:
            return domain
    return target or "general"


def _action_from_text(normalized: str, target: str) -> str:
    if target == "briefing" and any(word in normalized for word in ("fazer", "gerar", "preparar", "rodar")):
        return "run"
    for action, hints in ACTION_HINTS.items():
        if any(hint in normalized for hint in hints):
            return action
    return "announce"


def _scope_from_text(normalized: str, now: datetime) -> tuple[str, str, str]:
    if re.search(r"\bamanha\b", normalized):
        start = datetime.combine((now + timedelta(days=1)).date(), datetime.min.time())
        end = start + timedelta(days=1)
        return "amanha", start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds")
    if re.search(r"\b(?:hoje|por hoje)\b", normalized):
        end = datetime.combine((now + timedelta(days=1)).date(), datetime.min.time())
        return "hoje", "", end.isoformat(timespec="seconds")
    if re.search(r"\b(?:por enquanto|temporariamente|por agora)\b", normalized):
        return "por enquanto", "", ""
    return "permanente", "", ""


def _validity(scope: str, starts_at: str, expires_at: str) -> dict[str, str]:
    return {"scope": scope, "starts_at": starts_at, "expires_at": expires_at}


def _base_rule(
    *,
    rule_id: str,
    kind: str,
    target: str,
    label: str,
    raw_text: str,
    now: datetime,
    scope: str,
    starts_at: str,
    expires_at: str,
    priority: int,
    action: str = "all",
    value: Any = None,
    conditions: dict[str, Any] | None = None,
) -> dict:
    return {
        "id": rule_id,
        "kind": kind,
        "domain": _domain_from_target(target),
        "target": target,
        "label": label,
        "action": action,
        "value": value,
        "scope": scope,
        "validity": _validity(scope, starts_at, expires_at),
        "starts_at": starts_at,
        "expires_at": expires_at,
        "priority": int(priority),
        "conditions": conditions if isinstance(conditions, dict) else {},
        "enabled": True,
        "origin": {"source": "user_natural_language", "text": _compact(raw_text)},
        "source_text": _compact(raw_text),
        "created_at": now.isoformat(timespec="seconds"),
        "undo": {
            "natural": [
                "volta como era",
                "esquece essa regra",
                f"desfazer regra de {label}",
            ],
            "disable_rule_id": rule_id,
        },
    }


def _is_rule_active(rule: dict, *, now: datetime) -> bool:
    starts_at = str(rule.get("starts_at") or (rule.get("validity") or {}).get("starts_at") or "").strip()
    expires_at = str(rule.get("expires_at") or (rule.get("validity") or {}).get("expires_at") or "").strip()
    try:
        if starts_at and now < datetime.fromisoformat(starts_at):
            return False
    except Exception:
        pass
    try:
        if expires_at and now >= datetime.fromisoformat(expires_at):
            return False
    except Exception:
        pass
    return bool(rule.get("enabled", True))


def _condition_from_text(normalized: str) -> tuple[dict[str, Any], str]:
    if re.search(r"\b(?:de manha|pela manha|manha)\b", normalized):
        return {"time_of_day": "morning"}, " de manha"
    if re.search(r"\b(?:de tarde|pela tarde|a tarde|tarde)\b", normalized):
        return {"time_of_day": "afternoon"}, " a tarde"
    if re.search(r"\b(?:de noite|pela noite|a noite|noite)\b", normalized):
        return {"time_of_day": "night"}, " a noite"
    if re.search(r"\b(?:quando|se)\s+eu\s+(?:estiver|tiver|estou|to|tou)\s+estud", normalized):
        return {"context": "studies"}, " quando estiver estudando"
    if re.search(r"\b(?:quando|se)\s+eu\s+(?:estiver|tiver|estou|to|tou)\s+(?:atrasado|com pressa|correndo)\b", normalized):
        return {"context": "rushed"}, " quando estiver com pressa"
    return {}, ""


def _conditions_match(conditions: dict[str, Any], *, now: datetime, context: dict[str, Any] | str | None = None) -> bool:
    if not conditions:
        return True
    time_of_day = str(conditions.get("time_of_day") or "").strip()
    if time_of_day:
        hour = now.hour
        if time_of_day == "morning" and not (5 <= hour < 12):
            return False
        if time_of_day == "afternoon" and not (12 <= hour < 18):
            return False
        if time_of_day == "night" and not (hour >= 18 or hour < 5):
            return False

    expected_context = str(conditions.get("context") or "").strip()
    if expected_context:
        if isinstance(context, dict):
            active_context = str(context.get("context") or context.get("domain") or "").strip()
        else:
            active_context = str(context or "").strip()
        if active_context != expected_context:
            return False
    return True


def _context_from_text(normalized: str) -> tuple[str, str, int]:
    if re.search(r"\b(?:estou|to|tou|vou ficar|estarei)\s+estud", normalized) or re.search(
        r"\b(?:modo|sessao|sessao de|periodo de)\s+estud", normalized
    ):
        return "studies", "estudando", 3 * 60 * 60
    if re.search(r"\b(?:estou|to|tou)\s+(?:atrasado|com pressa|correndo)\b", normalized):
        return "rushed", "com pressa", 60 * 60
    if re.search(r"\b(?:sai|sair|terminei|encerrei|parei)\s+(?:de\s+)?estud", normalized):
        return "clear:studies", "estudo encerrado", 0
    if re.search(r"\b(?:sem pressa|nao estou mais com pressa|nao to mais com pressa|desacelerei)\b", normalized):
        return "clear:rushed", "pressa encerrada", 0
    return "", "", 0


def set_current_adaptive_context(
    context: str,
    *,
    label: str = "",
    raw_text: str = "",
    now: datetime | None = None,
    ttl_seconds: int = 3 * 60 * 60,
) -> dict:
    now = now or datetime.now()
    context = str(context or "").strip()
    expires_at = now + timedelta(seconds=max(60, int(ttl_seconds or 60)))
    payload = {
        "context": context,
        "label": str(label or context).strip() or context,
        "source_text": _compact(raw_text),
        "created_at": now.isoformat(timespec="seconds"),
        "expires_at": expires_at.isoformat(timespec="seconds"),
    }

    def apply(data: dict) -> dict:
        data["current_context"] = payload
        return data

    _update(apply)
    return payload


def clear_current_adaptive_context(context: str = "", *, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    expected = str(context or "").strip()

    def apply(data: dict) -> dict:
        current = data.get("current_context") if isinstance(data.get("current_context"), dict) else {}
        if not expected or str(current.get("context") or "") == expected:
            current["cleared_at"] = now.isoformat(timespec="seconds")
            current["enabled"] = False
            data["current_context"] = current
        return data

    return _update(apply).get("current_context") or {}


def get_current_adaptive_context(*, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    current = _load().get("current_context") or {}
    if not isinstance(current, dict) or not bool(current.get("context")):
        return {}
    if current.get("enabled") is False:
        return {}
    expires_at = str(current.get("expires_at") or "").strip()
    try:
        if expires_at and now >= datetime.fromisoformat(expires_at):
            return {}
    except Exception:
        pass
    return dict(current)


def maybe_handle_adaptive_context_request(raw_text: str, *, now: datetime | None = None) -> str | None:
    now = now or datetime.now()
    normalized = _normalize(raw_text)
    context, label, ttl_seconds = _context_from_text(normalized)
    if not context:
        return None
    if context.startswith("clear:"):
        cleared = context.split(":", 1)[1]
        clear_current_adaptive_context(cleared, now=now)
        if cleared == "studies":
            return "Entendi. Nao vou mais considerar que voce esta estudando agora."
        if cleared == "rushed":
            return "Entendi. Nao vou mais considerar que voce esta com pressa agora."
        return "Entendi. Limpei esse contexto atual."

    set_current_adaptive_context(context, label=label, raw_text=raw_text, now=now, ttl_seconds=ttl_seconds)
    if context == "studies":
        return "Entendi. Vou considerar que voce esta estudando pelas proximas horas."
    if context == "rushed":
        return "Entendi. Vou considerar que voce esta com pressa por um tempo."
    return f"Entendi. Contexto atual: {label}."


def _matches_rule_target(rule: dict, target: str, text: str = "", domain: str = "") -> bool:
    rule_target = str(rule.get("target") or "").strip()
    if rule_target == target:
        return True
    rule_domain = str(rule.get("domain") or "").strip()
    if domain and rule_domain == domain:
        return True
    normalized_text = _normalize(text)
    label = _normalize(str(rule.get("label") or ""))
    return bool(label and normalized_text and label in normalized_text)


def _remember_last_applied(rule: dict, *, reason: str) -> None:
    def apply(data: dict) -> dict:
        data["last_applied"] = {
            "rule_id": rule.get("id"),
            "label": rule.get("label"),
            "domain": rule.get("domain"),
            "kind": rule.get("kind"),
            "reason": reason,
            "source_text": rule.get("source_text"),
            "origin": rule.get("origin") or {},
            "undo": rule.get("undo") or {},
            "applied_at": datetime.now().isoformat(timespec="seconds"),
        }
        return data

    try:
        _update(apply)
    except Exception:
        pass


def _active_rules_for(
    *,
    target: str = "",
    domain: str = "",
    kind: str = "",
    action: str = "",
    text: str = "",
    now: datetime | None = None,
    context: dict[str, Any] | str | None = None,
) -> list[dict]:
    now = now or datetime.now()
    if context is None:
        active_context = get_current_adaptive_context(now=now)
        context = active_context.get("context") if active_context else None
    rules = []
    for rule in _load().get("rules") or []:
        if kind and str(rule.get("kind") or "") != kind:
            continue
        if action and str(rule.get("action") or "all") not in {action, "all"}:
            continue
        if not _is_rule_active(rule, now=now):
            continue
        conditions = rule.get("conditions") if isinstance(rule.get("conditions"), dict) else {}
        if not _conditions_match(conditions, now=now, context=context):
            continue
        if target or domain:
            if not _matches_rule_target(rule, target, text=text, domain=domain):
                continue
        rules.append(dict(rule))
    return sorted(rules, key=lambda item: int(item.get("priority") or 0), reverse=True)


def is_adaptive_preference_suppressed(
    target: str,
    *,
    action: str = "announce",
    text: str = "",
    now: datetime | None = None,
    context: dict[str, Any] | str | None = None,
) -> bool:
    rules = _active_rules_for(target=target, kind="suppress", action=action, text=text, now=now, context=context)
    if rules:
        _remember_last_applied(rules[0], reason=f"bloqueou {target}:{action}")
        return True
    return False


def remember_adaptive_suppression(raw_text: str, *, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    normalized = _normalize(raw_text)
    target, label = _target_from_text(normalized)
    if target == "studies" and any(re.search(rf"\b{re.escape(_normalize(alias))}\b", normalized) for alias in TARGET_ALIASES["training"]):
        target, label = "training", TARGET_LABELS["training"]
    action = _action_from_text(normalized, target)
    scope, starts_at, expires_at = _scope_from_text(normalized, now)
    conditions, condition_label = _condition_from_text(normalized)
    rule_id = f"{target}:{action}:{starts_at or 'now'}:{expires_at or 'open'}:{re.sub(r'[^a-z0-9]+', '_', condition_label).strip('_') or 'always'}"
    rule = _base_rule(
        rule_id=rule_id,
        kind="suppress",
        target=target,
        label=label,
        action=action,
        raw_text=raw_text,
        now=now,
        scope=scope,
        starts_at=starts_at,
        expires_at=expires_at,
        priority=50 if scope == "permanente" else 70,
        conditions=conditions,
    )

    def apply(data: dict) -> dict:
        rules = [item for item in data.get("rules") or [] if not (isinstance(item, dict) and item.get("id") == rule_id)]
        rules.append(rule)
        data["rules"] = rules[-120:]
        return data

    _update(apply)
    remember_operational_preference(f"Preferencia adaptativa: evitar {label}{condition_label} ({scope}).")
    return rule


def remember_adaptive_rule(raw_text: str, *, now: datetime | None = None) -> dict | None:
    now = now or datetime.now()
    normalized = _normalize(raw_text)
    scope, starts_at, expires_at = _scope_from_text(normalized, now)
    conditions, condition_label = _condition_from_text(normalized)

    if "professor" in normalized and any(term in normalized for term in ("estud", "aula", "prova", "materia")):
        rule_id = f"studies:teacher_tone:{starts_at or 'now'}:{expires_at or 'open'}:{re.sub(r'[^a-z0-9]+', '_', condition_label).strip('_') or 'always'}"
        rule = _base_rule(
            rule_id=rule_id,
            kind="response_tone",
            target="studies",
            label="tom professor em estudos",
            action="respond",
            value={"style": "teacher", "instruction": "explicar como professor, com passos curtos e pergunta de checagem"},
            raw_text=raw_text,
            now=now,
            scope=scope,
            starts_at=starts_at,
            expires_at=expires_at,
            priority=60,
            conditions=conditions,
        )
    elif any(term in normalized for term in ("indo para academia", "vou para academia", "fui para academia", "marque os dias que eu fui")):
        rule_id = f"training:attendance:{starts_at or 'now'}:{expires_at or 'open'}"
        rule = _base_rule(
            rule_id=rule_id,
            kind="tracking",
            target="training",
            label="registro de idas a academia",
            action="track",
            value={"track": "gym_attendance"},
            raw_text=raw_text,
            now=now,
            scope=scope,
            starts_at=starts_at,
            expires_at=expires_at,
            priority=45,
        )
    else:
        return None

    def apply(data: dict) -> dict:
        rules = [item for item in data.get("rules") or [] if not (isinstance(item, dict) and item.get("id") == rule_id)]
        rules.append(rule)
        data["rules"] = rules[-120:]
        return data

    _update(apply)
    remember_operational_preference(f"Regra adaptativa: {rule['label']}{condition_label} ({scope}).")
    return rule


def _briefing_section_from_text(normalized: str) -> tuple[str, str]:
    for section, aliases in BRIEFING_SECTION_ALIASES.items():
        if any(re.search(rf"\b{re.escape(_normalize(alias))}\b", normalized) for alias in aliases):
            return section, BRIEFING_SECTION_LABELS.get(section, section)
    return "", ""


def _briefing_sections_in_text(normalized: str) -> list[str]:
    found: list[tuple[int, str]] = []
    for section, aliases in BRIEFING_SECTION_ALIASES.items():
        positions = []
        for alias in aliases:
            match = re.search(rf"\b{re.escape(_normalize(alias))}\b", normalized)
            if match:
                positions.append(match.start())
        if positions:
            found.append((min(positions), section))
    ordered = []
    for _position, section in sorted(found):
        if section not in ordered:
            ordered.append(section)
    return ordered


def _extract_briefing_order(raw_text: str) -> list[str]:
    normalized = _normalize(raw_text)
    if "ordem" not in normalized and "sequencia" not in normalized:
        return []
    match = re.search(r"\b(?:ordem|sequencia)\b\s*:?\s*(.+)$", normalized)
    tail = match.group(1) if match else normalized
    sections = _briefing_sections_in_text(tail)
    return sections if len(sections) >= 2 else []


def _extract_briefing_custom_note(raw_text: str) -> str:
    raw = _compact(raw_text)
    patterns = (
        r"\b(?:adiciona|adicione|inclui|inclua|coloca|coloque)\s+(.+?)\s+(?:no|ao|na)\s+briefing\b",
        r"\bbriefing\s+(?:com|incluindo)\s+(.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.I)
        if match:
            note = _compact(match.group(1))
            note = re.sub(r"\b(?:tambem|tambem|por favor|pfv)\b", " ", note, flags=re.I).strip()
            return note[:120]
    return ""


def remember_briefing_layout_rule(raw_text: str, *, now: datetime | None = None) -> dict | None:
    now = now or datetime.now()
    normalized = _normalize(raw_text)

    scope, starts_at, expires_at = _scope_from_text(normalized, now)
    conditions, condition_label = _condition_from_text(normalized)
    ordered_sections = _extract_briefing_order(raw_text)
    section, section_label = _briefing_section_from_text(normalized)
    has_briefing_subject = "briefing" in normalized or "resumo do dia" in normalized or "panorama do dia" in normalized
    has_implicit_briefing_section = section in {"focus"}
    if not has_briefing_subject and not has_implicit_briefing_section:
        return None

    remove_markers = (
        "tira",
        "tirar",
        "retira",
        "retirar",
        "remove",
        "remover",
        "sem ",
        "nao coloca",
        "nao inclua",
        "nao quero",
        "nao informe",
        "nao me informe",
        "pode parar",
        "pare de",
        "parar de",
        "para de",
    )
    add_markers = ("adiciona", "adicione", "inclui", "inclua", "coloca", "coloque")

    if ordered_sections:
        action = "set_order"
        value = {"sections": ordered_sections}
        labels = [BRIEFING_SECTION_LABELS.get(item, item) for item in ordered_sections]
        label = "ordem do briefing: " + ", ".join(labels)
        priority = 80
    elif section and any(marker in normalized for marker in remove_markers):
        action = "remove_section"
        value = {"section": section}
        label = f"remover {section_label} do briefing"
        priority = 75
    elif section and "primeiro" in normalized:
        action = "reorder_section"
        value = {"section": section, "position": "first"}
        label = f"{section_label} primeiro no briefing"
        priority = 65
    elif any(marker in normalized for marker in add_markers):
        note = _extract_briefing_custom_note(raw_text)
        if not note or _briefing_section_from_text(_normalize(note))[0]:
            return None
        action = "add_note"
        value = {"text": note}
        label = f"adicionar {note} ao briefing"
        priority = 40
    else:
        return None

    label = label + condition_label
    rule_key = section or "_".join(value.get("sections") or []) or re.sub(r"[^a-z0-9]+", "_", str(value.get("text") or "note")).strip("_")
    rule_id = f"briefing:{action}:{rule_key}:{starts_at or 'now'}:{expires_at or 'open'}:{re.sub(r'[^a-z0-9]+', '_', condition_label).strip('_') or 'always'}"
    rule = _base_rule(
        rule_id=rule_id,
        kind="briefing_layout",
        target="briefing",
        label=label,
        action=action,
        value=value,
        raw_text=raw_text,
        now=now,
        scope=scope,
        starts_at=starts_at,
        expires_at=expires_at,
        priority=priority if scope == "permanente" else priority + 10,
        conditions=conditions,
    )

    def apply(data: dict) -> dict:
        rules = [item for item in data.get("rules") or [] if not (isinstance(item, dict) and item.get("id") == rule_id)]
        rules.append(rule)
        data["rules"] = rules[-120:]
        return data

    _update(apply)
    remember_operational_preference(f"Regra adaptativa do briefing: {label} ({scope}).")
    return rule


def _extract_identity_name(raw_text: str) -> str:
    raw = _compact(raw_text)
    patterns = (
        r"\b(?:muda|troca|alterar|altera|mudar|trocar)\s+(?:seu|teu)\s+nome\s+(?:para|pra|por)\s+(.+)$",
        r"\b(?:seu|teu)\s+nome\s+agora\s+(?:e|eh|vai\s+ser)\s+(.+)$",
        r"\ba\s+partir\s+de\s+agora\s+(?:voce\s+se\s+chama|seu\s+nome\s+e|teu\s+nome\s+e)\s+(.+)$",
        r"\b(?:quero|vou)\s+te\s+chamar\s+de\s+(.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.I)
        if match:
            name = _compact(match.group(1))
            name = re.sub(r"\b(?:por favor|pfv|ok|beleza)\b", " ", name, flags=re.I).strip()
            return name[:32]
    return ""


def create_pending_adaptation_candidate(raw_text: str, *, now: datetime | None = None) -> dict | None:
    now = now or datetime.now()
    normalized = _normalize(raw_text)
    requested_name = _extract_identity_name(raw_text)
    if requested_name and any(marker in normalized for marker in IDENTITY_CHANGE_MARKERS):
        candidate = {
            "id": f"candidate:identity_name:{now.isoformat(timespec='seconds')}",
            "kind": "change_assistant_name",
            "domain": "identity",
            "target": "identity",
            "label": f"mudar nome de apresentacao para {requested_name}",
            "status": "pending_confirmation",
            "priority": 95,
            "value": {"assistant_name": requested_name},
            "origin": {"source": "user_natural_language", "text": _compact(raw_text)},
            "source_text": _compact(raw_text),
            "created_at": now.isoformat(timespec="seconds"),
            "undo": {"natural": ["volta como era", "esquece essa regra", "volte a se chamar Axel"]},
        }

        def apply_identity(data: dict) -> dict:
            pending = [item for item in data.get("pending_candidates") or [] if item.get("status") == "pending_confirmation"]
            pending.append(candidate)
            data["pending_candidates"] = pending[-20:]
            return data

        _update(apply_identity)
        return candidate

    if not any(marker in normalized for marker in IMPORTANT_CHANGE_MARKERS):
        return None
    if not any(term in normalized for term in ("treino", "academia", "ficha", "plano")):
        return None

    candidate = {
        "id": f"candidate:training_plan:{now.isoformat(timespec='seconds')}",
        "kind": "replace_training_plan",
        "domain": "training",
        "target": "training",
        "label": "substituir plano de treino",
        "status": "pending_confirmation",
        "priority": 90,
        "origin": {"source": "user_natural_language", "text": _compact(raw_text)},
        "source_text": _compact(raw_text),
        "created_at": now.isoformat(timespec="seconds"),
        "undo": {"natural": ["volta como era", "esquece essa regra"], "requires_restore_snapshot": True},
    }

    def apply(data: dict) -> dict:
        pending = [item for item in data.get("pending_candidates") or [] if item.get("status") == "pending_confirmation"]
        pending.append(candidate)
        data["pending_candidates"] = pending[-20:]
        return data

    _update(apply)
    return candidate


def _latest_pending_candidate() -> dict | None:
    for item in reversed(_load().get("pending_candidates") or []):
        if item.get("status") == "pending_confirmation":
            return dict(item)
    return None


def resolve_pending_adaptation(raw_text: str, *, now: datetime | None = None) -> str | None:
    now = now or datetime.now()
    candidate = _latest_pending_candidate()
    if not candidate:
        return None

    normalized = _normalize(raw_text)
    if normalized not in CONFIRM_YES and normalized not in CONFIRM_NO:
        return None

    accepted = normalized in CONFIRM_YES

    def apply(data: dict) -> dict:
        for item in data.get("pending_candidates") or []:
            if item.get("id") == candidate.get("id"):
                item["status"] = "accepted" if accepted else "cancelled"
                item["resolved_at"] = now.isoformat(timespec="seconds")
        if accepted:
            if candidate.get("kind") == "change_assistant_name":
                value = candidate.get("value") if isinstance(candidate.get("value"), dict) else {}
                name = str(value.get("assistant_name") or "").strip()
                rule = _base_rule(
                    rule_id="identity:assistant_name:confirmed",
                    kind="identity",
                    target="identity",
                    label=f"nome de apresentacao {name}",
                    action="present",
                    value={"assistant_name": name},
                    raw_text=str(candidate.get("source_text") or ""),
                    now=now,
                    scope="permanente",
                    starts_at="",
                    expires_at="",
                    priority=95,
                )
            else:
                rule = _base_rule(
                    rule_id="training:plan_replacement:pending_confirmed",
                    kind="pending_change_accepted",
                    target="training",
                    label="substituicao de plano de treino confirmada",
                    action="replace_plan",
                    value={"candidate_id": candidate.get("id")},
                    raw_text=str(candidate.get("source_text") or ""),
                    now=now,
                    scope="permanente",
                    starts_at="",
                    expires_at="",
                    priority=90,
                )
            data["rules"] = [
                item
                for item in data.get("rules") or []
                if not (
                    isinstance(item, dict)
                    and item.get("target") == rule.get("target")
                    and item.get("kind") == rule.get("kind")
                    and item.get("action") == rule.get("action")
                )
            ]
            data["rules"].append(rule)
            data["last_applied"] = {
                "rule_id": rule.get("id"),
                "label": rule.get("label"),
                "domain": rule.get("domain"),
                "kind": rule.get("kind"),
                "reason": "confirmacao de mudanca importante",
                "source_text": rule.get("source_text"),
                "origin": rule.get("origin") or {},
                "undo": rule.get("undo") or {},
                "applied_at": now.isoformat(timespec="seconds"),
            }
        return data

    _update(apply)
    if accepted:
        if candidate.get("kind") == "change_assistant_name":
            name = str(((candidate.get("value") or {}).get("assistant_name")) or "").strip()
            return f"Confirmado. Vou me apresentar como {name}. Para desfazer, diga 'volta como era'."
        return "Confirmado. Deixei a mudanca do plano de treino registrada como aprovada para aplicacao supervisionada."
    return "Certo. Cancelei essa mudanca pendente e mantive o plano como estava."


def restore_adaptive_preference(raw_text: str, *, now: datetime | None = None) -> dict | None:
    now = now or datetime.now()
    normalized = _normalize(raw_text)
    target, _label = _target_from_text(normalized)
    generic_undo = any(marker in normalized for marker in ("volta como era", "esquece essa regra", "desfaz essa regra"))
    changed: dict | None = None

    def apply(data: dict) -> dict:
        nonlocal changed
        for rule in reversed(data.get("rules") or []):
            if not isinstance(rule, dict) or not bool(rule.get("enabled", True)):
                continue
            if generic_undo or _matches_rule_target(rule, target, text=raw_text):
                rule["enabled"] = False
                rule["disabled_at"] = now.isoformat(timespec="seconds")
                rule["disabled_by"] = _compact(raw_text)
                changed = dict(rule)
                break
        return data

    _update(apply)
    return changed


def adaptive_rules_for_domain(domain: str, *, text: str = "", now: datetime | None = None) -> list[dict]:
    return _active_rules_for(domain=str(domain or "").strip(), text=text, now=now)


def adaptive_response_tone_instruction(context: str, *, now: datetime | None = None) -> str | None:
    now = now or datetime.now()
    normalized = _normalize(context)
    active_context = get_current_adaptive_context(now=now)
    explicit_study = any(term in normalized for term in ("estud", "aula", "prova", "materia"))
    live_context = str(active_context.get("context") or "").strip()
    domain = "studies" if explicit_study or live_context == "studies" else "response_tone"
    rule_context = "studies" if explicit_study or live_context == "studies" else live_context or None
    rules = _active_rules_for(domain=domain, kind="response_tone", action="respond", text=context, now=now, context=rule_context)
    if not rules:
        return None
    rule = rules[0]
    _remember_last_applied(rule, reason="ajustou o tom da resposta")
    value = rule.get("value") if isinstance(rule.get("value"), dict) else {}
    return str(value.get("instruction") or "").strip() or None


def get_adaptive_assistant_name(*, now: datetime | None = None, default: str = "Axel") -> str:
    rules = _active_rules_for(target="identity", kind="identity", action="present", now=now)
    if not rules:
        return default
    rule = rules[0]
    value = rule.get("value") if isinstance(rule.get("value"), dict) else {}
    name = str(value.get("assistant_name") or "").strip()
    if not name:
        return default
    _remember_last_applied(rule, reason="respondeu identidade adaptada")
    return name


def apply_adaptive_briefing_layout(
    sections: list[dict],
    *,
    now: datetime | None = None,
    context: dict[str, Any] | str | None = None,
) -> list[dict]:
    now = now or datetime.now()
    current = [dict(section) for section in sections if isinstance(section, dict)]
    if context is None:
        active_context = get_current_adaptive_context(now=now)
        context = active_context.get("context") if active_context else None
    rules = _active_rules_for(target="briefing", kind="briefing_layout", now=now, context=context)
    if not rules:
        return current

    for rule in rules:
        if not _conditions_match(rule.get("conditions") if isinstance(rule.get("conditions"), dict) else {}, now=now, context=context):
            continue
        action = str(rule.get("action") or "").strip()
        value = rule.get("value") if isinstance(rule.get("value"), dict) else {}
        if action == "set_order":
            ordered_ids = [str(item).strip() for item in value.get("sections") or [] if str(item).strip()]
            ordered = []
            for section_id in ordered_ids:
                ordered.extend([section for section in current if str(section.get("id") or "") == section_id])
            rest = [section for section in current if str(section.get("id") or "") not in set(ordered_ids)]
            if ordered:
                current = ordered + rest
                _remember_last_applied(rule, reason="reordenou briefing por sequencia completa")
        elif action == "remove_section":
            target_section = str(value.get("section") or "").strip()
            if target_section:
                current = [section for section in current if str(section.get("id") or "") != target_section]
                _remember_last_applied(rule, reason=f"removeu secao {target_section} do briefing")
        elif action == "reorder_section" and value.get("position") == "first":
            target_section = str(value.get("section") or "").strip()
            moving = [section for section in current if str(section.get("id") or "") == target_section]
            rest = [section for section in current if str(section.get("id") or "") != target_section]
            if moving:
                current = moving + rest
                _remember_last_applied(rule, reason=f"reordenou secao {target_section} do briefing")
        elif action == "add_note":
            text = _compact(str(value.get("text") or ""))
            if text:
                current.append({"id": f"custom_{abs(hash(text))}", "text": text})
                _remember_last_applied(rule, reason="adicionou nota customizada ao briefing")
    return current


def apply_adaptive_response_tone(response: str, context: str, *, now: datetime | None = None) -> str:
    instruction = adaptive_response_tone_instruction(context, now=now)
    text = str(response or "").strip()
    if not instruction or not text:
        return text
    if "pergunta de checagem" in instruction and "Me diga" not in text and "Se voce" not in text:
        return f"{text} Me diga onde travar que eu explico passo a passo."
    return text


def explain_adaptive_behavior(*, now: datetime | None = None) -> str:
    data = _load()
    last = data.get("last_applied") or {}
    if last:
        label = last.get("label") or "uma regra adaptativa"
        source = ((last.get("origin") or {}).get("text") or last.get("source_text") or "pedido anterior")
        undo = ", ".join((last.get("undo") or {}).get("natural") or ["volta como era", "esquece essa regra"])
        return f"Eu me adaptei por causa da regra '{label}', criada a partir de: '{source}'. Para desfazer, diga: {undo}."

    active = list_adaptive_preferences(now=now)
    if not active:
        return "Nao encontrei regra adaptativa ativa agora. Se eu ajustei algo, foi pelo contexto da conversa, nao por memoria salva."
    rule = active[0]
    undo = ", ".join((rule.get("undo") or {}).get("natural") or ["volta como era", "esquece essa regra"])
    return f"Existe uma regra ativa: '{rule.get('label')}'. Ela veio de: '{rule.get('source_text')}'. Para desfazer, diga: {undo}."


def maybe_handle_adaptive_preference_request(raw_text: str, *, now: datetime | None = None) -> str | None:
    now = now or datetime.now()
    normalized = _normalize(raw_text)
    if not normalized:
        return None

    pending_resolution = resolve_pending_adaptation(raw_text, now=now)
    if pending_resolution:
        return pending_resolution

    if any(marker in normalized for marker in EXPLAIN_MARKERS):
        return explain_adaptive_behavior(now=now)

    context_response = maybe_handle_adaptive_context_request(raw_text, now=now)
    if context_response:
        return context_response

    has_restore = any(marker in normalized for marker in RESTORE_MARKERS)
    has_suppress = any(marker in normalized for marker in SUPPRESS_MARKERS)
    has_adaptable_subject = any(
        alias in normalized
        for aliases in TARGET_ALIASES.values()
        for alias in (_normalize(item) for item in aliases)
    )

    if has_restore and not has_suppress:
        restored = restore_adaptive_preference(raw_text, now=now)
        if not restored:
            return "Entendi a preferencia, mas nao encontrei uma regra adaptativa ativa para isso."
        if str(restored.get("kind") or "") == "suppress":
            return f"Entendi. Voltei a permitir {restored.get('label') or 'isso'}."
        return f"Entendi. Desfiz a regra de {restored.get('label') or 'adaptacao'}."

    candidate = create_pending_adaptation_candidate(raw_text, now=now)
    if candidate:
        if candidate.get("kind") == "change_assistant_name":
            return "Isso muda minha identidade de apresentacao. Criei uma mudanca pendente; confirme com 'sim' para aplicar ou 'nao' para manter como esta."
        return "Isso muda o plano de treino. Criei uma mudanca pendente; confirme com 'sim' para aplicar ou 'nao' para manter como esta."

    briefing_rule = remember_briefing_layout_rule(raw_text, now=now)
    if briefing_rule:
        label = str(briefing_rule.get("label") or "o formato do briefing")
        scope = str(briefing_rule.get("scope") or "permanente")
        if scope == "permanente":
            return f"Entendi. Vou ajustar o briefing: {label}."
        return f"Entendi. Vou ajustar o briefing {scope}: {label}."

    if has_suppress and has_adaptable_subject:
        rule = remember_adaptive_suppression(raw_text, now=now)
        label = str(rule.get("label") or "isso")
        scope = str(rule.get("scope") or "permanente")
        if scope == "permanente":
            return f"Entendi. Vou evitar {label} daqui em diante."
        return f"Entendi. Vou evitar {label} {scope}."

    rule = remember_adaptive_rule(raw_text, now=now)
    if rule:
        label = str(rule.get("label") or "essa adaptacao")
        scope = str(rule.get("scope") or "permanente")
        if scope == "permanente":
            return f"Entendi. Vou usar {label} daqui em diante."
        return f"Entendi. Vou usar {label} {scope}."

    return None


def list_adaptive_preferences(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    return [dict(rule) for rule in _load().get("rules") or [] if _is_rule_active(rule, now=now)]
