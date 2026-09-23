from __future__ import annotations

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from memory.json_store import read_json_file

SECTION_PREFERENCES = "preferencias_usuario"
SECTION_ADAPTIVE_RULES = "regras_adaptativas"
SECTION_CURRENT_CONTEXT = "contexto_atual"
SECTION_ACTIVE_DOMAINS = "projetos_dominios_ativos"
SECTION_ROUTINE = "rotina_habitos"
SECTION_EPISODIC = "historico_episodico"
SECTION_OBSERVATIONS = "observacoes_importantes"
SECTION_PENDING = "pendencias_proximos_passos"

SECTIONS = (
    SECTION_PREFERENCES,
    SECTION_ADAPTIVE_RULES,
    SECTION_CURRENT_CONTEXT,
    SECTION_ACTIVE_DOMAINS,
    SECTION_ROUTINE,
    SECTION_EPISODIC,
    SECTION_OBSERVATIONS,
    SECTION_PENDING,
)

DOMAIN_ALIASES = {
    "treino": {"treino", "treinos", "training", "academia", "exercicio", "calistenia"},
    "estudos": {"estudo", "estudos", "study", "revisao", "revisoes", "aula"},
    "investimentos": {"investimento", "investimentos", "carteira", "ticker", "watchlist", "preco teto"},
    "programacao": {"programacao", "programming", "codigo", "codex", "axel", "dev", "projeto"},
    "rotina": {"rotina", "habito", "habitos", "agenda", "lembrete", "briefing", "aviso", "avisos"},
    "voz": {"voz", "tts", "hotword", "audio", "microfone"},
    "operacional": {"operacional", "contexto", "preferencia", "preferencias"},
}

VOICE_PREFERENCE_KEYS = {
    "assistant_style": ("Estilo de resposta do Axel", "operacional", "media"),
    "assistant_address_user": ("Forma de tratamento do usuario", "operacional", "media"),
    "assistant_brief_confirmations": ("Confirmacoes breves", "operacional", "media"),
    "assistant_humor_enabled": ("Humor habilitado", "operacional", "baixa"),
    "assistant_humor_style": ("Estilo de humor", "operacional", "baixa"),
    "assistant_humor_level": ("Nivel de humor", "operacional", "baixa"),
    "assistant_personality_enabled": ("Personalidade habilitada", "operacional", "media"),
    "assistant_proactivity_enabled": ("Proatividade habilitada", "rotina", "media"),
    "startup_briefing_enabled": ("Briefing inicial habilitado", "rotina", "media"),
    "chat_model": ("Modelo de chat preferido", "programacao", "baixa"),
    "tts_engine": ("Motor de voz preferido", "voz", "media"),
    "tts_voice_name": ("Voz TTS preferida", "voz", "baixa"),
    "gemini_tts_voice_name": ("Voz Gemini TTS preferida", "voz", "baixa"),
    "hotword": ("Palavra de ativacao", "voz", "media"),
    "trigger_hotkey": ("Atalho de comando", "voz", "baixa"),
    "toggle_listening_hotkey": ("Atalho de escuta continua", "voz", "baixa"),
}

ACTION_LABELS = {
    "announce": "avisar",
    "run": "executar",
    "all": "aplicar a tudo",
}


def _compact(text: Any, limit: int = 220) -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip(" .,:;-")
    if len(clean) > limit:
        return clean[: max(0, limit - 3)].rstrip() + "..."
    return clean


def _normalize(text: Any) -> str:
    lowered = str(text or "").lower()
    lowered = re.sub(r"[^\w\s/-]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _timestamp_from_path(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    except Exception:
        return ""


def _iso_from_epoch(value: Any) -> str:
    try:
        timestamp = float(value or 0)
    except Exception:
        return ""
    if timestamp <= 0:
        return ""
    return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")


def _metadata(
    *,
    source: str,
    date: str = "",
    validity: str = "durable",
    confidence: float = 0.7,
    scope: str = "global",
    priority: str = "media",
    reason: str = "",
    undo: str = "",
) -> dict:
    return {
        "origem": source,
        "data": date,
        "validade": validity,
        "confianca": round(float(confidence), 2),
        "escopo": scope,
        "prioridade": priority,
        "motivo": reason,
        "desfazer": undo,
    }


def _item(
    section: str,
    text: str,
    *,
    source: str,
    domain: str = "operacional",
    item_id: str = "",
    date: str = "",
    validity: str = "durable",
    confidence: float = 0.7,
    scope: str = "global",
    priority: str = "media",
    reason: str = "",
    undo: str = "",
    raw_ref: str = "",
) -> dict:
    clean = _compact(text)
    return {
        "id": item_id or f"{source}:{section}:{domain}:{_normalize(clean)[:80]}",
        "secao": section,
        "dominio": domain,
        "texto": clean,
        "metadados": _metadata(
            source=source,
            date=date,
            validity=validity,
            confidence=confidence,
            scope=scope,
            priority=priority,
            reason=reason,
            undo=undo,
        ),
        "referencia": raw_ref,
    }


def _empty_view() -> dict:
    return {
        "generated_at": time.time(),
        "sections": {section: [] for section in SECTIONS},
        "conflicts": [],
        "summary": "",
    }


def _add(view: dict, item: dict) -> None:
    view["sections"].setdefault(item["secao"], []).append(item)


def _read_voice_preferences(view: dict) -> None:
    try:
        from memory.voice_preferences import FILE, load_voice_preferences

        preferences = load_voice_preferences() or {}
        date = _timestamp_from_path(FILE)
    except Exception:
        return

    for key, (label, domain, priority) in VOICE_PREFERENCE_KEYS.items():
        value = preferences.get(key)
        if value in ("", None):
            continue
        _add(
            view,
            _item(
                SECTION_PREFERENCES,
                f"{label}: {value}",
                source="memory/voice_preferences.json",
                domain=domain,
                item_id=f"voice_preferences:{key}",
                date=date,
                confidence=0.85,
                scope=domain,
                priority=priority,
                reason="preferencia operacional carregada do arquivo de voz/configuracao",
                undo=f"alterar/remover a chave {key} em voice_preferences",
                raw_ref=key,
            ),
        )


def _read_operational_memory(view: dict) -> None:
    try:
        from memory.operational_context import OPERATIONAL_MEMORY_PATH, load_operational_memory

        memory = load_operational_memory() or {}
        date = _iso_from_epoch(memory.get("updated_at")) or _timestamp_from_path(OPERATIONAL_MEMORY_PATH)
    except Exception:
        return

    for index, text in enumerate(memory.get("preferences") or []):
        clean = _compact(text)
        if not clean:
            continue
        domain = infer_domain(clean) or "operacional"
        _add(
            view,
            _item(
                SECTION_PREFERENCES,
                clean,
                source="memory/operational_memory.json",
                domain=domain,
                item_id=f"operational_memory:preference:{index}",
                date=date,
                confidence=0.8,
                scope=domain,
                priority="media",
                reason="preferencia operacional salva explicitamente",
                undo="usar esquecer preferencia operacional ou editar operational_memory.json",
            ),
        )

    for index, text in enumerate(memory.get("notes") or []):
        clean = _compact(text)
        if not clean:
            continue
        domain = infer_domain(clean) or "operacional"
        _add(
            view,
            _item(
                SECTION_OBSERVATIONS,
                clean,
                source="memory/operational_memory.json",
                domain=domain,
                item_id=f"operational_memory:note:{index}",
                date=date,
                confidence=0.72,
                scope=domain,
                priority="media",
                reason="nota operacional salva",
                undo="remover a nota de operational_memory.json",
            ),
        )


def _read_adaptive_preferences(view: dict) -> None:
    try:
        from memory.adaptive_preferences import ADAPTIVE_PREFERENCES_PATH

        data = read_json_file(ADAPTIVE_PREFERENCES_PATH, {"rules": []}, validator=lambda value: isinstance(value, dict))
    except Exception:
        return

    for rule in data.get("rules") or []:
        if not isinstance(rule, dict):
            continue
        target = str(rule.get("target") or "").strip() or "custom"
        domain = _domain_from_adaptive_target(target)
        action = str(rule.get("action") or "announce").strip()
        label = str(rule.get("label") or target).strip()
        enabled = bool(rule.get("enabled", True))
        scope = str(rule.get("scope") or target).strip() or target
        expires_at = str(rule.get("expires_at") or "").strip()
        validity = f"ate {expires_at}" if expires_at else ("ativa" if enabled else "desativada")
        text = f"Regra adaptativa: evitar {ACTION_LABELS.get(action, action)} {label}"
        if not enabled:
            text += " (desativada)"
        _add(
            view,
            _item(
                SECTION_ADAPTIVE_RULES,
                text,
                source="memory/adaptive_preferences.json",
                domain=domain,
                item_id=str(rule.get("id") or f"adaptive:{target}:{action}"),
                date=str(rule.get("created_at") or ""),
                validity=validity,
                confidence=0.9 if enabled else 0.65,
                scope=scope,
                priority="alta" if enabled else "baixa",
                reason=str(rule.get("source_text") or "pedido adaptativo do usuario"),
                undo=f"pedir para voltar a permitir {label}",
                raw_ref=str(rule.get("id") or ""),
            ),
        )


def _read_operational_context(view: dict) -> None:
    try:
        from memory.operational_context import OPERATIONAL_CONTEXT_PATH

        context = read_json_file(OPERATIONAL_CONTEXT_PATH, {}, validator=lambda value: isinstance(value, dict))
    except Exception:
        return

    date = _iso_from_epoch(context.get("generated_at"))
    summary = _compact(context.get("summary"), limit=260)
    if summary:
        _add(
            view,
            _item(
                SECTION_CURRENT_CONTEXT,
                summary,
                source="memory/operational_context.json",
                domain="operacional",
                item_id="operational_context:summary",
                date=date,
                validity="curta",
                confidence=0.72,
                scope="sessao/operacional",
                priority="media",
                reason="sintese operacional atual gerada a partir de estado local",
            ),
        )

    current_focus = _compact(context.get("current_focus"))
    if current_focus:
        _add(
            view,
            _item(
                SECTION_ACTIVE_DOMAINS,
                f"Foco atual: {current_focus}",
                source="memory/operational_context.json",
                domain=infer_domain(current_focus) or "programacao",
                item_id="operational_context:current_focus",
                date=date,
                validity="curta",
                confidence=0.7,
                scope="operacional",
                priority="alta",
                reason="foco atual consolidado pelo contexto operacional",
            ),
        )

    for index, task in enumerate(context.get("open_tasks") or []):
        clean = _compact(task)
        if clean:
            _add(
                view,
                _item(
                    SECTION_PENDING,
                    clean,
                    source="memory/todo.md",
                    domain=infer_domain(clean) or "operacional",
                    item_id=f"operational_context:open_task:{index}",
                    date=date,
                    validity="ate concluir/remover",
                    confidence=0.75,
                    scope="operacional",
                    priority="media",
                    reason="tarefa aberta no contexto operacional",
                    undo="marcar como concluida ou remover de memory/todo.md",
                ),
            )


def _read_long_memory(view: dict) -> None:
    try:
        from memory.long_memory import load_long_memory

        data = load_long_memory() or {}
    except Exception:
        return

    for item in data.get("items") or []:
        if not isinstance(item, dict):
            continue
        fact = _compact(item.get("fact"))
        if not fact:
            continue
        category = str(item.get("category") or "context").strip()
        section = {
            "preference": SECTION_PREFERENCES,
            "project": SECTION_ACTIVE_DOMAINS,
            "future": SECTION_PENDING,
            "decision": SECTION_OBSERVATIONS,
            "context": SECTION_OBSERVATIONS,
        }.get(category, SECTION_OBSERVATIONS)
        _add(
            view,
            _item(
                section,
                fact,
                source="memory/long_memory.json",
                domain=infer_domain(f"{category} {fact}") or "operacional",
                item_id=str(item.get("id") or ""),
                date=_iso_from_epoch(item.get("updated_at") or item.get("created_at")),
                validity=str(item.get("validity") or "durable"),
                confidence=float(item.get("confidence") or 0.7),
                scope=category,
                priority="alta" if category in {"preference", "decision", "project"} else "media",
                reason=str(item.get("reason") or "memoria longa consultavel"),
                undo="remover/limpar item correspondente em long_memory.json",
                raw_ref=str(item.get("id") or ""),
            ),
        )


def _read_episodic_memory(view: dict) -> None:
    try:
        from memory.episodic_memory import latest_episode

        episode = latest_episode() or {}
    except Exception:
        return

    summary = _compact(episode.get("summary"))
    if not summary:
        return
    _add(
        view,
        _item(
            SECTION_EPISODIC,
            summary,
            source="memory/episodes.json",
            domain=infer_domain(" ".join([summary, " ".join(episode.get("keywords") or [])])) or "operacional",
            item_id=str(episode.get("id") or "latest_episode"),
            date=str(episode.get("date") or _iso_from_epoch(episode.get("updated_at"))),
            validity="historica",
            confidence=0.68,
            scope="sessao",
            priority="media",
            reason="ultimo resumo episodico salvo",
            undo="remover ou regenerar o episodio em memory/episodes.json",
        ),
    )
    for index, step in enumerate(episode.get("next_steps") or []):
        clean = _compact(step)
        if clean:
            _add(
                view,
                _item(
                    SECTION_PENDING,
                    clean,
                    source="memory/episodes.json",
                    domain=infer_domain(clean) or "operacional",
                    item_id=f"{episode.get('id') or 'latest_episode'}:next:{index}",
                    date=str(episode.get("date") or ""),
                    validity="ate revisar",
                    confidence=0.64,
                    scope="sessao",
                    priority="media",
                    reason="proximo passo extraido de memoria episodica",
                    undo="atualizar/remover o episodio em memory/episodes.json",
                ),
            )


def _read_training(view: dict) -> None:
    try:
        from memory.training import training_snapshot

        snap = training_snapshot()
    except Exception:
        return

    workout = snap.get("workout") or {}
    reminder = snap.get("reminder") or {}
    today = str(snap.get("today") or "")
    if workout:
        title = _compact(workout.get("title"))
        label = _compact(workout.get("label"))
        status = "concluido" if snap.get("completed_today") else "ativo"
        if title:
            _add(
                view,
                _item(
                    SECTION_CURRENT_CONTEXT,
                    f"Treino de hoje: {label}, {title}. Status: {status}",
                    source="memory/training.json",
                    domain="treino",
                    item_id=f"training:today:{today}",
                    date=today,
                    validity="hoje",
                    confidence=0.82,
                    scope="treino",
                    priority="alta",
                    reason="snapshot local do plano de treino",
                ),
            )
    if reminder:
        _add(
            view,
            _item(
                SECTION_ROUTINE,
                f"Lembrete de treino: enabled={bool(reminder.get('enabled'))}, horario={reminder.get('time', '')}",
                source="memory/training.json",
                domain="treino",
                item_id="training:reminder",
                date=today,
                validity="enquanto configurado",
                confidence=0.85,
                scope="treino/rotina",
                priority="alta" if reminder.get("enabled") else "media",
                reason="configuracao local do lembrete de treino",
                undo="ajustar ou desativar lembrete em memory/training.json",
            ),
        )


def _read_study(view: dict) -> None:
    try:
        from memory.study import study_snapshot

        snap = study_snapshot()
    except Exception:
        return

    text = (
        f"Estudos hoje: {snap.get('minutes_today', 0)}/{snap.get('daily_minutes', 0)} min; "
        f"revisoes pendentes={len(snap.get('pending_reviews') or [])}; metas ativas={len(snap.get('goals') or [])}"
    )
    _add(
        view,
        _item(
            SECTION_CURRENT_CONTEXT,
            text,
            source="memory/study.json",
            domain="estudos",
            item_id=f"study:today:{snap.get('today', '')}",
            date=str(snap.get("today") or ""),
            validity="hoje",
            confidence=0.8,
            scope="estudos",
            priority="media",
            reason="snapshot local de estudos",
        ),
    )
    for index, review in enumerate(snap.get("pending_reviews") or []):
        if isinstance(review, dict) and _compact(review.get("text")):
            _add(
                view,
                _item(
                    SECTION_PENDING,
                    f"Revisao pendente: {_compact(review.get('text'))}",
                    source="memory/study.json",
                    domain="estudos",
                    item_id=f"study:review:{review.get('id') or index}",
                    date=str(review.get("created_at") or ""),
                    validity=str(review.get("due_at") or "ate concluir"),
                    confidence=0.82,
                    scope="estudos",
                    priority="alta",
                    reason="revisao de estudo pendente",
                    undo="concluir ou remover revisao em memory/study.json",
                ),
            )


def _read_investments(view: dict) -> None:
    try:
        from memory.investment_strategy import get_auto_ceiling_settings, load_investment_strategy

        strategy = load_investment_strategy() or {}
        ceiling = get_auto_ceiling_settings() or {}
    except Exception:
        return

    watchlist = [str(item).upper() for item in strategy.get("watchlist") or [] if str(item).strip()]
    if watchlist:
        _add(
            view,
            _item(
                SECTION_ACTIVE_DOMAINS,
                "Watchlist de investimentos: " + ", ".join(watchlist[:12]),
                source="memory/profile.py:financas.estrategia",
                domain="investimentos",
                item_id="investments:watchlist",
                validity="durable",
                confidence=0.78,
                scope="investimentos",
                priority="media",
                reason="estrategia local de investimentos",
                undo="remover ativos da watchlist",
            ),
        )
    if ceiling:
        _add(
            view,
            _item(
                SECTION_ADAPTIVE_RULES,
                (
                    "Preco-teto automatico: "
                    f"enabled={ceiling.get('enabled')}, metodo={ceiling.get('method')}, "
                    f"margem={ceiling.get('margin_percent')}%"
                ),
                source="memory/profile.py:financas.estrategia.preco_teto_automatico",
                domain="investimentos",
                item_id="investments:auto_ceiling",
                validity="durable",
                confidence=0.78,
                scope="investimentos",
                priority="media",
                reason="regra local de decisao para investimentos",
                undo="alterar configuracao de preco-teto automatico",
            ),
        )


def _domain_from_adaptive_target(target: str) -> str:
    target = str(target or "").strip()
    if target == "training":
        return "treino"
    if target in {"briefing", "notifications", "reminders", "agenda"}:
        return "rotina"
    if target == "investments":
        return "investimentos"
    return infer_domain(target) or "operacional"


def infer_domain(text: Any) -> str:
    normalized = _normalize(text)
    if not normalized:
        return ""
    for domain, aliases in DOMAIN_ALIASES.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", normalized) for alias in aliases):
            return domain
    return ""


def _detect_conflicts(view: dict) -> list[dict]:
    conflicts = []
    rules = view["sections"].get(SECTION_ADAPTIVE_RULES, [])
    preferences = view["sections"].get(SECTION_PREFERENCES, []) + view["sections"].get(SECTION_ROUTINE, [])
    active_suppressions = [
        item
        for item in rules
        if "evitar" in _normalize(item.get("texto")) and "(desativada)" not in _normalize(item.get("texto"))
    ]
    for rule in active_suppressions:
        rule_text = _normalize(rule.get("texto"))
        for pref in preferences:
            pref_text = _normalize(pref.get("texto"))
            if rule.get("dominio") != pref.get("dominio"):
                continue
            if "enabled=true" in pref_text or "habilitado: true" in pref_text or "habilitada: true" in pref_text:
                conflicts.append(
                    {
                        "dominio": rule.get("dominio"),
                        "itens": [rule.get("id"), pref.get("id")],
                        "descricao": "Ha uma regra adaptativa de supressao junto de uma preferencia/configuracao habilitada.",
                    }
                )
                continue
            if "briefing" in rule_text and "briefing inicial habilitado true" in pref_text:
                conflicts.append(
                    {
                        "dominio": rule.get("dominio"),
                        "itens": [rule.get("id"), pref.get("id")],
                        "descricao": "Briefing esta habilitado nas preferencias, mas uma regra adaptativa pode suprimi-lo.",
                    }
                )
    return conflicts


def _build_summary(view: dict, *, max_items: int = 8) -> str:
    candidates = []
    for section in (
        SECTION_ADAPTIVE_RULES,
        SECTION_PREFERENCES,
        SECTION_CURRENT_CONTEXT,
        SECTION_PENDING,
        SECTION_OBSERVATIONS,
    ):
        candidates.extend(view["sections"].get(section, []))
    priority_score = {"alta": 3, "media": 2, "baixa": 1}
    candidates.sort(
        key=lambda item: (
            priority_score.get(str((item.get("metadados") or {}).get("prioridade") or "media"), 2),
            float((item.get("metadados") or {}).get("confianca") or 0),
        ),
        reverse=True,
    )
    rows = []
    for item in candidates[: max(1, int(max_items))]:
        meta = item.get("metadados") or {}
        rows.append(
            f"{item.get('dominio')}/{item.get('secao')}: {item.get('texto')} "
            f"(origem {meta.get('origem')}, escopo {meta.get('escopo')})"
        )
    if view.get("conflicts"):
        rows.append(f"Conflitos sinalizados: {len(view['conflicts'])}.")
    return "Memoria profunda: " + " ; ".join(rows) + "." if rows else "Memoria profunda ainda sem itens relevantes."


def load_deep_memory(*, include_domain_sources: bool = True) -> dict:
    view = _empty_view()
    _read_voice_preferences(view)
    _read_operational_memory(view)
    _read_adaptive_preferences(view)
    _read_operational_context(view)
    _read_long_memory(view)
    _read_episodic_memory(view)
    if include_domain_sources:
        _read_training(view)
        _read_study(view)
        _read_investments(view)
    view["conflicts"] = _detect_conflicts(view)
    view["summary"] = _build_summary(view)
    return view


def iter_deep_memory_items(view: dict | None = None) -> list[dict]:
    memory = view or load_deep_memory()
    items = []
    for section in SECTIONS:
        items.extend(memory.get("sections", {}).get(section, []))
    return items


def query_deep_memory_by_domain(domain: str, *, limit: int = 12, view: dict | None = None) -> list[dict]:
    wanted = infer_domain(domain) or _normalize(domain)
    if not wanted:
        return []
    terms = DOMAIN_ALIASES.get(wanted, {wanted})
    results = []
    for item in iter_deep_memory_items(view):
        haystack = _normalize(f"{item.get('dominio')} {item.get('secao')} {item.get('texto')}")
        if item.get("dominio") == wanted or any(term in haystack for term in terms):
            results.append(item)
    priority_score = {"alta": 3, "media": 2, "baixa": 1}
    results.sort(
        key=lambda item: (
            priority_score.get(str((item.get("metadados") or {}).get("prioridade") or "media"), 2),
            float((item.get("metadados") or {}).get("confianca") or 0),
        ),
        reverse=True,
    )
    return results[: max(1, int(limit))]


def explain_memory_influence(query: str, *, limit: int = 8, view: dict | None = None) -> dict:
    memory = view or load_deep_memory()
    domain = infer_domain(query)
    query_terms = {token for token in _normalize(query).split() if len(token) >= 3}
    matches = []
    for item in iter_deep_memory_items(memory):
        haystack = _normalize(f"{item.get('dominio')} {item.get('secao')} {item.get('texto')} {(item.get('metadados') or {}).get('motivo')}")
        score = len(query_terms & set(haystack.split()))
        if domain and item.get("dominio") == domain:
            score += 3
        if score:
            matches.append({**item, "score": score})
    matches.sort(
        key=lambda item: (
            int(item.get("score") or 0),
            float((item.get("metadados") or {}).get("confianca") or 0),
        ),
        reverse=True,
    )
    conflicts = [
        conflict for conflict in memory.get("conflicts") or []
        if not domain or conflict.get("dominio") == domain
    ]
    return {
        "query": query,
        "domain": domain,
        "items": matches[: max(1, int(limit))],
        "conflicts": conflicts,
    }


def format_deep_memory_summary(query: str = "", *, limit: int = 6) -> str:
    if query:
        explanation = explain_memory_influence(query, limit=limit)
        items = explanation.get("items") or []
        if not items:
            return "Memoria profunda: nenhum item especifico influenciou esta pergunta."
        rows = []
        for item in items[: max(1, int(limit))]:
            meta = item.get("metadados") or {}
            rows.append(
                f"{item.get('dominio')}/{item.get('secao')}: {item.get('texto')} "
                f"(origem {meta.get('origem')}, conf {meta.get('confianca')}, escopo {meta.get('escopo')})"
            )
        if explanation.get("conflicts"):
            rows.append(f"Conflitos no dominio: {len(explanation['conflicts'])}.")
        return "Memoria profunda relevante: " + " ; ".join(rows) + "."
    return _build_summary(load_deep_memory(), max_items=limit)


def format_domain_memory(domain: str, *, limit: int = 8) -> str:
    items = query_deep_memory_by_domain(domain, limit=limit)
    if not items:
        return f"Nao encontrei memoria profunda para {domain}."
    rows = []
    for item in items:
        meta = item.get("metadados") or {}
        rows.append(
            f"{item.get('secao')}: {item.get('texto')} "
            f"[origem {meta.get('origem')}, validade {meta.get('validade')}, prioridade {meta.get('prioridade')}]"
        )
    return f"Memoria profunda de {domain}: " + " ; ".join(rows) + "."
