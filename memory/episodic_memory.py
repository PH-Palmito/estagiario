from __future__ import annotations

import json
import re
import time
from pathlib import Path

from memory.json_store import read_json_file, write_json_atomic

EPISODES_PATH = Path("memory/episodes.json")
EXECUTION_LOG_PATH = Path("memory/execution_log.jsonl")
MAX_EPISODES = 120

IMPORTANT_MARKERS = (
    "decidimos",
    "ficou decidido",
    "vamos fazer",
    "prioridade",
    "proximo passo",
    "próximo passo",
    "implementar",
    "criar",
    "corrigir",
    "salvar",
    "continuar",
)

STOPWORDS = {
    "para",
    "com",
    "sem",
    "que",
    "isso",
    "essa",
    "esse",
    "agora",
    "depois",
    "antes",
    "sobre",
    "como",
    "qual",
    "quais",
    "voce",
    "você",
    "axel",
    "pode",
    "vamos",
    "fazer",
    "entao",
    "então",
}


def _compact(text: str, limit: int = 220) -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip(" .")
    if len(clean) > limit:
        return clean[: max(0, limit - 3)].rstrip() + "..."
    return clean


def _read_recent_events(path: Path | None = None, limit: int = 120) -> list[dict]:
    log_path = path or EXECUTION_LOG_PATH
    if not log_path.exists():
        return []
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-max(1, int(limit)) :]
    except Exception:
        return []
    events = []
    for line in lines:
        try:
            item = json.loads(line)
        except Exception:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def _extract_keywords(texts: list[str], limit: int = 8) -> list[str]:
    scores: dict[str, int] = {}
    for text in texts:
        normalized = re.sub(r"[^\w\s/-]", " ", str(text or "").lower())
        for token in normalized.split():
            if len(token) < 4 or token.isdigit() or token in STOPWORDS:
                continue
            scores[token] = scores.get(token, 0) + 1
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [token for token, _score in ranked[:limit]]


def _turn_texts(turns: list[dict]) -> tuple[list[str], list[str]]:
    user_texts = []
    assistant_texts = []
    for item in turns:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        text = _compact(str(item.get("text", "")), limit=280)
        if not text:
            continue
        if role in {"user", "usuario", "usuário"}:
            user_texts.append(text)
        elif role in {"assistant", "axel"}:
            assistant_texts.append(text)
    return user_texts, assistant_texts


def _event_user_texts(events: list[dict]) -> list[str]:
    texts = []
    for event in events:
        if str(event.get("event") or "") != "user_input":
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        text = _compact(str(data.get("text") or data.get("message") or ""))
        if text:
            texts.append(text)
    return texts


def _important_points(user_texts: list[str], action_errors: list[dict], limit: int = 6) -> list[str]:
    points = []
    seen = set()
    for text in user_texts:
        lower = text.lower()
        if not any(marker in lower for marker in IMPORTANT_MARKERS):
            continue
        key = lower
        if key in seen:
            continue
        seen.add(key)
        points.append(text)
        if len(points) >= limit:
            break
    for item in action_errors:
        action = str(item.get("action") or "acao").strip()
        error = str(item.get("error") or "falha").strip()
        text = _compact(f"{action} falhou: {error}")
        if text.lower() not in seen:
            points.append(text)
            seen.add(text.lower())
        if len(points) >= limit:
            break
    return points


def _action_summary(events: list[dict]) -> tuple[list[dict], list[dict]]:
    actions = []
    errors = []
    for event in events:
        if str(event.get("event") or "") != "command_execute_end":
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        item = {
            "action": str(data.get("action") or "").strip(),
            "risk_level": str(data.get("risk_level") or "").strip(),
            "action_class": str(data.get("action_class") or "").strip(),
            "success": bool(data.get("success", True)),
            "duration_ms": data.get("duration_ms", 0),
            "error": str(data.get("error") or "").strip(),
        }
        if item["action"]:
            actions.append(item)
        if not item["success"] or item["error"]:
            errors.append(item)
    return actions[-8:], errors[-6:]


def _model_summary(events: list[dict]) -> dict:
    calls = []
    fallback_count = 0
    token_total = 0
    for event in events:
        if str(event.get("event") or "") != "model_call_end":
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if bool(data.get("fallback_used")):
            fallback_count += 1
        try:
            token_total += int(float(data.get("total_tokens_estimate") or 0))
        except Exception:
            pass
        calls.append(
            {
                "provider": str(data.get("provider") or "").strip(),
                "model": str(data.get("model") or "").strip(),
                "success": bool(data.get("success", True)),
                "fallback_used": bool(data.get("fallback_used")),
            }
        )
    return {
        "count": len(calls),
        "fallback_count": fallback_count,
        "tokens_estimate": token_total,
        "recent": calls[-4:],
    }


def build_episode_summary(
    *,
    session_id: str | None = None,
    turns: list[dict] | None = None,
    events: list[dict] | None = None,
    now: float | None = None,
) -> dict:
    from memory.session import recent_turns
    from memory.session_index import SESSION_ID

    current_time = float(now or time.time())
    sid = str(session_id or SESSION_ID)
    recent = turns if turns is not None else recent_turns(limit=16)
    log_events = events if events is not None else _read_recent_events(limit=160)
    turn_user_texts, assistant_texts = _turn_texts(list(recent or []))
    user_texts = turn_user_texts or _event_user_texts(log_events)
    actions, action_errors = _action_summary(log_events)
    model = _model_summary(log_events)
    keywords = _extract_keywords(user_texts + assistant_texts + [item.get("action", "") for item in actions])
    important = _important_points(user_texts, action_errors)

    if important:
        summary = "Pontos principais: " + "; ".join(important[:3]) + "."
    elif user_texts:
        summary = "Sessao focada em: " + "; ".join(user_texts[-3:]) + "."
    elif actions:
        summary = "Sessao com actions recentes: " + ", ".join(item["action"] for item in actions[-4:]) + "."
    else:
        summary = "Sessao sem atividade suficiente para resumir."

    next_steps = []
    for text in user_texts:
        lower = text.lower()
        if any(marker in lower for marker in {"continue", "continuar", "proximo", "próximo", "vamos fazer"}):
            next_steps.append(text)
    if not next_steps and action_errors:
        next_steps.append("Revisar falhas recentes antes de repetir a execucao.")

    return {
        "id": f"{sid}-{time.strftime('%Y%m%d', time.localtime(current_time))}",
        "session_id": sid,
        "date": time.strftime("%Y-%m-%d", time.localtime(current_time)),
        "created_at": current_time,
        "updated_at": current_time,
        "summary": summary,
        "important_points": important[:6],
        "keywords": keywords,
        "recent_user_requests": user_texts[-8:],
        "assistant_highlights": assistant_texts[-4:],
        "actions": actions,
        "action_errors": action_errors,
        "model": model,
        "next_steps": next_steps[-5:],
    }


def load_episodes(path: Path | None = None) -> dict:
    data = read_json_file(path or EPISODES_PATH, {"episodes": []}, validator=lambda value: isinstance(value, dict))
    episodes = data.get("episodes") if isinstance(data.get("episodes"), list) else []
    return {"updated_at": data.get("updated_at", 0.0), "episodes": [item for item in episodes if isinstance(item, dict)]}


def save_episode_summary(episode: dict | None = None, *, path: Path | None = None) -> dict:
    data = load_episodes(path)
    item = dict(episode or build_episode_summary())
    item["updated_at"] = time.time()
    episodes = [existing for existing in data.get("episodes", []) if existing.get("id") != item.get("id")]
    episodes.insert(0, item)
    payload = {"updated_at": time.time(), "episodes": episodes[:MAX_EPISODES]}
    write_json_atomic(path or EPISODES_PATH, payload, indent=2, trailing_newline=True)
    return item


def latest_episode(path: Path | None = None) -> dict:
    episodes = load_episodes(path).get("episodes") or []
    return dict(episodes[0]) if episodes else {}


def search_episodes(query: str, limit: int = 5, *, path: Path | None = None) -> list[dict]:
    terms = _extract_keywords([query], limit=12)
    if not terms:
        return []
    scored = []
    for episode in load_episodes(path).get("episodes") or []:
        haystack = " ".join(
            [
                str(episode.get("summary") or ""),
                " ".join(str(item) for item in episode.get("important_points") or []),
                " ".join(str(item) for item in episode.get("keywords") or []),
            ]
        ).lower()
        score = sum(1 for term in terms if term in haystack)
        if score:
            scored.append({**episode, "score": score})
    scored.sort(key=lambda item: (int(item.get("score") or 0), float(item.get("updated_at") or 0)), reverse=True)
    return scored[: max(1, int(limit))]


def format_episode(episode: dict | None = None) -> str:
    item = episode or latest_episode()
    if not item:
        return "Ainda nao ha memoria episodica salva."
    parts = [f"Episodio {item.get('date', '')}: {item.get('summary', '')}"]
    important = [str(value).strip() for value in (item.get("important_points") or []) if str(value).strip()]
    if important:
        parts.append("Pontos importantes: " + "; ".join(important[:4]) + ".")
    next_steps = [str(value).strip() for value in (item.get("next_steps") or []) if str(value).strip()]
    if next_steps:
        parts.append("Proximos passos: " + "; ".join(next_steps[:3]) + ".")
    actions = item.get("actions") or []
    if actions:
        parts.append("Actions recentes: " + ", ".join(str(action.get("action", "")) for action in actions[-4:] if action.get("action")) + ".")
    return " ".join(parts)


def format_episode_list(limit: int = 5) -> str:
    episodes = load_episodes().get("episodes") or []
    if not episodes:
        return "Ainda nao ha episodios salvos."
    rows = []
    for index, episode in enumerate(episodes[: max(1, int(limit))], start=1):
        rows.append(f"{index}. {episode.get('date', '')}: {_compact(str(episode.get('summary') or ''), limit=120)}")
    return "Episodios recentes: " + " | ".join(rows)


def format_episode_search(query: str, limit: int = 4) -> str:
    matches = search_episodes(query, limit=limit)
    if not matches:
        return "Nao encontrei episodios sobre isso."
    rows = [f"{item.get('date', '')}: {_compact(str(item.get('summary') or ''), limit=160)}" for item in matches]
    return "Episodios encontrados: " + " | ".join(rows)
