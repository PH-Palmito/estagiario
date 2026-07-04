from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

from memory.json_store import read_json_file, update_json_file


TODO_PATH = Path(__file__).with_name("todo.md")
TODO_EVIDENCE_PATH = Path(__file__).with_name("todo_evidence.json")


@dataclass(frozen=True)
class TodoItem:
    text: str
    done: bool
    section: str
    line_number: int
    indent: int = 0


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _todo_key(item: TodoItem) -> str:
    from core.router_utils import normalize_text

    section = normalize_text(item.section)
    text = normalize_text(item.text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:90]
    section = re.sub(r"[^a-z0-9]+", "-", section).strip("-")[:50]
    return f"{section}:{text}"


def _evidence_path_for_todo(path: Path | None) -> Path:
    if path is None or path == TODO_PATH:
        return TODO_EVIDENCE_PATH
    return path.with_name("todo_evidence.json")


def _load_evidence(path: Path) -> dict:
    data = read_json_file(path, {"items": {}}, validator=lambda value: isinstance(value, dict))
    items = data.get("items")
    if not isinstance(items, dict):
        data["items"] = {}
    return data


def _split_csv_like(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,;]", str(value or "")) if part.strip()]


def load_todo_items(path: Path | None = None) -> list[TodoItem]:
    todo_path = path or TODO_PATH
    try:
        lines = todo_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

    section = "Sem seção"
    items: list[TodoItem] = []
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("## "):
            section = stripped.lstrip("#").strip() or section
            continue
        match = re.match(r"^(?P<indent>\s*)-\s+\[(?P<mark>[ xX])\]\s+(?P<text>.+)$", line)
        if not match:
            continue
        items.append(
            TodoItem(
                text=_clean_text(match.group("text")),
                done=match.group("mark").lower() == "x",
                section=section,
                line_number=line_number,
                indent=len(match.group("indent") or ""),
            )
        )
    return items


def pending_todo_items(path: Path | None = None) -> list[TodoItem]:
    return [item for item in load_todo_items(path) if not item.done]


def completed_todo_items(path: Path | None = None) -> list[TodoItem]:
    return [item for item in load_todo_items(path) if item.done]


def current_priority_items(path: Path | None = None, limit: int = 8) -> list[TodoItem]:
    pending = pending_todo_items(path)
    if not pending:
        return []

    active_section = pending[0].section
    active_items = [item for item in pending if item.section == active_section]
    return active_items[: max(1, int(limit))]


def _read_todo_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []


def _write_todo_lines(path: Path, lines: list[str]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    tmp_path.replace(path)


def next_todo_item(path: Path | None = None) -> TodoItem | None:
    items = current_priority_items(path, limit=1)
    return items[0] if items else None


def _format_item(item: TodoItem, index: int | None = None) -> str:
    prefix = f"{index}. " if index is not None else ""
    return f"{prefix}{item.text} ({item.section}, linha {item.line_number})"


def _selected_priority(index: int, path: Path | None = None) -> TodoItem | None:
    priorities = current_priority_items(path, limit=20)
    try:
        selected_index = int(index)
    except Exception:
        return None
    if selected_index < 1 or selected_index > len(priorities):
        return None
    return priorities[selected_index - 1]


def _format_evidence_summary(item: TodoItem, evidence: dict) -> str:
    files = evidence.get("files") or []
    tests = evidence.get("tests") or []
    notes = evidence.get("notes") or []
    status_events = evidence.get("status_events") or []
    parts = [f"Meta: {item.text.rstrip('.!?')}."]
    if files:
        parts.append("Arquivos: " + ", ".join(str(value) for value in files[:8]) + ".")
    if tests:
        parts.append("Testes: " + ", ".join(str(value) for value in tests[:8]) + ".")
    if notes:
        latest = notes[-1] if isinstance(notes[-1], dict) else {"text": str(notes[-1])}
        parts.append("Nota mais recente: " + str(latest.get("text") or "").strip() + ".")
    if status_events:
        latest_status = status_events[-1] if isinstance(status_events[-1], dict) else {}
        status = str(latest_status.get("status") or "").strip()
        if status:
            parts.append("Último status registrado: " + status + ".")
    if not files and not tests and not notes and not status_events:
        parts.append("Ainda sem evidências registradas.")
    return " ".join(parts)


def _has_strong_evidence(evidence: dict) -> bool:
    return bool(evidence.get("files") or evidence.get("tests") or evidence.get("notes"))


def _append_status_event(item: TodoItem, *, status: str, path: Path | None = None) -> None:
    evidence_path = _evidence_path_for_todo(path)
    key = _todo_key(item)

    def updater(data: dict) -> dict:
        payload = data if isinstance(data, dict) else {"items": {}}
        items = payload.setdefault("items", {})
        record = items.setdefault(
            key,
            {
                "section": item.section,
                "text": item.text,
                "line_number": item.line_number,
                "files": [],
                "tests": [],
                "notes": [],
                "status_events": [],
                "updated_at": 0.0,
            },
        )
        record["section"] = item.section
        record["text"] = item.text
        record["line_number"] = item.line_number
        record.setdefault("status_events", []).append({"status": status, "at": time.time()})
        record["updated_at"] = time.time()
        return payload

    update_json_file(evidence_path, {"items": {}}, updater, validator=lambda value: isinstance(value, dict), trailing_newline=True)


def format_todo_priorities(path: Path | None = None, limit: int = 8) -> str:
    from core.response_polish import polish_assistant_response

    items = load_todo_items(path)
    if not items:
        return "Não encontrei a lista de afazeres do Axel."

    pending = [item for item in items if not item.done]
    done_count = len(items) - len(pending)
    if not pending:
        return f"Lista de afazeres do Axel: {done_count}/{len(items)} itens concluídos. Não há pendências abertas."

    priorities = current_priority_items(path, limit=limit)
    section = priorities[0].section if priorities else pending[0].section
    rows = [_format_item(item, index) for index, item in enumerate(priorities, start=1)]
    return polish_assistant_response(
        f"Prioridade atual do Axel: {section}. "
        f"Progresso geral: {done_count}/{len(items)} itens concluídos. "
        "Pendências principais: " + " | ".join(rows) + "."
    )


def format_next_todo_step(path: Path | None = None) -> str:
    from core.response_polish import polish_assistant_response

    item = next_todo_item(path)
    if not item:
        return "Não encontrei pendência aberta na lista de afazeres do Axel."
    text = item.text.rstrip(".!?")
    return polish_assistant_response(
        "Próximo passo do Axel: "
        f"{text}. "
        f"Origem: {item.section}, linha {item.line_number} em memory/todo.md. "
        "Critério de utilidade: precisa virar comando, efeito observável, teste ou evidência clara antes de ser marcado como concluído."
    )


def update_current_priority_status(index: int, *, done: bool, path: Path | None = None) -> str:
    from core.response_polish import polish_assistant_response

    todo_path = path or TODO_PATH
    priorities = current_priority_items(todo_path, limit=20)
    if not priorities:
        return "Não encontrei pendências abertas na lista de afazeres do Axel."

    try:
        selected_index = int(index)
    except Exception:
        return "Diga o número da meta na lista de prioridades. Exemplo: concluir meta 2."

    if selected_index < 1 or selected_index > len(priorities):
        return f"Não encontrei a meta {selected_index} na prioridade atual. Use `como estamos na lista de prioridades` para ver os números."

    item = priorities[selected_index - 1]
    lines = _read_todo_lines(todo_path)
    line_index = item.line_number - 1
    if line_index < 0 or line_index >= len(lines):
        return "Não consegui localizar a linha da meta no arquivo."

    line = lines[line_index]
    match = re.match(r"^(?P<prefix>\s*-\s+\[)(?P<mark>[ xX])(?P<suffix>\]\s+.+)$", line)
    if not match:
        return "A linha da meta não está em um formato atualizável."

    current_done = match.group("mark").lower() == "x"
    item_text = item.text.rstrip(".!?")
    if current_done == done:
        state = "concluída" if done else "aberta"
        return polish_assistant_response(f"Essa meta já está {state}: {item_text}.")

    new_mark = "x" if done else " "
    lines[line_index] = f"{match.group('prefix')}{new_mark}{match.group('suffix')}"
    _write_todo_lines(todo_path, lines)
    _append_status_event(item, status="concluída" if done else "reaberta", path=path)

    action = "concluída" if done else "reaberta"
    return polish_assistant_response(
        f"Meta {selected_index} {action}: {item_text}. "
        f"Atualizei a linha {item.line_number} em memory/todo.md."
    )


def add_current_priority_evidence(
    index: int,
    *,
    files: list[str] | tuple[str, ...] | None = None,
    tests: list[str] | tuple[str, ...] | None = None,
    note: str = "",
    path: Path | None = None,
) -> str:
    from core.response_polish import polish_assistant_response

    todo_path = path or TODO_PATH
    item = _selected_priority(index, todo_path)
    if item is None:
        return f"Não encontrei a meta {index} na prioridade atual. Use `como estamos na lista de prioridades` para ver os números."

    clean_files = [str(value).strip() for value in (files or []) if str(value).strip()]
    clean_tests = [str(value).strip() for value in (tests or []) if str(value).strip()]
    clean_note = _clean_text(note)
    if not clean_files and not clean_tests and not clean_note:
        return "Diga pelo menos uma evidência: arquivos, testes ou uma nota curta."

    evidence_path = _evidence_path_for_todo(path)
    key = _todo_key(item)

    def updater(data: dict) -> dict:
        payload = data if isinstance(data, dict) else {"items": {}}
        items = payload.setdefault("items", {})
        record = items.setdefault(
            key,
            {
                "section": item.section,
                "text": item.text,
                "line_number": item.line_number,
                "files": [],
                "tests": [],
                "notes": [],
                "updated_at": 0.0,
            },
        )
        for file in clean_files:
            if file not in record.setdefault("files", []):
                record["files"].append(file)
        for test in clean_tests:
            if test not in record.setdefault("tests", []):
                record["tests"].append(test)
        if clean_note:
            record.setdefault("notes", []).append({"text": clean_note, "at": time.time()})
        record["section"] = item.section
        record["text"] = item.text
        record["line_number"] = item.line_number
        record["updated_at"] = time.time()
        return payload

    payload = update_json_file(evidence_path, {"items": {}}, updater, validator=lambda value: isinstance(value, dict), trailing_newline=True)
    record = ((payload.get("items") or {}).get(key) or {}) if isinstance(payload, dict) else {}
    return polish_assistant_response("Evidência registrada. " + _format_evidence_summary(item, record))


def format_current_priority_evidence(index: int, *, path: Path | None = None) -> str:
    from core.response_polish import polish_assistant_response

    todo_path = path or TODO_PATH
    item = _selected_priority(index, todo_path)
    if item is None:
        return f"Não encontrei a meta {index} na prioridade atual. Use `como estamos na lista de prioridades` para ver os números."
    payload = _load_evidence(_evidence_path_for_todo(path))
    record = ((payload.get("items") or {}).get(_todo_key(item)) or {}) if isinstance(payload, dict) else {}
    return polish_assistant_response(_format_evidence_summary(item, record))


def parse_and_add_current_priority_evidence(index: int, evidence_text: str, *, path: Path | None = None) -> str:
    text = str(evidence_text or "").strip()
    files: list[str] = []
    tests: list[str] = []
    note = text

    files_match = re.search(r"(?:arquivo|arquivos|files?)\s*[:=]\s*(?P<value>[^|]+)", text, flags=re.I)
    tests_match = re.search(r"(?:teste|testes|tests?)\s*[:=]\s*(?P<value>[^|]+)", text, flags=re.I)
    note_match = re.search(r"(?:nota|obs|observacao|observação)\s*[:=]\s*(?P<value>[^|]+)", text, flags=re.I)
    if files_match:
        files = _split_csv_like(files_match.group("value"))
    if tests_match:
        tests = _split_csv_like(tests_match.group("value"))
    if note_match:
        note = note_match.group("value").strip()
    elif files_match or tests_match:
        note = ""

    return add_current_priority_evidence(index, files=files, tests=tests, note=note, path=path)


def format_todo_evidence_audit(path: Path | None = None, limit: int = 8) -> str:
    from core.response_polish import polish_assistant_response

    todo_path = path or TODO_PATH
    items = load_todo_items(todo_path)
    if not items:
        return "Não encontrei a lista de afazeres do Axel."

    evidence_payload = _load_evidence(_evidence_path_for_todo(path))
    evidence_items = evidence_payload.get("items") or {}
    completed = [item for item in items if item.done]
    pending = [item for item in items if not item.done]
    with_strong_evidence = []
    missing_strong_evidence = []

    for item in completed:
        record = evidence_items.get(_todo_key(item)) or {}
        if _has_strong_evidence(record):
            with_strong_evidence.append(item)
        else:
            missing_strong_evidence.append(item)

    rows = [
        f"{index}. {item.text.rstrip('.!?')} ({item.section}, linha {item.line_number})"
        for index, item in enumerate(missing_strong_evidence[: max(1, int(limit))], start=1)
    ]
    if rows:
        missing_text = "Concluídas sem evidência forte: " + " | ".join(rows) + "."
    else:
        missing_text = "Todas as metas concluídas possuem evidência forte registrada."

    return polish_assistant_response(
        f"Auditoria de evidências das metas: {len(completed)} concluídas, {len(pending)} abertas, "
        f"{len(with_strong_evidence)} com evidência forte e {len(missing_strong_evidence)} sem evidência forte. "
        + missing_text
    )
