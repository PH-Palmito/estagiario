from __future__ import annotations

from actions.registry import ActionSpec, register_action
from memory.action_memory import list_memory_entries, recall_memory, remember_memory
from memory.deep_memory import format_deep_memory_summary, format_domain_memory


def register_memory_actions() -> None:
    register_action(
        ActionSpec(
            name="memory.remember",
            description="Salva uma memoria simples em um namespace controlado.",
            handler=lambda args: remember_memory(
                args.get("namespace", "general"),
                args.get("key", ""),
                args.get("value"),
                tags=args.get("tags") or [],
            ),
            category="memory",
            read_only=False,
            requires_confirmation=False,
            parameters={
                "namespace": {"type": "string", "description": "Area da memoria.", "required": True},
                "key": {"type": "string", "description": "Chave da memoria.", "required": True},
                "value": {"type": "string", "description": "Valor a guardar.", "required": True},
                "tags": {"type": "array", "description": "Tags opcionais."},
            },
        )
    )
    register_action(
        ActionSpec(
            name="memory.recall",
            description="Busca uma memoria por namespace e chave.",
            handler=lambda args: recall_memory(args.get("namespace", "general"), args.get("key", "")),
            category="memory",
            read_only=True,
            parameters={
                "namespace": {"type": "string", "description": "Area da memoria.", "required": True},
                "key": {"type": "string", "description": "Chave da memoria.", "required": True},
            },
        )
    )
    register_action(
        ActionSpec(
            name="memory.list",
            description="Lista memorias de um namespace.",
            handler=lambda args: list_memory_entries(args.get("namespace", "general")),
            category="memory",
            read_only=True,
            parameters={
                "namespace": {"type": "string", "description": "Area da memoria.", "required": True},
            },
        )
    )
    register_action(
        ActionSpec(
            name="memory.deep.summary",
            description="Resume a memoria profunda local como indice/sintese curta.",
            handler=lambda args: format_deep_memory_summary(args.get("query", ""), limit=int(args.get("limit") or 6)),
            category="memory",
            read_only=True,
            parameters={
                "query": {"type": "string", "description": "Pergunta ou assunto opcional para filtrar a influencia."},
                "limit": {"type": "number", "description": "Quantidade maxima de itens relevantes."},
            },
        )
    )
    register_action(
        ActionSpec(
            name="memory.deep.domain",
            description="Consulta a memoria profunda por dominio, como treino, estudos, investimentos, programacao ou rotina.",
            handler=lambda args: format_domain_memory(args.get("domain", ""), limit=int(args.get("limit") or 8)),
            category="memory",
            read_only=True,
            parameters={
                "domain": {"type": "string", "description": "Dominio a consultar.", "required": True},
                "limit": {"type": "number", "description": "Quantidade maxima de itens."},
            },
        )
    )
    register_action(
        ActionSpec(
            name="memory.deep.explain",
            description="Explica quais memorias locais influenciaram uma resposta ou decisao.",
            handler=lambda args: format_deep_memory_summary(args.get("query", ""), limit=int(args.get("limit") or 8)),
            category="memory",
            read_only=True,
            parameters={
                "query": {"type": "string", "description": "Pergunta, resposta ou decisao a explicar.", "required": True},
                "limit": {"type": "number", "description": "Quantidade maxima de memorias influentes."},
            },
        )
    )
