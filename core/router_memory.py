from __future__ import annotations

import json
import re

from core.router_utils import normalize_text
from memory.docs_context import docs_plan_answer


def _memory_key_from_text(text: str) -> str:
    normalized = normalize_text(text)
    normalized = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE)
    normalized = re.sub(
        r"^(?:que\s+)?(?:eu\s+)?(?:prefiro|gosto|uso|quero|costumo|minha\s+preferencia\s+e|minha\s+preferencia\s+eh)\s+",
        "",
        normalized,
    )
    normalized = re.sub(r"^(?:o\s+)?(?:meu|minha)\s+", "", normalized)
    words = [
        word
        for word in normalized.split()
        if word not in {"que", "de", "do", "da", "dos", "das", "um", "uma", "o", "a"}
    ]
    key = "_".join(words[:6]).strip("_")
    return key or "nota"


def _memory_namespace_from_text(text: str, default: str = "general") -> str:
    normalized = normalize_text(text)
    if any(term in normalized for term in {"prefiro", "preferencia", "gosto", "uso", "quero", "costumo"}):
        return "preferences"
    if any(term in normalized for term in {"briefing", "noticia", "noticias", "carteira", "investimento", "investimentos"}):
        return "investments"
    if any(term in normalized for term in {"treino", "academia", "musculo", "musculos"}):
        return "training"
    if any(term in normalized for term in {"codigo", "projeto", "programacao", "codex"}):
        return "projects"
    return default


def detect_memory_command(user_input: str):
    cleaned_input = re.sub(r"^\s*axel[\s,;:.-]+", "", user_input.strip(), flags=re.I)
    lower = normalize_text(cleaned_input)
    if lower in {"o que voce sabe fazer", "o que voce consegue fazer"}:
        return None

    if lower in {"listar memoria", "liste a memoria", "listar atalhos", "liste os atalhos", "o que voce lembra"}:
        return {"intent": "list_smart_memory", "target": None}

    if lower in {
        "listar memoria simples",
        "liste memoria simples",
        "listar memorias",
        "liste memorias",
        "memoria simples",
    }:
        return {"intent": "action_memory_list", "target": "general"}

    list_match = re.match(r"^(?:listar|liste|mostrar|mostre|ver)\s+(?:a\s+)?memoria\s+(?:de\s+|sobre\s+)?(.+)$", lower)
    if list_match and list_match.group(1).strip() not in {"atalhos", "apps", "sites"}:
        namespace_text = list_match.group(1).strip()
        namespace = _memory_namespace_from_text(namespace_text, default=namespace_text.replace(" ", "_"))
        return {"intent": "action_memory_list", "target": namespace}

    recall_match = re.match(
        r"^(?:o\s+que\s+voce\s+(?:sabe|lembra)|consulta|consulte|buscar|busque|lembra)\s+(?:sobre\s+|da\s+|do\s+)?(.+)$",
        lower,
    )
    if recall_match:
        key_text = recall_match.group(1).strip()
        if key_text and key_text not in {"memoria", "atalhos"}:
            return {
                "intent": "action_memory_recall",
                "target": {
                    "namespace": _memory_namespace_from_text(key_text),
                    "key": _memory_key_from_text(key_text),
                },
            }

    explicit_memory_match = re.match(
        r"^(?:lembre|lembra|memorize|salve|guarde|registre|anote)\s+(?:na\s+)?(?:memoria|memória|contexto)\s+(?:que\s+)?(.+)$",
        cleaned_input,
        flags=re.I,
    )
    preference_match = re.match(
        r"^(?:lembre|lembra|memorize|salve|guarde|registre|anote)\s+que\s+(?:eu\s+)?(?:prefiro|gosto|uso|quero|costumo)\s+(.+)$",
        cleaned_input,
        flags=re.I,
    )
    project_idea_match = re.match(
        r"^(?:lembre|lembra|memorize|salve|guarde|registre|anote)\s+"
        r"(?:a\s+)?(?:ideia|idéia)\s+de\s+projeto\s*(?:[:=-]|\s+)?\s*[\"'“”‘’]?(.+?)[\"'“”‘’]?$",
        cleaned_input,
        flags=re.I,
    )
    generic_idea_match = re.match(
        r"^(?:lembre|lembra|memorize|salve|guarde|registre|anote)\s+"
        r"(?:uma\s+|a\s+)?(?:ideia|idéia)(?:\s+(?:sobre|de|para)\s+(.+))?$",
        cleaned_input,
        flags=re.I,
    )
    memory_match = explicit_memory_match or preference_match or project_idea_match or generic_idea_match
    if memory_match:
        if generic_idea_match and not project_idea_match:
            subject = (generic_idea_match.group(1) or "").strip(" .")
            namespace = _memory_namespace_from_text(subject, default="general")
            if namespace == "general" and subject:
                namespace = "projects"
            fact = f"ideia sobre {subject}" if subject else "ideia sem detalhes"
            return {
                "intent": "action_memory_remember",
                "target": {
                    "namespace": namespace,
                    "key": _memory_key_from_text(fact),
                    "value": fact,
                },
            }
        fact = memory_match.group(1).strip(" .")
        if fact:
            if project_idea_match:
                namespace = "projects"
                if "projeto" not in normalize_text(fact):
                    fact = f"ideia de projeto: {fact}"
            else:
                namespace = _memory_namespace_from_text(fact, default="preferences" if preference_match else "general")
            return {
                "intent": "action_memory_remember",
                "target": {
                    "namespace": namespace,
                    "key": _memory_key_from_text(fact),
                    "value": fact,
                },
            }

    remember_match = re.match(
        r"^(?:lembre|lembra|memorize|salve)\s+que\s+(.+?)\s+e\s+(app|aplicativo|programa|site)$",
        lower,
    )
    if remember_match:
        kind = remember_match.group(2)
        if kind in {"aplicativo", "programa"}:
            kind = "app"
        return {
            "intent": "remember_target_kind",
            "target": {
                "name": remember_match.group(1).strip(),
                "kind": kind,
            },
        }

    forget_match = re.match(
        r"^(?:esqueca|esquece|remova|apague)\s+(?:a\s+memoria\s+de\s+|o\s+atalho\s+|a\s+lembranca\s+de\s+)?(.+)$",
        lower,
    )
    if forget_match:
        return {"intent": "forget_smart_memory", "target": forget_match.group(1).strip()}

    return None


def detect_docs_context_command(user_input: str):
    answer = docs_plan_answer(user_input)
    if answer:
        return {"intent": "respond", "target": None, "response": answer}
    return None


def detect_action_core_command(user_input: str):
    text = normalize_text(user_input).strip(" .")

    if text in {
        "criar backup da memoria",
        "crie backup da memoria",
        "fazer backup da memoria",
        "faca backup da memoria",
        "backup da memoria",
        "backup das memorias",
    }:
        return {"intent": "action_tool_execute", "target": {"name": "memory.backup.create", "arguments": {}}}

    if text in {
        "listar backups da memoria",
        "liste backups da memoria",
        "ver backups da memoria",
        "backups da memoria",
        "listar backup da memoria",
    }:
        return {"intent": "action_tool_execute", "target": {"name": "memory.backup.list", "arguments": {}}}

    restore_match = re.match(
        r"^(?:restaurar|restaure|recuperar|recupere)\s+(?:arquivo\s+)?(?:da\s+)?memoria\s+([A-Za-z0-9_.-]+\.json)\s+(?:do|de|a\s+partir\s+do)\s+(memory-\d{8}-\d{6})$",
        text,
    )
    if restore_match:
        return {
            "intent": "action_tool_execute",
            "target": {
                "name": "memory.backup.restore_file",
                "arguments": {
                    "filename": restore_match.group(1),
                    "backup_name": restore_match.group(2),
                },
            },
        }

    if text in {"listar actions", "lista actions", "ver actions", "quais actions", "catalogo actions"}:
        return {"intent": "action_tool_list", "target": None}

    for category in {"training", "treino", "investments", "investimentos", "memory", "memoria", "files", "arquivos"}:
        if text in {f"listar actions {category}", f"ver actions {category}", f"actions {category}"}:
            category_map = {
                "treino": "training",
                "investimentos": "investments",
                "memoria": "memory",
                "arquivos": "files",
            }
            return {"intent": "action_tool_list", "target": category_map.get(category, category)}

    if text in {"schema actions", "schemas actions", "tools schema", "schema tools"}:
        return {"intent": "action_tool_schema", "target": None}

    for prefix in ("processar arquivo ", "processa arquivo ", "analisar arquivo ", "analisa arquivo "):
        if text.startswith(prefix):
            return {"intent": "action_file_process", "target": user_input[len(prefix):].strip()}

    action_exec = re.match(
        r"^(?:executar|execute|rodar|rode)\s+action\s+([A-Za-z0-9_.-]+)(?:\s+(?:com\s+)?(?:argumentos?\s*)?)?(.*)$",
        user_input.strip(),
        flags=re.I,
    )
    if action_exec:
        name = action_exec.group(1).strip()
        raw_arguments = action_exec.group(2).strip()
        arguments = {}
        if raw_arguments:
            json_start = min(
                [idx for idx in (raw_arguments.find("{"), raw_arguments.find("[")) if idx >= 0],
                default=-1,
            )
            if json_start >= 0:
                try:
                    arguments = json.loads(raw_arguments[json_start:])
                except json.JSONDecodeError as exc:
                    return {
                        "intent": "respond",
                        "target": None,
                        "response": f"JSON de argumentos invalido: {exc.msg}.",
                    }
        if name:
            return {"intent": "action_tool_execute", "target": {"name": name, "arguments": arguments}}

    return None


MEMORY_DETECTORS = [
    detect_memory_command,
    detect_docs_context_command,
    detect_action_core_command,
]
