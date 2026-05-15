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


def _folder_path(name: str) -> Path | None:
    vault = _vault_root()
    if vault is None:
        return None
    safe_name = re.sub(r"[\\/:*?\"<>|]+", " ", str(name or "").strip()).strip() or "Axel"
    return vault / "Axel" / safe_name


def _write_note(path: Path, content: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized = content.rstrip() + "\n"
        if path.exists():
            try:
                if path.read_text(encoding="utf-8") == normalized:
                    return True
            except Exception:
                pass
        path.write_text(normalized, encoding="utf-8")
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
                "title": topic,
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
                "title": "Operational Context",
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
                "title": name,
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


def sync_long_memory_note(payload: dict) -> bool:
    path = _note_path("Long Memory")
    if path is None:
        return False

    data = dict(payload or {})
    items = data.get("items") if isinstance(data.get("items"), list) else []
    grouped: dict[str, list[dict]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category", "context")).strip() or "context"
        grouped.setdefault(category, []).append(item)

    content = [
        _frontmatter(
            {
                "type": "axel-long-memory",
                "title": "Long Memory",
                "updated_at": data.get("updated_at", time.time()),
                "tags": ["axel", "memory", "curated"],
            }
        ),
        "# Long Memory",
        "",
        "Memoria longa curada do Axel. Cresce devagar: preferencias, decisoes, projetos, prioridades e contexto duravel.",
    ]

    labels = {
        "preference": "Preferencias",
        "decision": "Decisoes",
        "project": "Projetos",
        "future": "Futuros",
        "context": "Contexto duravel",
    }
    for category in ("preference", "decision", "project", "future", "context"):
        category_items = grouped.get(category) or []
        if not category_items:
            continue
        content.extend(["", f"## {labels.get(category, category.title())}"])
        for item in category_items[:40]:
            fact = str(item.get("fact", "")).strip()
            if not fact:
                continue
            source = str(item.get("source", "")).strip()
            suffix = f" _{source}_" if source else ""
            content.append(f"- {fact}{suffix}")

    content.extend(["", "## Estado bruto", _json_block(data)])
    return _write_note(path, "\n".join(content))


def _section_lines(title: str, items: list[str]) -> list[str]:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    if not cleaned:
        return []
    block = ["", f"## {title}"]
    block.extend(f"- {item}" for item in cleaned)
    return block


def sync_knowledge_vault(profile_payload: dict | None = None, directives_payload: dict | None = None) -> bool:
    profile = dict(profile_payload or {})
    directives = dict(directives_payload or {})
    root_index = _note_path("Home")
    projects_note = _note_path("Projects")
    preferences_note = _note_path("Preferences")
    investments_note = _note_path("Investments")
    learning_note = _note_path("Learning")
    if not all([root_index, projects_note, preferences_note, investments_note, learning_note]):
        return False

    knowledge_folder = _folder_path("Knowledge")
    if knowledge_folder is None:
        return False
    knowledge_folder.mkdir(parents=True, exist_ok=True)

    name = str(profile.get("nome", "")).strip() or "Pedro Henrique"
    stack = [str(item).strip() for item in (profile.get("stack") or []) if str(item).strip()]
    focus = [str(item).strip() for item in (profile.get("foco_profissional") or []) if str(item).strip()]
    objectives = [str(item).strip() for item in (profile.get("objetivos") or []) if str(item).strip()]
    observations = [str(item).strip() for item in (profile.get("observacoes") or []) if str(item).strip()]
    project_map = profile.get("projetos") if isinstance(profile.get("projetos"), dict) else {}
    learning = profile.get("aprendizado") if isinstance(profile.get("aprendizado"), dict) else {}
    finances = profile.get("financas") if isinstance(profile.get("financas"), dict) else {}
    interests = profile.get("interesses") if isinstance(profile.get("interesses"), dict) else {}
    core_directives = [str(item).strip() for item in (directives.get("core_directives") or []) if str(item).strip()]
    investment_mode = directives.get("investment_mode") if isinstance(directives.get("investment_mode"), dict) else {}

    home_content = [
        _frontmatter(
            {
                "type": "axel-home",
                "title": "Axel Home",
                "operator": name,
                "updated_at": time.time(),
                "tags": ["axel", "vault", "home"],
            }
        ),
        "# Axel Home",
        "",
        f"Base viva do Axel para lembrar contexto, projetos, preferências e temas recorrentes de {name}.",
        "",
        "## Mapa rápido",
        "- [[Profile]]",
        "- [[Current Topic]]",
        "- [[Operational Context]]",
        "- [[Projects]]",
        "- [[Preferences]]",
        "- [[Investments]]",
        "- [[Portfolio Snapshot]]",
        "- [[Learning]]",
    ]
    _write_note(root_index, "\n".join(home_content))

    project_lines = [
        _frontmatter(
            {
                "type": "axel-projects",
                "title": "Projects",
                "updated_at": time.time(),
                "tags": ["axel", "projects"],
            }
        ),
        "# Projects",
        "",
        "Projetos ativos e relevantes para o Axel usar como contexto.",
    ]
    for key, description in project_map.items():
        label = str(key).replace("_", " ").strip().title()
        project_lines.extend(["", f"## {label}", str(description).strip()])
    _write_note(projects_note, "\n".join(project_lines))

    preference_lines = [
        _frontmatter(
            {
                "type": "axel-preferences",
                "title": "Preferences",
                "updated_at": time.time(),
                "tags": ["axel", "preferences"],
            }
        ),
        "# Preferences",
        "",
        f"Preferências e estilo de trabalho de {name}.",
    ]
    preference_lines.extend(_section_lines("Foco profissional", focus))
    preference_lines.extend(_section_lines("Stack", stack))
    preference_lines.extend(_section_lines("Objetivos", objectives))
    preference_lines.extend(_section_lines("Observações", observations))
    _write_note(preferences_note, "\n".join(preference_lines))

    investment_lines = [
        _frontmatter(
            {
                "type": "axel-investments",
                "title": "Investments",
                "updated_at": time.time(),
                "tags": ["axel", "investments"],
            }
        ),
        "# Investments",
        "",
        "Regras, perfil e contexto financeiro que o Axel deve considerar antes de responder.",
    ]
    goal = str(investment_mode.get("goal", "")).strip()
    if goal:
        investment_lines.extend(["", "## Objetivo", goal])
    if finances:
        investment_lines.extend(["", "## Perfil financeiro"])
        for key, value in finances.items():
            if key == "estrategia":
                continue
            if isinstance(value, list):
                investment_lines.append(f"- {key}: {', '.join(str(item) for item in value)}")
            else:
                investment_lines.append(f"- {key}: {value}")
    strategy = finances.get("estrategia") if isinstance(finances.get("estrategia"), dict) else {}
    watchlist = [str(item).strip().upper() for item in (strategy.get("watchlist") or []) if str(item).strip()]
    price_targets = strategy.get("precos_teto") if isinstance(strategy.get("precos_teto"), dict) else {}
    theses = strategy.get("teses") if isinstance(strategy.get("teses"), dict) else {}
    if watchlist:
        investment_lines.extend(["", "## Watchlist"])
        investment_lines.extend(f"- {item}" for item in watchlist)
    if price_targets:
        investment_lines.extend(["", "## Preços-teto"])
        for ticker, price in sorted(price_targets.items()):
            investment_lines.append(f"- {ticker}: {price}")
    if theses:
        investment_lines.extend(["", "## Teses curtas"])
        for ticker, thesis in sorted(theses.items()):
            investment_lines.append(f"- {ticker}: {thesis}")
    rules = [str(item).strip() for item in (investment_mode.get("rules") or []) if str(item).strip()]
    investment_lines.extend(_section_lines("Regras do modo investimentos", rules))
    _write_note(investments_note, "\n".join(investment_lines))

    learning_lines = [
        _frontmatter(
            {
                "type": "axel-learning",
                "title": "Learning",
                "updated_at": time.time(),
                "tags": ["axel", "learning"],
            }
        ),
        "# Learning",
        "",
        "Como Pedro aprende, decide e costuma estruturar projetos.",
    ]
    for key, value in learning.items():
        learning_lines.extend(["", f"## {str(key).replace('_', ' ').title()}", str(value).strip()])
    interest_lines = []
    for key, value in interests.items():
        if isinstance(value, list):
            interest_lines.append(f"{key}: {', '.join(str(item) for item in value)}")
        elif value:
            interest_lines.append(str(key).replace("_", " ").title())
    learning_lines.extend(_section_lines("Interesses", interest_lines))
    learning_lines.extend(_section_lines("Diretrizes centrais", core_directives))
    _write_note(learning_note, "\n".join(learning_lines))
    return True


def load_vault_context() -> dict:
    root = _vault_root()
    if root is None or not root.exists():
        return {}

    note_names = ["Home", "Profile", "Current Topic", "Operational Context", "Long Memory", "Projects", "Preferences", "Investments", "Learning", "Portfolio Snapshot"]
    result = {}
    for note_name in note_names:
        path = _note_path(note_name)
        if path and path.exists():
            try:
                result[note_name.lower().replace(" ", "_")] = path.read_text(encoding="utf-8")
            except Exception:
                continue
    return result


def _strip_frontmatter_and_blocks(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    raw = re.sub(r"^---\n.*?\n---\n", "", raw, flags=re.S)
    raw = re.sub(r"```.*?```", " ", raw, flags=re.S)
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


def _tokenize_for_search(text: str) -> list[str]:
    normalized = re.sub(r"[^\w\s]", " ", str(text or "").lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return [
        token
        for token in normalized.split()
        if len(token) >= 4 and token not in {"isso", "essa", "esse", "sobre", "mais", "como", "qual", "porque", "para"}
    ]


def search_vault_context(query: str, limit: int = 2, max_chars: int = 500) -> list[dict]:
    vault = load_vault_context() or {}
    if not vault:
        return []

    tokens = _tokenize_for_search(query)
    if not tokens:
        return []

    ranked = []
    for name, content in vault.items():
        cleaned = _strip_frontmatter_and_blocks(content)
        lower_cleaned = cleaned.lower()
        score = sum(2 if token in name else 1 for token in tokens if token in lower_cleaned or token in name)
        if score <= 0:
            continue
        ranked.append((score, name, cleaned[:max_chars]))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [
        {"name": name, "excerpt": excerpt, "score": score}
        for score, name, excerpt in ranked[: max(1, int(limit))]
    ]


def sync_operational_context_note(payload: dict) -> bool:
    path = _note_path("Operational Context")
    if path is None:
        return False
    data = dict(payload or {})
    summary = str(data.get("summary", "")).strip() or "Sem contexto consolidado."
    recent_topics = [str(item).strip() for item in (data.get("recent_topics") or []) if str(item).strip()]
    recent_tickers = [str(item).strip().upper() for item in (data.get("recent_tickers") or []) if str(item).strip()]
    recent_apps = [str(item).strip() for item in (data.get("recent_apps") or []) if str(item).strip()]
    recent_sites = [str(item).strip() for item in (data.get("recent_sites") or []) if str(item).strip()]
    next_advances = [str(item).strip() for item in (data.get("next_advances") or []) if str(item).strip()]
    active_bottlenecks = [str(item).strip() for item in (data.get("active_bottlenecks") or []) if str(item).strip()]
    open_tasks = [str(item).strip() for item in (data.get("open_tasks") or []) if str(item).strip()]
    preference_summary = str(data.get("preference_summary", "")).strip()

    content = [
        _frontmatter(
            {
                "type": "axel-operational-context",
                "title": "Operational Context",
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
    if recent_tickers:
        content.extend(["", "## Tickers recentes"])
        content.extend(f"- {item}" for item in recent_tickers[:8])
    if recent_apps:
        content.extend(["", "## Apps recentes"])
        content.extend(f"- {item}" for item in recent_apps[:6])
    if recent_sites:
        content.extend(["", "## Contexto web"])
        content.extend(f"- {item}" for item in recent_sites[:6])
    if preference_summary:
        content.extend(["", "## Preferencias operacionais", preference_summary])
    if next_advances:
        content.extend(["", "## Próximos passos"])
        content.extend(f"- {item}" for item in next_advances[:6])
    if open_tasks:
        content.extend(["", "## Tarefas abertas"])
        content.extend(f"- {item}" for item in open_tasks[:8])
    if active_bottlenecks:
        content.extend(["", "## Gargalos"])
        content.extend(f"- {item}" for item in active_bottlenecks[:6])
    content.extend(["", "## Estado bruto", _json_block(data)])
    return _write_note(path, "\n".join(content))


def sync_portfolio_snapshot_note(payload: dict) -> bool:
    path = _note_path("Portfolio Snapshot")
    if path is None:
        return False

    data = dict(payload or {})
    metric_map = data.get("metric_map") if isinstance(data.get("metric_map"), dict) else {}
    positions = data.get("asset_positions") if isinstance(data.get("asset_positions"), dict) else {}
    category_breakdown = data.get("category_breakdown") if isinstance(data.get("category_breakdown"), dict) else {}
    category_summaries = data.get("category_summaries") if isinstance(data.get("category_summaries"), dict) else {}
    unresolved = data.get("unresolved_category_counts") if isinstance(data.get("unresolved_category_counts"), dict) else {}

    highlights = []
    for key in ("patrimonio", "valor investido", "rentabilidade", "proventos", "variacao"):
        value = str(metric_map.get(key, "")).strip()
        if value:
            highlights.append(f"{key}: {value}")

    category_rows = []
    for name, value in category_breakdown.items():
        summary = category_summaries.get(name) if isinstance(category_summaries.get(name), dict) else {}
        bits = [f"{name}: {value}"]
        for key in ("value_total", "assets_count"):
            field = str(summary.get(key, "")).strip()
            if field:
                bits.append(field)
        category_rows.append(" | ".join(bits))

    position_rows = []
    for ticker, position in positions.items():
        if not isinstance(position, dict):
            continue
        bits = [ticker]
        for key in ("balance", "rentability", "portfolio_percentage"):
            value = str(position.get(key, "")).strip()
            if value:
                bits.append(value)
        position_rows.append((str(position.get("portfolio_percentage", "")).strip(), " | ".join(bits)))
    position_rows = [row for _weight, row in sorted(position_rows, reverse=True)[:8]]

    unresolved_rows = []
    for name, info in unresolved.items():
        if not isinstance(info, dict):
            continue
        reported = int(info.get("reported") or 0)
        captured = int(info.get("captured") or 0)
        unresolved_rows.append(f"{name}: {captured} de {reported} individualizados")

    content = [
        _frontmatter(
            {
                "type": "axel-portfolio-snapshot",
                "title": "Portfolio Snapshot",
                "updated_at": data.get("updated_at", time.time()),
                "source": data.get("source", "investment_snapshot"),
                "tags": ["axel", "investments", "portfolio"],
            }
        ),
        "# Portfolio Snapshot",
        "",
        str(data.get("summary", "")).strip() or "Sem resumo financeiro salvo.",
    ]
    content.extend(_section_lines("Destaques", highlights))
    content.extend(_section_lines("Classes", category_rows))
    content.extend(_section_lines("Posições visíveis", position_rows))
    content.extend(_section_lines("Blocos ainda agregados", unresolved_rows))
    content.extend(["", "## Estado bruto", _json_block(data)])
    return _write_note(path, "\n".join(content))
