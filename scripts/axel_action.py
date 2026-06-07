from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.action_rpc import (
    action_rpc_catalog,
    action_rpc_execute,
    action_rpc_execute_json,
    action_rpc_schema,
    format_action_rpc_payload,
)


def _coerce_arg_value(value: str):
    text = str(value or "")
    lowered = text.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _parse_key_values(items: list[str]) -> tuple[dict, str]:
    values = {}
    for item in items:
        if "=" not in str(item or ""):
            return {}, f"Argumento invalido em --arg: {item}. Use chave=valor."
        key, value = str(item).split("=", 1)
        key = key.strip()
        if not key:
            return {}, "Argumento invalido em --arg: chave vazia."
        values[key] = _coerce_arg_value(value)
    return values, ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Executa actions do Axel por RPC local seguro.")
    parser.add_argument("action", nargs="?", default="", help="Nome da action a executar.")
    parser.add_argument("--json", default="", help="Argumentos JSON para a action.")
    parser.add_argument("--arg", action="append", default=[], help="Argumento simples chave=valor; pode repetir.")
    parser.add_argument("--list", action="store_true", help="Lista actions registradas.")
    parser.add_argument("--schema", action="store_true", help="Mostra schema da action informada.")
    parser.add_argument("--category", default="", help="Filtra lista por categoria.")
    parser.add_argument("--allow-write", action="store_true", help="Permite actions de escrita em scripts confiaveis.")
    args = parser.parse_args(argv)

    if args.list:
        payload = action_rpc_catalog(args.category or None)
    elif args.schema:
        payload = action_rpc_schema(args.action)
    elif args.action:
        if args.arg:
            arguments, error = _parse_key_values(args.arg)
            if error:
                payload = {"ok": False, "action": args.action, "error": error}
            else:
                payload = action_rpc_execute(args.action, arguments, allow_write=bool(args.allow_write))
        else:
            payload = action_rpc_execute_json(args.action, args.json, allow_write=bool(args.allow_write))
    else:
        payload = {"ok": False, "error": "Informe uma action, --list ou --schema."}

    print(format_action_rpc_payload(payload))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
