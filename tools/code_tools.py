import json
import re
import subprocess
import time
from pathlib import Path

from tools.system_tools import focus_app

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".css", ".html"}
SKIP_PARTS = {"venv", "__pycache__", ".git", ".tmp", "models", "sandbox"}
POWERSHELL_EXE = "powershell"


def _resolve_target(path: str | None) -> Path:
    raw = str(path or ".").strip().strip('"').strip("'")
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = (ROOT / candidate).resolve()
    return candidate


def _iter_code_files(base: Path, limit: int = 160):
    if base.is_file():
        yield base
        return

    count = 0
    for path in base.rglob("*"):
        if count >= limit:
            return
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in DEFAULT_EXTENSIONS:
            continue
        count += 1
        yield path


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def _add_finding(findings: list[dict], severity: int, path: Path, message: str, line: int | None = None):
    findings.append(
        {
            "severity": int(severity),
            "path": _rel(path),
            "line": int(line or 0),
            "message": str(message).strip(),
        }
    )


def _inspect_python(path: Path, text: str, findings: list[dict]):
    try:
        compile(text, str(path), "exec")
    except SyntaxError as exc:
        _add_finding(findings, 0, path, f"Erro de sintaxe: {exc.msg}", exc.lineno or 0)

    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped == "except:":
            _add_finding(findings, 1, path, "Bare except pode esconder erro real.", number)
        if re.fullmatch(r"except\s+Exception\s*:\s*pass", stripped):
            _add_finding(findings, 1, path, "except Exception: pass silencia falha importante.", number)
        if re.search(r"^\s*print\(", line) and "print(__name__" not in stripped:
            _add_finding(findings, 3, path, "Possivel debug residual com print.", number)
        if "TODO" in stripped or "FIXME" in stripped:
            _add_finding(findings, 3, path, "TODO/FIXME pendente em trecho executavel.", number)
        if stripped.startswith(("<<<<<<<", ">>>>>>>")) or stripped == "=======":
            _add_finding(findings, 0, path, "Marcador de conflito de merge encontrado.", number)


def _inspect_js_ts(path: Path, text: str, findings: list[dict]):
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if "console.log(" in stripped:
            _add_finding(findings, 3, path, "Possivel debug residual com console.log.", number)
        if re.search(r"\bdebugger\s*;?", stripped):
            _add_finding(findings, 1, path, "Debugger residual pode interromper execucao.", number)
        if stripped.startswith(("<<<<<<<", ">>>>>>>")) or stripped == "=======":
            _add_finding(findings, 0, path, "Marcador de conflito de merge encontrado.", number)
        if "TODO" in stripped or "FIXME" in stripped:
            _add_finding(findings, 3, path, "TODO/FIXME pendente em trecho de codigo.", number)


def _inspect_json(path: Path, text: str, findings: list[dict]):
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        _add_finding(findings, 0, path, f"JSON invalido: {exc.msg}", exc.lineno or 0)


def _inspect_text_file(path: Path, findings: list[dict]):
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
    except Exception as exc:
        _add_finding(findings, 0, path, f"Nao consegui ler o arquivo: {exc}")
        return

    suffix = path.suffix.lower()
    if suffix == ".py":
        _inspect_python(path, text, findings)
    elif suffix in {".js", ".jsx", ".ts", ".tsx"}:
        _inspect_js_ts(path, text, findings)
    elif suffix == ".json":
        _inspect_json(path, text, findings)
    else:
        for number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith(("<<<<<<<", ">>>>>>>")) or stripped == "=======":
                _add_finding(findings, 0, path, "Marcador de conflito de merge encontrado.", number)


def _run_powershell(script: str, timeout_seconds: int = 8) -> str:
    completed = subprocess.run(
        [POWERSHELL_EXE, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "").strip() or "Falha no PowerShell.")
    return completed.stdout or ""


def _get_clipboard_text() -> str:
    try:
        return _run_powershell("Get-Clipboard -Raw -ErrorAction SilentlyContinue", timeout_seconds=5)
    except Exception:
        return ""


def _set_clipboard_text(text: str):
    escaped = text.replace("'", "''")
    _run_powershell(f"Set-Clipboard -Value '{escaped}'", timeout_seconds=5)


def _copy_selected_text() -> str:
    previous_clipboard = _get_clipboard_text()
    sentinel = f"__AXEL_EMPTY_SELECTION_{time.time_ns()}__"
    try:
        _set_clipboard_text(sentinel)
        _run_powershell(
            "$wshell = New-Object -ComObject WScript.Shell; $wshell.SendKeys('^c')",
            timeout_seconds=5,
        )
        time.sleep(0.25)
        copied = _get_clipboard_text()
        if copied.strip() == sentinel:
            return ""
        return copied
    finally:
        try:
            _set_clipboard_text(previous_clipboard)
        except Exception:
            pass


def _guess_selected_code_path(text: str) -> Path:
    stripped = text.strip()
    if stripped.startswith(("{", "[")):
        return ROOT / "codigo_selecionado.json"
    if re.search(r"\b(def|import|from|class)\b", stripped) or "__name__" in stripped:
        return ROOT / "codigo_selecionado.py"
    if re.search(r"\b(function|const|let|var|export|import|interface|type)\b", stripped):
        return ROOT / "codigo_selecionado.ts"
    if "<html" in stripped.lower() or re.search(r"</\w+>", stripped):
        return ROOT / "codigo_selecionado.html"
    return ROOT / "codigo_selecionado.txt"


def _inspect_selected_text(text: str) -> list[dict]:
    findings = []
    pseudo_path = _guess_selected_code_path(text)
    suffix = pseudo_path.suffix.lower()
    if suffix == ".py":
        _inspect_python(pseudo_path, text, findings)
    elif suffix in {".js", ".jsx", ".ts", ".tsx"}:
        _inspect_js_ts(pseudo_path, text, findings)
    elif suffix == ".json":
        _inspect_json(pseudo_path, text, findings)
    else:
        for number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith(("<<<<<<<", ">>>>>>>")) or stripped == "=======":
                _add_finding(findings, 0, pseudo_path, "Marcador de conflito de merge encontrado.", number)
    return findings


def _format_findings(findings: list[dict], scanned_files: int, target_label: str) -> str:
    if not findings:
        return f"Inspecionei {scanned_files} arquivo(s) em {target_label} e nao achei erro evidente."

    findings.sort(key=lambda item: (item["severity"], item["path"], item["line"]))
    severity_label = {0: "critico", 1: "alto", 2: "medio", 3: "baixo"}
    rows = []
    for finding in findings[:10]:
        line_text = f":{finding['line']}" if finding["line"] else ""
        rows.append(
            f"{severity_label.get(finding['severity'], 'medio')} - {finding['path']}{line_text} - {finding['message']}"
        )

    return (
        f"Inspecionei {scanned_files} arquivo(s) em {target_label} e achei {len(findings)} ponto(s): "
        + "; ".join(rows)
        + "."
    )


def inspect_code_target(path: str | None = None, limit: int = 160) -> str:
    target = _resolve_target(path)
    if not target.exists():
        return f"Nao encontrei esse caminho para inspecao: {target}"

    findings = []
    scanned_files = 0
    for file_path in _iter_code_files(target, limit=limit):
        scanned_files += 1
        _inspect_text_file(file_path, findings)

    label = _rel(target)
    if label == ".":
        label = "workspace atual"
    return _format_findings(findings, scanned_files, label)


def inspect_workspace_code() -> str:
    return inspect_code_target(".")


def inspect_selected_code() -> str:
    try:
        text = _copy_selected_text()
    except Exception as exc:
        return f"Não consegui copiar o código selecionado para inspeção: {exc}"

    if not text.strip():
        try:
            focus_app("code")
            time.sleep(0.35)
            text = _copy_selected_text()
        except Exception:
            text = ""

    if not text.strip():
        return "Não encontrei código selecionado. Selecione o trecho no VS Code ou no app ativo e peça para inspecionar de novo."

    findings = _inspect_selected_text(text)
    line_count = max(1, len(text.splitlines()))
    if not findings:
        return f"Inspecionei o código selecionado ({line_count} linha(s)) e não achei erro evidente."
    return _format_findings(findings, 1, f"código selecionado ({line_count} linha(s))")
