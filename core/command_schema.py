from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Command:
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    source: str = "router"
    confidence: float = 1.0
    requires_confirmation: bool = False