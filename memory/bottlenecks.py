import json
import os
import re
import time
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
UI_STATE_PATH = MEMORY_DIR / "ui_state.json"
BOTTLENECKS_PATH = MEMORY_DIR / "bottlenecks.json"


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_json(path: Path, payload: dict):
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _history() -> list[dict]:
    data = _load_json(UI_STATE_PATH)
    history = data.get("history") if isinstance(data, dict) else None
    if isinstance(history, list):
        return [item for item in history if isinstance(item, dict)]
    return []


def _normalize(text: str) -> str:
    text = str(text or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _latest_user_before(history: list[dict], index: int) -> str:
    for back in range(index - 1, -1, -1):
        item = history[back]
        if str(item.get("role", "")).strip().lower() == "user":
            return str(item.get("text", "")).strip()
    return ""


def _classify(message: str) -> tuple[str, str, str] | None:
    normalized = _normalize(message)
    if not normalized:
        return None

    if any(fragment in normalized for fragment in {
        "nao captei com precisao",
        "nao entendi",
        "pode repetir",
        "nao identifiquei o comando",
        "esse comando nao ficou claro",
    }):
        return (
            "voice_understanding",
            "Entendimento de voz instavel",
            "O Axel ainda esta tendo dificuldade para interpretar falas e comandos de forma consistente.",
        )

    if "erro ao executar" in normalized or normalized.startswith("erro "):
        return (
            "execution_error",
            "Falha na execucao de acoes",
            "Algumas acoes estao chegando na etapa de execucao, mas ainda falham no sistema.",
        )

    if any(fragment in normalized for fragment in {
        "nao consegui ler",
        "nao capturei os valores",
        "nao capturei os valores e rotulos principais",
        "nao consegui ler itens clicaveis",
        "nao capturei",
    }):
        return (
            "screen_reading",
            "Leitura de tela inconsistente",
            "A leitura de pagina ainda perde partes uteis do conteudo em alguns cenarios.",
        )

    if any(fragment in normalized for fragment in {
        "nao encontrei uma janela aberta",
        "nao parecia estar aberto",
        "aplicativo",
        "nao permitido",
    }):
        return (
            "app_control",
            "Controle de aplicativos ainda fragil",
            "Alguns comandos de abrir, fechar ou focar app ainda falham em casos reais.",
        )

    return None


def generate_bottlenecks(limit: int = 5) -> list[dict]:
    history = _history()
    grouped: dict[str, dict] = {}

    for index, item in enumerate(history):
        role = str(item.get("role", "")).strip().lower()
        if role != "assistant":
            continue

        message = str(item.get("text", "")).strip()
        classification = _classify(message)
        if not classification:
            continue

        key, title, reason = classification
        user_text = _latest_user_before(history, index)
        bucket = grouped.setdefault(
            key,
            {
                "kind": key,
                "title": title,
                "reason": reason,
                "count": 0,
                "examples": [],
                "assistant_examples": [],
            },
        )
        bucket["count"] += 1
        if user_text:
            bucket["examples"].append(user_text)
        if message:
            bucket["assistant_examples"].append(message)

    items = []
    for bucket in grouped.values():
        example_counter = Counter(_normalize(text) for text in bucket["examples"] if text)
        top_examples = [text for text, _ in example_counter.most_common(3)]
        assistant_counter = Counter(_normalize(text) for text in bucket["assistant_examples"] if text)
        top_assistant = [text for text, _ in assistant_counter.most_common(2)]
        items.append(
            {
                "kind": bucket["kind"],
                "title": bucket["title"],
                "reason": bucket["reason"],
                "count": bucket["count"],
                "examples": top_examples,
                "assistant_signals": top_assistant,
            }
        )

    items.sort(key=lambda item: item.get("count", 0), reverse=True)
    return items[: max(1, int(limit))]


def save_bottlenecks(limit: int = 5) -> list[dict]:
    items = generate_bottlenecks(limit=limit)
    payload = {
        "generated_at": time.time(),
        "items": items,
    }
    _save_json(BOTTLENECKS_PATH, payload)
    return items


def load_bottlenecks() -> list[dict]:
    data = _load_json(BOTTLENECKS_PATH)
    items = data.get("items") if isinstance(data, dict) else None
    if isinstance(items, list) and items:
        return items
    return save_bottlenecks()

