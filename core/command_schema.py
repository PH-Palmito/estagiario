from dataclasses import dataclass, field
from typing import Any


@dataclass
class Command:
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    source: str = "router"
    confidence: float = 1.0
    requires_confirmation: bool = False