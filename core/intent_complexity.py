from __future__ import annotations

from dataclasses import dataclass

from core.router_registry import (
    INTENT_LEVEL_COMPOSITE_TASK,
    INTENT_LEVEL_CONVERSATION,
    INTENT_LEVEL_DIRECT_COMMAND,
    INTENT_LEVEL_QUESTION,
)

SIMPLE_COMMAND = "simple_command"
COMPLEX_REASONING = "complex_reasoning"

COMPLEX_TEXT_HINTS = {
    "compare",
    "comparar",
    "analise",
    "analisar",
    "avalie",
    "avaliar",
    "explique",
    "explica",
    "planeje",
    "planejar",
    "estrategia",
    "estratégia",
    "cenario",
    "cenário",
    "vale a pena",
    "por que",
    "porque",
    "opina",
    "opiniao",
    "opinião",
    "riscos",
    "decida",
    "decidir",
}


@dataclass(frozen=True)
class IntentComplexity:
    kind: str
    reason: str
    should_plan: bool = False
    should_use_llm: bool = False

    @property
    def is_complex(self) -> bool:
        return self.kind == COMPLEX_REASONING


def _normalize(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def text_looks_complex(user_input: str) -> bool:
    normalized = _normalize(user_input)
    if not normalized:
        return False
    if any(hint in normalized for hint in COMPLEX_TEXT_HINTS):
        return True
    return len(normalized.split()) >= 18


def classify_intent_complexity(
    user_input: str,
    *,
    intent_level: str,
    raw_action: dict | None = None,
) -> IntentComplexity:
    raw_action = raw_action or {}
    intent = str(raw_action.get("intent") or "")
    looks_complex = text_looks_complex(user_input)

    if intent_level == INTENT_LEVEL_DIRECT_COMMAND and not looks_complex:
        return IntentComplexity(SIMPLE_COMMAND, "comando direto deterministico")

    if intent_level == INTENT_LEVEL_COMPOSITE_TASK:
        return IntentComplexity(COMPLEX_REASONING, "tarefa composta", should_plan=True, should_use_llm=looks_complex)

    if intent_level == INTENT_LEVEL_QUESTION:
        return IntentComplexity(
            COMPLEX_REASONING if looks_complex else SIMPLE_COMMAND,
            "pergunta complexa" if looks_complex else "pergunta simples",
            should_use_llm=looks_complex,
        )

    if intent_level == INTENT_LEVEL_CONVERSATION:
        return IntentComplexity(
            COMPLEX_REASONING if looks_complex else SIMPLE_COMMAND,
            "conversa com raciocinio" if looks_complex else "conversa simples",
            should_use_llm=True,
        )

    if looks_complex:
        return IntentComplexity(COMPLEX_REASONING, "texto longo ou analitico", should_use_llm=True)

    return IntentComplexity(SIMPLE_COMMAND, "fallback simples")
