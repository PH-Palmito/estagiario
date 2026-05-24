from __future__ import annotations

import json
from pathlib import Path

from core.router_utils import normalize_text

DIRECTIVES_PATH = Path(__file__).resolve().parents[1] / "memory" / "axel_directives.json"


def load_axel_directives() -> dict:
    try:
        data = json.loads(DIRECTIVES_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def maybe_handle_directives_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)
    if normalized not in {
        "diretrizes",
        "diretrizes do axel",
        "diretrizes do axe",
        "mostrar diretrizes",
        "modo investimentos",
        "modo investimento",
        "base do modo investimentos",
        "como funciona modo investimentos",
    } and not (normalized.startswith("diretrizes") and "axe" in normalized):
        return None

    payload = load_axel_directives()
    if not payload:
        return "Ainda nao consegui carregar minhas diretrizes."

    if normalized in {"modo investimentos", "modo investimento"}:
        return (
            "Modo investimentos pronto para leitura de tela. Abra sua carteira ou ativo e diga: "
            "analisar investimentos, resumo financeiro ou analisar carteira."
        )

    if "investimento" in normalized:
        investment = payload.get("investment_mode") or {}
        goal = str(investment.get("goal", "")).strip()
        rules = [str(item) for item in (investment.get("rules") or [])[:3]]
        if not goal:
            return "Modo investimentos ainda esta sem diretrizes configuradas."
        suffix = " Regras: " + "; ".join(rules) + "." if rules else ""
        return f"Modo investimentos preparado. {goal}{suffix}"

    directives = [str(item) for item in (payload.get("core_directives") or [])[:4]]
    if not directives:
        return "Minhas diretrizes ainda estao vazias."
    return "Diretrizes do Axel: " + "; ".join(directives) + "."
