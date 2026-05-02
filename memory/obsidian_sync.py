from __future__ import annotations

import json
import re
import time
from pathlib import Path

from config import BASE_DIR, OBSIDIAN_SYNC_ENABLED, OBSIDIAN_VAULT_PATH


DEFAULT_VAULT = BASE_DIR / "memory" / "obsidian_vault"


def _vault_root() -> Path | None:
    if not OBSIDIAN_SYNC_ENABLED:
        return None
    raw_path = str(OBSIDIAN_VAULT_PATH or "").strip()
    return Path(raw_path).expanduser() if raw_path else DEFAULT_VAULT


def obsidian_sync_ready() -> bool:
    return _vault_root() is not None


def _note_path(name: str) -> Path | None:
    vault = _vault_root()
    if vault is None:
        return None
    safe_name = re.sub(r"[\\/:*?\"<>|]+", " ", str(name or "").strip()).strip() or "Axel"
    return vault / "Axel" / f"{safe_name}.md"


def _write_note(path: Path, content: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.rstrip() + "\n", encoding="utf-8")
        return True
    except Exception:
        return False


def _yaml_scalar(value) -> str:
    text = str(value if value is not None else "").replace("\r", " ").replace("\n", " ").strip()
    text = text.replace('"', '\\"')
    return f"\"{text}\""


def _yaml_list(values: list[str]) -> str:
    items = [str(item).strip() for item in values if str(item).strip()]
    if not items:
        return "[]"
    return "[" + ", ".join(_yaml_scalar(item) for item in items) + "]"


def _frontmatter(data: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}: {_yaml_list(value)}")
        else:
            lines.append(f"{key}: {_yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines)


def _json_block(data: dict) -> str:
    return "```json\n" + json.dumps(data, ensure_ascii=False, indent=2) + "\n```"


def sync_current_topic_note(payload: dict) -> bool:
    path = _note_path("Current Topic")
    if path is None:
        return False
    data = dict(payload or {})
    topic = str(data.get("topic", "")).strip() or "Assunto em aberto"
    summary = str(data.get("summary", "")).strip() or "Sem resumo salvo."
    lines = [str(item).strip() for item in (data.get("lines") or []) if str(item).strip()]
    source = str(data.get("source", "")).strip() or "unknown"
    page_title = str(data.get("page_title", "")).strip()
    page_url = str(data.get("page_url", "")).strip()

    content = [
        _frontmatter(
            {
                "type": "axel-current-topic",
                "topic": topic,
                "source": source,
                "page_title": page_title,
                "page_url": page_url,
                "updated_at": data.get("updated_at", time.time()),
            }
        ),
        f"# {topic}",
        "",
        "## Resumo",
        summary,
    ]
    if lines:
        content.extend(["", "## Pontos visíveis"])
        content.extend(f"- {item}" for item in lines[:10])
    if page_url:
        content.extend(["", "## Origem", page_url])
    content.extend(["", "## Estado bruto", _json_block(data)])
    return _write_note(path, "\n".join(content))


def sync_operational_context_note(payload: dict) -> bool:
    path = _note_path("Operational Context")
    if path is None:
        return False
    data = dict(payload or {})
    summary = str(data.get("summary", "")).strip() or "Sem contexto consolidado."
    recent_topics = [str(item).strip() for item in (data.get("recent_topics") or []) if str(item).strip()]
    recent_apps = [str(item).strip() for item in (data.get("recent_apps") or []) if str(item).strip()]
    recent_sites = [str(item).strip() for item in (data.get("recent_sites") or []) if str(item).strip()]
    next_advances = [str(item).strip() for item in (data.get("next_advances") or []) if str(item).strip()]
    active_bottlenecks = [str(item).strip() for item in (data.get("active_bottlenecks") or []) if str(item).strip()]

    content = [
        _frontmatter(
            {
                "type": "axel-operational-context",
                "assistant": data.get("assistant_name", "Axel"),
                "operator": data.get("operator_name", ""),
                "updated_at": data.get("generated_at", time.time()),
            }
        ),
        "# Operational Context",
        "",
        summary,
    ]
    if recent_topics:
        content.extend(["", "## Tópicos recentes"])
        content.extend(f"- {item}" for item in recent_topics[:8])
    if recent_apps:
        content.extend(["", "## Apps recentes"])
        content.extend(f"- {item}" for item in recent_apps[:6])
    if recent_sites:
        content.extend(["", "## Contexto web"])
        content.extend(f"- {item}" for item in recent_sites[:6])
    if next_advances:
        content.extend(["", "## Próximos passos"])
        content.extend(f"- {item}" for item in next_advances[:6])
    if active_bottlenecks:
        content.extend(["", "## Gargalos"])
        content.extend(f"- {item}" for item in active_bottlenecks[:6])
    content.extend(["", "## Estado bruto", _json_block(data)])
    return _write_note(path, "\n".join(content))


def sync_profile_note(payload: dict) -> bool:
    path = _note_path("Profile")
    if path is None:
        return False
    data = dict(payload or {})
    name = str(data.get("nome", "")).strip() or "Pedro Henrique"
    focus = [str(item).strip() for item in (data.get("foco_profissional") or []) if str(item).strip()]
    projects = [str(item).strip() for item in (data.get("projetos_ativos") or []) if str(item).strip()]

    content = [
        _frontmatter(
            {
                "type": "axel-profile",
                "name": name,
                "updated_at": time.time(),
            }
        ),
        f"# {name}",
    ]
    if focus:
        content.extend(["", "## Foco profissional"])
        content.extend(f"- {item}" for item in focus[:8])
    if projects:
        content.extend(["", "## Projetos ativos"])
        content.extend(f"- {item}" for item in projects[:8])
    content.extend(["", "## Estado bruto", _json_block(data)])
    return _write_note(path, "\n".join(content))

