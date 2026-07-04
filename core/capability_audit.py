from __future__ import annotations

from dataclasses import dataclass

from core.specialist_agents import list_agents
from memory.procedural_skills import load_skills


@dataclass(frozen=True)
class CapabilityAuditItem:
    name: str
    status: str
    summary: str
    evidence: str
    next_step: str = ""


VALID_STATUSES = ("funcional", "parcial", "visual/organizacional", "planejado")


def capability_audit_items() -> list[CapabilityAuditItem]:
    skill_count = len(load_skills())
    agent_count = len(list_agents())
    return [
        CapabilityAuditItem(
            name="Comandos e actions locais",
            status="funcional",
            summary="Abre apps/sites, executa rotas locais, lida com lembretes, briefing, arquivos, mídia e comandos compartilhados.",
            evidence="Roteadores, actions, /status, /autoteste, testes de comandos e log operacional.",
        ),
        CapabilityAuditItem(
            name="Conversa geral útil",
            status="funcional",
            summary="Responde perguntas abertas, aprendizado, inglês, treino, presentes e conselhos cotidianos sem cair em tela/carteira por engano.",
            evidence="Fast path de conversa, roteamento geral, política de modelo e autoteste de perguntas abertas.",
        ),
        CapabilityAuditItem(
            name="Arquivos e estudos",
            status="funcional",
            summary="Analisa PDF, DOCX, TXT, HTML e outros textos comuns, mantém arquivo atual e responde páginas/follow-ups quando a extração permite.",
            evidence="study_file_analysis, study_commands, cache de contexto de estudo e testes de PDF/slide.",
            next_step="Continuar melhorando OCR e PDFs estranhos.",
        ),
        CapabilityAuditItem(
            name="Briefing, agenda e lembretes",
            status="funcional",
            summary="Gera briefing com clima, agenda, carteira quando útil e cria lembretes naturais com menos confirmação quando a data está clara.",
            evidence="briefing_tools, reminder_tools, startup briefing e rotas cobertas no autoteste.",
        ),
        CapabilityAuditItem(
            name="Telegram e WhatsApp",
            status="funcional",
            summary="Aceitam comandos remotos com permissões reduzidas, comandos compartilhados e bloqueios para ações sensíveis.",
            evidence="Gateways remotos, allowlist, comandos compartilhados e testes de /autoteste remoto.",
        ),
        CapabilityAuditItem(
            name="Metas e lista de afazeres",
            status="funcional",
            summary="Funcionam como sistema operacional do projeto: mostram prioridade, próximo passo, status e evidências por item importante.",
            evidence="memory/todo.md, memory/todo_evidence.json, memory/todo_status.py e testes de comandos de prioridade.",
        ),
        CapabilityAuditItem(
            name="Agentes especialistas",
            status="parcial",
            summary=f"Existem {agent_count} perfis operacionais com roteamento, toolsets, métricas e handoff prático, mas ainda não são processos autônomos independentes.",
            evidence="core/specialist_agents.py, core/agent_operations.py, core/agent_handoff.py e rankings de capacidades.",
            next_step="Manter como agentes operacionais até haver execução independente com fila própria por agente.",
        ),
        CapabilityAuditItem(
            name="Skills procedurais",
            status="funcional",
            summary=f"Existem {skill_count} skills procedurais com gatilhos, validação de prontidão e ligação com actions quando faz sentido.",
            evidence="memory/skills, core/skill_operations.py e testes de validação de skills.",
        ),
        CapabilityAuditItem(
            name="AxelBrain",
            status="parcial",
            summary="Influencia risco, agente, toolset, memória, política de modelo, confirmação e resposta final, mas ainda não é um planejador autônomo completo.",
            evidence="core/axel_brain.py, core/axel_brain_effects.py, core/decision_orchestrator.py e comandos de auditoria.",
            next_step="Evoluir apenas onde houver efeito observável, não como painel decorativo.",
        ),
        CapabilityAuditItem(
            name="HUD",
            status="parcial",
            summary="Mostra estado real, botões com feedback e controles úteis, mas ainda contém painéis de primeira camada que dependem de integrações futuras.",
            evidence="ui_state, qt_axel_hud e command deck.",
            next_step="Continuar rotulando painéis sem backend completo como primeira camada.",
        ),
        CapabilityAuditItem(
            name="Tarefas e hábitos do HUD",
            status="visual/organizacional",
            summary="São primeira camada de visualização local, sem integração estruturada com gestor externo de tarefas ou rastreador de hábitos.",
            evidence="ui/axel_web_hud.html.",
            next_step="Integrar uma fonte real antes de prometer calendário, recorrência ou estatísticas completas.",
        ),
        CapabilityAuditItem(
            name="LED do teclado",
            status="parcial",
            summary="Primeira camada plugável: salva estado, cor, perfil e efeito para uso futuro, mas ainda não controla hardware físico sem provedor ou driver compatível.",
            evidence="tools/keyboard_led_tools.py e memory/keyboard_led_state.json.",
            next_step="Manter rotulado como primeira camada até conectar um provedor físico real.",
        ),
        CapabilityAuditItem(
            name="App Windows",
            status="parcial",
            summary="Primeira camada por atalhos e startup: pode abrir sem terminal via pythonw/atalho e registrar logs, mas ainda não é um instalador final com tray, ícone empacotado e atualização própria.",
            evidence="tools/system_tools.py, ui/ui_bridge.py, atalhos Axel.lnk e logs em .tmp.",
            next_step="Manter como app por atalho até virar empacotamento completo.",
        ),
    ]


def _group_items(items: list[CapabilityAuditItem]) -> dict[str, list[CapabilityAuditItem]]:
    grouped = {status: [] for status in VALID_STATUSES}
    for item in items:
        grouped.setdefault(item.status, []).append(item)
    return grouped


def format_real_capabilities_report() -> str:
    grouped = _group_items(capability_audit_items())
    parts = ["Capacidades reais do Axel:"]
    for status in VALID_STATUSES:
        items = grouped.get(status) or []
        if not items:
            continue
        label = status.capitalize()
        rows = []
        for item in items:
            row = f"{item.name}: {item.summary} Evidência: {item.evidence}"
            if item.next_step:
                row += f" Próximo passo: {item.next_step}"
            rows.append(row)
        parts.append(f"{label}: " + " | ".join(rows) + ".")
    parts.append("Regra prática: se não tiver comando, efeito observável, teste ou evidência, entra como parcial ou organizacional até virar capacidade real.")
    return " ".join(parts)


def capability_audit_summary() -> dict[str, int]:
    summary = {status: 0 for status in VALID_STATUSES}
    for item in capability_audit_items():
        summary[item.status] = summary.get(item.status, 0) + 1
    return summary
