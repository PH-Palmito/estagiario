from __future__ import annotations

import json
import re
from dataclasses import dataclass

from config import LLM_INTENT_JUDGE_ENABLED, OLLAMA_TEXT_MODEL
from core.command_schema import Command
from core.intent_judge import IntentJudgeResult, text_has_investment_context
from core.permission_policy import command_requires_confirmation, command_requires_strong_confirmation
from core.router_utils import normalize_text
from llm.ollama_client import ask_model
from memory.ui_state import load_ui_state


@dataclass(frozen=True)
class LlmIntentReview:
    verdict: str
    reason: str = ""
    message: str = ""


RISKY_ACTIONS = {
    "open_app",
    "smart_open",
    "open_url",
    "close_app",
    "smart_close_app",
    "type_text",
    "run_script",
    "system_shutdown",
    "file_create",
    "file_write",
    "file_append",
    "file_replace",
    "file_delete",
    "file_copy",
    "file_move",
    "file_rename",
    "folder_create",
}
READ_ONLY_INVESTMENT_ANSWERS = {"investment.answer", "investment_memory_answer"}


def is_llm_intent_judge_enabled() -> bool:
    try:
        state = load_ui_state()
        if isinstance(state, dict) and "llm_intent_judge_enabled" in state:
            return bool(state.get("llm_intent_judge_enabled"))
    except Exception:
        pass
    return bool(LLM_INTENT_JUDGE_ENABLED)


def _action_name(command: Command) -> str:
    action = str(getattr(command, "action", "") or "").strip()
    if action != "action_tool_execute":
        return action
    params = getattr(command, "params", {}) or {}
    return str(params.get("name") or "").strip() or action


def _looks_mixed_or_ambiguous(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return False
    if " e " in normalized and any(verb in normalized for verb in {"abra", "guarde", "salve", "desligue", "feche", "leia", "analise"}):
        return True
    return normalized in {"isso", "aquilo", "faz isso", "faz aquilo"} or len(normalized.split()) <= 2


def should_request_llm_intent_review(
    user_input: str,
    command: Command,
    *,
    route_trace: dict | None = None,
    decision_plan: dict | None = None,
) -> bool:
    if not is_llm_intent_judge_enabled():
        return False

    action = _action_name(command)
    if not action or action == "respond":
        return False
    if action in READ_ONLY_INVESTMENT_ANSWERS and text_has_investment_context(user_input):
        return False

    plan = decision_plan or {}
    try:
        confidence = float(plan.get("confidence", 1.0))
    except (TypeError, ValueError):
        confidence = 1.0

    trace = route_trace or {}
    return (
        action in RISKY_ACTIONS
        or action.startswith(("investment", "browser_", "image_analyze"))
        or command_requires_confirmation(command)
        or command_requires_strong_confirmation(command)
        or confidence < 0.62
        or _looks_mixed_or_ambiguous(user_input)
        or trace.get("group") == "conversation"
    )


def _extract_json_object(text: str) -> dict:
    raw = str(text or "").strip()
    raw = re.sub(r"^```json\s*", "", raw, flags=re.I)
    raw = re.sub(r"^```\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\{.*\}", raw, flags=re.S)
    if not match:
        return {}
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def review_intent_with_llm(
    user_input: str,
    command: Command,
    *,
    route_trace: dict | None = None,
    decision_plan: dict | None = None,
    ask_model_fn=ask_model,
) -> LlmIntentReview | None:
    action = _action_name(command)
    params = getattr(command, "params", {}) or {}
    prompt = f"""
Voce e o critico de seguranca de intencao do Axel.

Compare o pedido do usuario com a acao proposta. Responda SOMENTE JSON.

Veredictos:
- allow: a acao combina claramente com o pedido.
- confirm: a acao talvez combine, mas precisa confirmar antes.
- block: a acao nao combina ou pode ser perigosa.

Pedido do usuario: {user_input}
Acao proposta: {action}
Parametros: {json.dumps(params, ensure_ascii=False)}
Rota: {json.dumps(route_trace or {}, ensure_ascii=False)[:900]}
Plano: {json.dumps(decision_plan or {}, ensure_ascii=False)[:900]}

JSON:
{{"verdict":"allow|confirm|block","reason":"curto","message":"mensagem curta ao usuario se bloquear ou confirmar"}}
""".strip()

    try:
        response = ask_model_fn(
            prompt,
            model=OLLAMA_TEXT_MODEL,
            timeout_seconds=6,
            num_predict=120,
            temperature=0.1,
            provider="local",
        )
    except Exception:
        return None

    payload = _extract_json_object(response)
    verdict = str(payload.get("verdict") or "").strip().lower()
    if verdict not in {"allow", "confirm", "block"}:
        return None

    return LlmIntentReview(
        verdict=verdict,
        reason=str(payload.get("reason") or "").strip()[:180],
        message=str(payload.get("message") or "").strip()[:260],
    )


def llm_review_to_judge_result(review: LlmIntentReview | None) -> IntentJudgeResult:
    if review is None or review.verdict == "allow":
        return IntentJudgeResult()
    if review.verdict == "confirm":
        return IntentJudgeResult(
            allowed=True,
            requires_confirmation=True,
            reason=f"llm_intent_confirm:{review.reason}",
            message=review.message,
        )
    return IntentJudgeResult(
        allowed=False,
        reason=f"llm_intent_block:{review.reason}",
        message=review.message or "Interpretação insegura. Vou evitar executar essa ação sem um pedido mais claro.",
    )
