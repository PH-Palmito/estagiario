from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTEXT_CANDIDATES = (
    "AGENTS.md",
    "AXEL.md",
    ".agents/AGENTS.md",
    ".agents/AXEL.md",
    ".axel/context.md",
)
MAX_CONTEXT_CHARS = 6000
MAX_SUMMARY_CHARS = 900


@dataclass(frozen=True)
class WorkspaceContext:
    path: str
    title: str
    summary: str
    instructions: list[str]
    raw_text: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "title": self.title,
            "summary": self.summary,
            "instructions": list(self.instructions),
            "raw_text": self.raw_text,
        }


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def _clean_line(line: str) -> str:
    text = re.sub(r"\s+", " ", str(line or "")).strip()
    return text.strip("-*# ")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:MAX_CONTEXT_CHARS]
    except Exception:
        return ""


def _extract_title(text: str, fallback: str) -> str:
    for line in str(text or "").splitlines():
        clean = _clean_line(line)
        if clean:
            return clean[:120]
    return fallback


def _extract_instructions(text: str, limit: int = 8) -> list[str]:
    instructions: list[str] = []
    for raw in str(text or "").splitlines():
        line = str(raw or "").strip()
        if not line.startswith(("-", "*")):
            continue
        clean = _clean_line(line)
        if clean and clean not in instructions:
            instructions.append(clean[:180])
        if len(instructions) >= limit:
            break
    if instructions:
        return instructions

    paragraphs = [
        _clean_line(part)
        for part in re.split(r"\n\s*\n", str(text or ""))
        if _clean_line(part)
    ]
    return [item[:180] for item in paragraphs[:limit]]


def _summarize_context(title: str, instructions: list[str]) -> str:
    if not instructions:
        return f"Contexto do workspace: {title}."
    joined = "; ".join(instructions[:4])
    summary = f"Contexto do workspace: {title}. Instrucoes: {joined}."
    return summary[:MAX_SUMMARY_CHARS]


def find_workspace_context_files(root: Path | None = None) -> list[Path]:
    workspace = root or ROOT
    files = []
    for relative in CONTEXT_CANDIDATES:
        path = workspace / relative
        if path.exists() and path.is_file():
            files.append(path)
    return files


def load_workspace_context(root: Path | None = None) -> dict:
    workspace = root or ROOT
    files = find_workspace_context_files(workspace)
    if not files:
        return {
            "available": False,
            "root": str(workspace),
            "files": [],
            "summary": "",
            "instructions": [],
        }

    contexts: list[WorkspaceContext] = []
    for path in files[:3]:
        text = _read_text(path)
        if not text.strip():
            continue
        relative = _safe_relative(path, workspace)
        title = _extract_title(text, relative)
        instructions = _extract_instructions(text)
        contexts.append(
            WorkspaceContext(
                path=relative,
                title=title,
                summary=_summarize_context(title, instructions),
                instructions=instructions,
                raw_text=text,
            )
        )

    instructions = []
    for context in contexts:
        for item in context.instructions:
            if item not in instructions:
                instructions.append(item)

    summary = " ".join(context.summary for context in contexts).strip()
    return {
        "available": bool(contexts),
        "root": str(workspace),
        "files": [context.path for context in contexts],
        "summary": summary[:MAX_SUMMARY_CHARS],
        "instructions": instructions[:12],
        "contexts": [context.to_dict() for context in contexts],
    }


def format_workspace_context(root: Path | None = None) -> str:
    context = load_workspace_context(root)
    if not context.get("available"):
        return (
            "Nenhum contexto de workspace encontrado. Crie AGENTS.md, AXEL.md "
            "ou .axel/context.md na raiz do projeto."
        )
    files = ", ".join(str(item) for item in context.get("files") or [])
    summary = str(context.get("summary") or "").strip()
    if summary:
        return f"Contexto de workspace carregado de {files}. {summary}"
    return f"Contexto de workspace carregado de {files}."
