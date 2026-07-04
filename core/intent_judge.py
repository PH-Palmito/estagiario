from __future__ import annotations

import re
from dataclasses import dataclass

from core.command_schema import Command
from core.router_utils import normalize_text


@dataclass(frozen=True)
class IntentJudgeResult:
    allowed: bool = True
    requires_confirmation: bool = False
    reason: str = ""
    message: str = ""


INVESTMENT_ACTION_PREFIXES = (
    "investment",
    "background_investment",
    "browser_investment",
)

INVESTMENT_KEYWORDS = {
    "acao",
    "acoes",
    "ativo",
    "ativos",
    "bbas",
    "carteira",
    "cotacao",
    "cripto",
    "dividendo",
    "fii",
    "fiis",
    "financeiro",
    "investimento",
    "investimentos",
    "patrimonio",
    "preco teto",
    "rentabilidade",
    "tesouro",
    "ticker",
}
TICKER_PATTERN = re.compile(r"\b[a-z]{4}\d{1,2}\b", re.I)

OPEN_TERMS = {"abra", "abre", "abrir", "inicie", "iniciar", "ligue", "ligar", "abrindo"}
CLOSE_TERMS = {"feche", "fecha", "fechar", "encerre", "encerrar", "desligue", "desligar"}
SCREEN_TERMS = {"tela", "pagina", "visivel", "visible", "isso", "ai", "aqui", "selecionado", "selecao"}
QUESTION_TERMS = {"o que", "oq", "oque", "qual", "como", "por que", "porque", "quem"}


def _action_name(command: Command) -> str:
    action = str(getattr(command, "action", "") or "").strip()
    if action != "action_tool_execute":
        return action
    params = getattr(command, "params", {}) or {}
    return str(params.get("name") or "").strip() or action


def _target_text(command: Command) -> str:
    params = getattr(command, "params", {}) or {}
    values = []
    for key in ("target", "query", "ticker", "name", "path", "location"):
        value = params.get(key)
        if value:
            values.append(str(value))
    return normalize_text(" ".join(values))


def _term_in_text(text: str, term: str) -> bool:
    if " " in term:
        return term in text
    return bool(re.search(rf"\b{re.escape(term)}\b", text))


def _has_any(text: str, terms: set[str]) -> bool:
    return any(_term_in_text(text, term) for term in terms)


def text_has_investment_context(text: str) -> bool:
    normalized = normalize_text(text)
    return _has_any(normalized, INVESTMENT_KEYWORDS) or bool(TICKER_PATTERN.search(normalized))


def judge_command_interpretation(user_input: str, command: Command, *, route_trace: dict | None = None) -> IntentJudgeResult:
    text = normalize_text(user_input)
    action = _action_name(command)
    target = _target_text(command)

    if not text or action == "respond":
        return IntentJudgeResult()

    if action.startswith(INVESTMENT_ACTION_PREFIXES) and not text_has_investment_context(text):
        return IntentJudgeResult(
            allowed=False,
            reason="investment_action_without_investment_terms",
            message=(
                "Segurei essa ação: o pedido não parece ser sobre carteira ou investimentos, "
                "então não vou acionar rotinas financeiras."
            ),
        )

    if action in {"open_app", "smart_open", "open_url"}:
        if not _has_any(text, OPEN_TERMS) and target and target not in text:
            return IntentJudgeResult(
                allowed=False,
                reason="open_action_without_open_intent",
                message=f"Segurei a abertura de {target}: o pedido não parecia pedir para abrir isso.",
            )

    if action in {"close_app", "smart_close_app"} and not _has_any(text, CLOSE_TERMS):
        return IntentJudgeResult(
            allowed=True,
            requires_confirmation=True,
            reason="close_action_needs_confirmation",
        )

    if action in {"browser_describe_screen", "browser_explain_screen", "browser_summarize_screen", "image_analyze_screen"}:
        if _has_any(text, QUESTION_TERMS) and not _has_any(text, SCREEN_TERMS):
            return IntentJudgeResult(
                allowed=False,
                reason="screen_action_for_general_question",
                message=(
                    "Segurei a leitura da tela: essa parece uma pergunta geral. "
                    "Se quiser que eu olhe a tela, peça isso claramente."
                ),
            )

    trace = route_trace or {}
    if trace.get("group") == "conversation" and action != "respond":
        return IntentJudgeResult(
            allowed=True,
            requires_confirmation=True,
            reason="conversation_route_with_action",
        )

    return IntentJudgeResult()
