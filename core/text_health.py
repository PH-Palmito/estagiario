from __future__ import annotations

from pathlib import Path


MOJIBAKE_MARKERS = (
    "\u00c3\u00a1",
    "\u00c3\u00a0",
    "\u00c3\u00a2",
    "\u00c3\u00a3",
    "\u00c3\u00a7",
    "\u00c3\u00a9",
    "\u00c3\u00aa",
    "\u00c3\u00ad",
    "\u00c3\u00b3",
    "\u00c3\u00b4",
    "\u00c3\u00b5",
    "\u00c3\u00ba",
    "\u00c2",
    "\u00e2\u20ac",
    "\u00c4\u0192",
)

TEXT_HEALTH_PATTERNS = ("*.py", "*.md", "*.txt", "*.html")
TEXT_HEALTH_SKIP_PARTS = {
    ".git",
    ".tmp",
    "__pycache__",
    "venv",
    "models",
    "memory/chunks",
    "backups",
}


def _should_skip(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path
    parts = {part.lower() for part in relative.parts}
    normalized = str(relative).replace("\\", "/").lower()
    return bool(parts & TEXT_HEALTH_SKIP_PARTS) or any(skip in normalized for skip in TEXT_HEALTH_SKIP_PARTS)


def find_mojibake_files(root: Path, *, limit: int = 20) -> list[dict]:
    project_dir = Path(root)
    findings: list[dict] = []
    for pattern in TEXT_HEALTH_PATTERNS:
        for path in project_dir.rglob(pattern):
            if _should_skip(path, project_dir):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            hits = sum(text.count(marker) for marker in MOJIBAKE_MARKERS)
            if hits <= 0:
                continue
            try:
                relative = path.relative_to(project_dir).as_posix()
            except ValueError:
                relative = str(path)
            findings.append({"path": relative, "markers": hits})
            if len(findings) >= max(1, int(limit)):
                return findings
    return findings


def text_encoding_health(root: Path, *, limit: int = 20) -> dict:
    findings = find_mojibake_files(root, limit=limit)
    return {
        "mojibake_count": len(findings),
        "findings": findings,
        "status": "precisa de revisao" if findings else "ok",
    }
