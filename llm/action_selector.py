from __future__ import annotations

import json
import re

from config import OLLAMA_TEXT_MODEL
from core.tool_router import tool_definitions
from llm.ollama_client import ask_model


def _compact_catalog() -> str:
    entries = []
    for tool in tool_definitions():
        metadata = tool.get("metadata") or {}
        if not metadata.get("read_only", True):
            continue
        params = ((tool.get("parameters") or {}).get("properties") or {}).keys()
        entries.append(
            {
                "name": tool.get("name"),
                "description": tool.get("description"),
                "category": metadata.get("category"),
                "params": list(params),
            }
        )
    return json.dumps(entries, ensure_ascii=False)


def _extract_json(text: str) -> dict:
    raw = str(text or "").strip()
    if not raw:
        return {}
    match = re.search(r"\{.*\}", raw, flags=re.S)
    if match:
        raw = match.group(0)
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _deterministic_domain_match(user_input: str) -> dict | None:
    text = str(user_input or "").strip()
    normalized = text.lower()
    muscle_terms = {
        "panturrilha",
        "panturrilhas",
        "perna",
        "pernas",
        "core",
        "abdomen",
        "abdômen",
        "peito",
        "costas",
        "ombro",
        "ombros",
        "biceps",
        "bíceps",
        "triceps",
        "tríceps",
        "antebraco",
        "antebraço",
    }
    muscle_status_terms = {
        "fadiga",
        "recuperado",
        "recuperada",
        "recuperar",
        "dolorido",
        "dolorida",
        "lesao",
        "lesão",
        "machucado",
        "machucada",
    }
    if any(term in normalized for term in muscle_terms) and any(term in normalized for term in muscle_status_terms):
        return {
            "name": "training.muscle_status",
            "arguments": {"text": text},
            "confidence": 0.8,
            "reason": "Pergunta parece ser sobre fadiga ou recuperacao muscular.",
        }

    has_ticker = bool(re.search(r"\b[A-Za-z]{4,5}\d{1,2}\b", text))
    investment_terms = {
        "carteira",
        "investimento",
        "investimentos",
        "acao",
        "ações",
        "ações",
        "ativo",
        "ticker",
        "dividendo",
        "dividendos",
        "dy",
        "preco teto",
        "preço teto",
        "rentabilidade",
        "patrimonio",
        "patrimônio",
    }
    if has_ticker or any(term in normalized for term in investment_terms):
        return {
            "name": "investment.answer",
            "arguments": {"question": text},
            "confidence": 0.8,
            "reason": "Pergunta parece ser sobre investimentos.",
        }
    return None


def _coerce_arguments(name: str, user_input: str, arguments: dict) -> dict:
    args = arguments if isinstance(arguments, dict) else {}
    if name == "investment.answer" and not args.get("question"):
        args["question"] = user_input
    if name == "training.muscle_status" and not args.get("text"):
        args["text"] = user_input
    return args


def select_read_action(user_input: str) -> dict | None:
    deterministic = _deterministic_domain_match(user_input)
    if deterministic:
        return deterministic

    catalog = _compact_catalog()
    prompt = f"""
Voce escolhe uma action de leitura para o assistente Axel.
Responda somente JSON valido, sem markdown.
Se nenhuma action do catalogo servir, responda {{"name": "", "arguments": {{}}, "confidence": 0, "reason": "none"}}.

Regras:
- Use apenas actions do catalogo.
- Nunca escolha action de escrita.
- Para investment.answer, coloque a pergunta original em question.
- Para training.muscle_status, coloque a frase original em text.
- confidence deve ir de 0 a 1.

Catalogo:
{catalog}

Mensagem do usuario:
{user_input}
""".strip()

    try:
        response = ask_model(
            prompt,
            model=OLLAMA_TEXT_MODEL,
            timeout_seconds=8,
            num_predict=140,
            temperature=0.05,
        )
    except Exception:
        return None

    data = _extract_json(response)
    name = str(data.get("name", "")).strip()
    if not name:
        return None

    try:
        confidence = float(data.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0
    if confidence < 0.62:
        return None

    allowed_names = {tool.get("name") for tool in tool_definitions() if (tool.get("metadata") or {}).get("read_only", True)}
    if name not in allowed_names:
        return None

    return {
        "name": name,
        "arguments": _coerce_arguments(name, user_input, data.get("arguments") or {}),
        "confidence": confidence,
        "reason": str(data.get("reason", "")).strip(),
    }
