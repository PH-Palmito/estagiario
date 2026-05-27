from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ActionResult:
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    @classmethod
    def ok(cls, message: str = "OK.", *, data: dict[str, Any] | None = None) -> "ActionResult":
        return cls(success=True, message=str(message or "OK."), data=data or {})

    @classmethod
    def failed(cls, message: str, *, error: str = "", data: dict[str, Any] | None = None) -> "ActionResult":
        text = str(message or error or "Falha ao executar acao.")
        return cls(success=False, message=text, data=data or {}, error=str(error or text))

    def __str__(self) -> str:
        return self.message


def normalize_action_result(result: Any) -> ActionResult:
    if isinstance(result, ActionResult):
        return result
    if result is None:
        return ActionResult.ok("")
    return ActionResult.ok(str(result))
