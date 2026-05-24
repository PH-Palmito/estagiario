from __future__ import annotations

import argparse
import compileall
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPILE_TARGETS = (
    "main.py",
    "core",
    "llm",
    "memory",
    "tools",
    "voice",
)


def compile_targets() -> int:
    failed = False
    for target in COMPILE_TARGETS:
        path = ROOT / target
        if not path.exists():
            continue
        if path.is_file():
            result = subprocess.run([sys.executable, "-m", "py_compile", str(path)], cwd=ROOT, stderr=subprocess.STDOUT)
            failed = failed or result.returncode != 0
        else:
            failed = failed or not compileall.compile_dir(str(path), quiet=1)
    return 1 if failed else 0


def run_unittest() -> int:
    return subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-v"],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
    ).returncode


def run_ruff() -> int:
    if importlib.util.find_spec("ruff") is None:
        print("Ruff nao esta instalado. Rode: .\\venv\\Scripts\\pip.exe install -r requirements-dev.txt")
        return 1
    result = subprocess.run([sys.executable, "-m", "ruff", "check", "."], cwd=ROOT, stderr=subprocess.STDOUT)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Roda verificacoes locais do Axel.")
    parser.add_argument("--lint", action="store_true", help="Tambem roda Ruff, se instalado.")
    args = parser.parse_args()

    checks = [
        ("compile", compile_targets),
        ("tests", run_unittest),
    ]
    if args.lint:
        checks.append(("ruff", run_ruff))

    for name, check in checks:
        print(f"\n== {name} ==", flush=True)
        result = check()
        if result != 0:
            return result

    print("\nTudo certo.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
