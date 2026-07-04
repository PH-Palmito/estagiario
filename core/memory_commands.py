from __future__ import annotations

import re

from core.project_health import format_latency_report
from core.router_utils import normalize_text
from core.toolsets import format_relevant_toolsets, format_toolset_catalog
from core.specialist_agents import format_agent_catalog, format_relevant_agents
from core.agent_tool_library import format_agent_tool_library
from core.agent_handoff import format_handoff_plan_for_task
from core.agent_operations import format_agent_operations_detail, format_agent_operations_overview
from core.skill_operations import format_actionable_skill_detail, format_actionable_skills_overview
from memory.long_memory import curate_recent_ui_history, format_clean_long_memory_report, format_long_memory, maybe_remember_from_user_text
from memory.session import recent_turns
from memory.operational_context import (
    forget_operational_preference,
    format_operational_context,
    format_operational_memory,
    remember_operational_preference,
    save_operational_context,
)
from memory.workspace_context import format_workspace_context
from memory.browser_product_cache import cheapest_cached_product, format_cached_products
from memory.session_index import format_session_search
from memory.procedural_skills import create_skill_from_request, format_skill_catalog, format_relevant_skills
from memory.skill_learning import approve_pending_skill_suggestion, format_pending_skill_suggestions, reject_pending_skill_suggestion
from memory.layered_recall import format_layered_memory_recall
from memory.episodic_memory import (
    build_episode_summary,
    format_episode,
    format_episode_list,
    format_episode_search,
    save_episode_summary,
)
from memory.task_evaluation import (
    format_latest_task_evaluation,
    format_task_evaluation_summary,
    update_latest_task_evaluation,
)
from memory.todo_status import (
    format_todo_evidence_audit,
    format_current_priority_evidence,
    format_next_todo_step,
    format_todo_priorities,
    parse_and_add_current_priority_evidence,
    update_current_priority_status,
)
from memory.capability_ranking import format_capability_rankings
from memory.workflow_planner import (
    close_workflow_plan,
    create_workflow_plan,
    format_workflow_list,
    format_workflow_plan,
    update_workflow_step,
)


def _recent_turn_text(role: str, *, skip_meta: bool = False) -> str:
    for item in reversed(recent_turns(limit=24)):
        if str(item.get("role") or "").strip() != role:
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        if skip_meta:
            normalized = normalize_text(text)
            if any(
                phrase in normalized
                for phrase in {
                    "qual foi minha ultima pergunta",
                    "qual foi a minha ultima pergunta",
                    "minha ultima pergunta",
                    "qual foi sua ultima resposta",
                    "qual foi a sua ultima resposta",
                    "sua ultima resposta",
                    "repita a ultima resposta",
                    "repetir ultima resposta",
                }
            ):
                continue
        return text
    return ""


def _format_recent_turn_question(user_input: str) -> str | None:
    normalized = normalize_text(user_input)
    if normalized in {
        "qual foi minha ultima pergunta",
        "qual foi a minha ultima pergunta",
        "qual foi minha pergunta anterior",
        "qual foi a minha pergunta anterior",
        "minha ultima pergunta",
        "ultima pergunta que eu fiz",
        "ultima coisa que eu perguntei",
    }:
        question = _recent_turn_text("user", skip_meta=True)
        if question:
            return f"Sua ultima pergunta foi: {question}"
        return "Ainda nao tenho uma pergunta anterior guardada nesta sessao."

    if normalized in {
        "qual foi sua ultima resposta",
        "qual foi a sua ultima resposta",
        "qual foi tua ultima resposta",
        "sua ultima resposta",
        "ultima resposta do axel",
        "repita a ultima resposta",
        "repetir ultima resposta",
    }:
        response = _recent_turn_text("assistant", skip_meta=True)
        if response:
            return f"Minha ultima resposta foi: {response}"
        return "Ainda nao tenho uma resposta anterior guardada nesta sessao."

    return None


def maybe_handle_operational_context_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)
    compact = re.sub(r"\s+", " ", normalized).strip()
    raw = str(user_input or "").strip()

    recent_turn_answer = _format_recent_turn_question(user_input)
    if recent_turn_answer:
        return recent_turn_answer

    remember_match = re.match(
        r"^(?:lembre|lembra|memorize|salve|guarde)\s+(?:na\s+)?"
        r"(?:mem.ria operacional|contexto operacional|prefer.ncia operacional)\s+(?:que\s+)?(.+)$",
        raw,
        flags=re.I,
    )
    if remember_match:
        return remember_operational_preference(remember_match.group(1), kind="preference")

    note_match = re.match(
        r"^(?:anote|registre)\s+(?:no\s+)?(?:contexto operacional|mem.ria operacional)\s+(?:que\s+)?(.+)$",
        raw,
        flags=re.I,
    )
    if note_match:
        return remember_operational_preference(note_match.group(1), kind="note")

    forget_match = re.match(
        r"^(?:esque.a|esqueca|remova|apague)\s+(?:da\s+)?"
        r"(?:mem.ria operacional|contexto operacional|prefer.ncia operacional)\s+(.+)$",
        raw,
        flags=re.I,
    )
    if forget_match:
        return forget_operational_preference(forget_match.group(1))

    if normalized in {
        "minhas preferencias operacionais",
        "preferencias operacionais",
        "memoria operacional salva",
        "mostrar memoria operacional",
    }:
        return format_operational_memory()

    if normalized in {
        "contexto do workspace",
        "contexto do projeto",
        "instrucoes do workspace",
        "instrucoes do projeto",
        "agents do projeto",
        "agents md",
    }:
        return format_workspace_context()

    if normalized in {
        "produtos recentes",
        "produtos em cache",
        "ultimos produtos",
        "ultimos produtos vistos",
        "últimos produtos",
        "últimos produtos vistos",
    }:
        return format_cached_products()

    if normalized in {
        "produto mais barato em cache",
        "mais barato em cache",
        "mais barato recente",
        "produto mais barato recente",
    }:
        return cheapest_cached_product()

    if normalized in {
        "qual meu foco",
        "qual o meu foco",
        "qual nosso foco",
        "o que estamos fazendo",
        "em que estamos agora",
        "resumir contexto",
        "resuma o contexto",
        "contexto atual",
        "contexto operacional",
        "qual o contexto atual",
        "o que voce sabe sobre mim agora",
    }:
        return format_operational_context()

    if normalized in {
        "atualizar contexto",
        "atualiza contexto",
        "atualizar contexto operacional",
        "recarregar contexto",
    }:
        payload = save_operational_context()
        summary = str(payload.get("summary", "")).strip()
        if summary:
            return "Contexto operacional atualizado. " + summary
        return "Contexto operacional atualizado."

    if ("context" in compact or "contr" in compact) and ("operac" in compact or "atual" in compact):
        return format_operational_context()

    if normalized in {
        "quais apps recentes",
        "apps recentes",
        "aplicativos recentes",
        "aplicativo recente",
        "sites recentes",
        "quais sites recentes",
        "topicos recentes",
    }:
        payload = save_operational_context()
        apps = payload.get("recent_apps") or []
        sites = payload.get("recent_sites") or []
        topics = payload.get("recent_topics") or []
        wants_apps = any(token in compact for token in {"app", "aplicativo"})
        wants_sites = "site" in compact
        wants_topics = any(token in compact for token in {"topico", "topicos"})

        if wants_apps and apps:
            return "Apps recentes: " + ", ".join(str(item) for item in apps[:4]) + "."
        if wants_apps:
            return "Ainda nao tenho apps recentes suficientes para resumir."

        if wants_sites and sites:
            return "Sites recentes: " + ", ".join(str(item) for item in sites[:4]) + "."
        if wants_sites:
            return "Ainda nao tenho sites recentes suficientes para resumir."

        if wants_topics and topics:
            return "Topicos recentes: " + ", ".join(str(item) for item in topics[:5]) + "."
        if wants_topics:
            return "Ainda nao tenho topicos recentes suficientes para resumir."

        parts = []
        if apps:
            parts.append("Apps: " + ", ".join(str(item) for item in apps[:4]) + ".")
        if sites:
            parts.append("Sites: " + ", ".join(str(item) for item in sites[:4]) + ".")
        if topics:
            parts.append("Topicos: " + ", ".join(str(item) for item in topics[:5]) + ".")
        return " ".join(parts) if parts else "Ainda nao tenho atividade recente suficiente para resumir."

    return None


def maybe_handle_long_memory_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)
    raw = str(user_input or "").strip()

    tool_library_match = re.match(
        r"^(?:ferramentas|biblioteca de ferramentas|tools)\s+"
        r"(?:do|da|de)?\s*(?:agente\s+)?(?P<agent>[a-zA-Z0-9_-]+(?:_agent)?)$",
        raw,
        flags=re.I,
    )
    if tool_library_match:
        return format_agent_tool_library(tool_library_match.group("agent"))

    ranking_match = re.match(
        r"^(?:ranking|rank|classificacao|classifica..o)\s+(?:de|dos|das|do)?\s*"
        r"(?P<kind>skills?|toolsets?|agentes?|agents?|actions?|acoes|a..es|capacidades|axel)?$",
        raw,
        flags=re.I,
    )
    if ranking_match:
        kind = ranking_match.group("kind") or "all"
        if normalize_text(kind) in {"capacidades", "axel"}:
            kind = "all"
        return format_capability_rankings(kind)

    if normalized in {
        "prioridades do axel",
        "prioridade do axel",
        "lista de prioridades",
        "lista de afazeres do axel",
        "afazeres do axel",
        "metas do axel",
        "status das metas",
        "status das metas do axel",
        "como estamos nas prioridades",
        "como estamos na lista de prioridades",
        "como esta a lista de prioridades",
        "como está a lista de prioridades",
    }:
        return format_todo_priorities()

    if normalized in {
        "auditar evidencias das metas",
        "auditar evidências das metas",
        "auditoria de evidencias das metas",
        "auditoria de evidências das metas",
        "metas sem evidencia",
        "metas sem evidência",
        "quais metas nao tem evidencia",
        "quais metas não têm evidência",
        "quais metas nao tem evidencias",
        "quais metas não têm evidências",
    }:
        return format_todo_evidence_audit()

    if normalized in {
        "proximo passo",
        "próximo passo",
        "proximo passo do axel",
        "próximo passo do axel",
        "qual o proximo passo",
        "qual o próximo passo",
        "qual proximo passo",
        "qual próximo passo",
        "o que falta fazer no axel",
        "oq falta fazer no axel",
        "o que falta no axel",
        "oq falta no axel",
    }:
        return format_next_todo_step()

    todo_update_match = re.match(
        r"^(?P<action>concluir|conclua|finalizar|finalize|marcar|marque)\s+"
        r"(?:a\s+)?(?:meta|tarefa|prioridade|item)\s+(?P<index>\d+)"
        r"(?:\s+(?:como\s+)?(?P<state>concluida|concluída|feita|feito|ok))?$",
        raw,
        flags=re.I,
    )
    if todo_update_match:
        return update_current_priority_status(int(todo_update_match.group("index")), done=True)

    todo_evidence_show_match = re.match(
        r"^(?:mostrar|mostre|ver|consultar|consulte)\s+"
        r"(?:a\s+)?(?:evidencia|evidência|evidencias|evidências)\s+"
        r"(?:da\s+)?(?:meta|tarefa|prioridade|item)\s+(?P<index>\d+)$",
        raw,
        flags=re.I,
    )
    if todo_evidence_show_match:
        return format_current_priority_evidence(int(todo_evidence_show_match.group("index")))

    todo_evidence_add_match = re.match(
        r"^(?:registrar|registre|adicionar|adicione|salvar|salve)\s+"
        r"(?:a\s+)?(?:evidencia|evidência|evidencias|evidências)\s+"
        r"(?:da\s+)?(?:meta|tarefa|prioridade|item)\s+(?P<index>\d+)\s*(?::|-)?\s*(?P<evidence>.+)$",
        raw,
        flags=re.I,
    )
    if todo_evidence_add_match:
        return parse_and_add_current_priority_evidence(
            int(todo_evidence_add_match.group("index")),
            todo_evidence_add_match.group("evidence"),
        )

    if normalized in {
        "autoavaliacao de tarefas",
        "avaliacao de tarefas",
        "mostrar autoavaliacao",
        "resumo de autoavaliacao",
        "status das execucoes",
    }:
        return format_task_evaluation_summary()

    if normalized in {
        "ultima autoavaliacao",
        "ultima avaliacao",
        "ultima tarefa avaliada",
    }:
        return format_latest_task_evaluation()

    latest_eval_match = re.match(
        r"^(?:a\s+)?(?:ultima|última)\s+(?:tarefa|execucao|execução|acao|ação|comando)\s+"
        r"(?P<status>funcionou|falhou|nao funcionou|não funcionou|precisa ajuste|precisa de ajuste)"
        r"(?:\s+(?P<note>.+))?$",
        raw,
        flags=re.I,
    )
    if latest_eval_match:
        status = latest_eval_match.group("status")
        status = "needs_adjustment" if "ajuste" in normalize_text(status) else status
        updated = update_latest_task_evaluation(status, note=latest_eval_match.group("note") or "")
        if not updated:
            return "Ainda nao ha tarefa recente para avaliar."
        return "Autoavaliacao registrada. " + format_latest_task_evaluation()

    if normalized in {
        "latencia do axel",
        "latencias do axel",
        "gargalos do axel",
        "gargalos recentes",
        "performance do axel",
        "relatorio de latencia",
        "relatorio de performance",
    }:
        return format_latency_report()

    if normalized in {
        "salvar episodio",
        "salvar memoria episodica",
        "atualizar memoria episodica",
        "criar resumo episodico",
        "resumir sessao",
        "resumo da sessao",
    }:
        episode = save_episode_summary(build_episode_summary())
        return "Memoria episodica atualizada. " + format_episode(episode)

    if normalized in {
        "memoria episodica",
        "mostrar memoria episodica",
        "ultimo episodio",
        "resumo episodico",
        "resumo da ultima sessao",
    }:
        return format_episode()

    if normalized in {
        "episodios recentes",
        "listar episodios",
        "listar memoria episodica",
    }:
        return format_episode_list()

    episode_search = re.match(
        r"^(?:buscar|busque|procure|procurar)\s+(?:na\s+)?(?:memoria episodica|episodios?)\s+(?:sobre\s+)?(.+)$",
        raw,
        flags=re.I,
    )
    if episode_search:
        return format_episode_search(episode_search.group(1))

    layered_recall_match = re.match(
        r"^(?:recall|lembrar|lembre|buscar|busque|consultar|consulte)\s+"
        r"(?:memoria\s+)?(?:em\s+camadas|camadas|completa|completo)?\s*"
        r"(?:sobre|de|para)?\s+(.+)$",
        raw,
        flags=re.I,
    )
    if layered_recall_match and any(token in normalized for token in {"recall", "memoria em camadas", "camadas"}):
        include_transcript = any(token in normalized for token in {"completa", "completo", "transcript", "original"})
        return format_layered_memory_recall(layered_recall_match.group(1), include_transcript=include_transcript)

    create_workflow_match = re.match(
        r"^(?:criar|crie|montar|monte|salvar|salve|planejar|planeje)\s+"
        r"(?:(?:um|uma)\s+)?(?:workflow|plano)\s+"
        r"(?:duravel\s+)?(?:para|de|sobre)\s+(.+)$",
        raw,
        flags=re.I,
    )
    if create_workflow_match:
        plan = create_workflow_plan(create_workflow_match.group(1))
        return "Workflow duravel criado. " + format_workflow_plan(plan)

    if normalized in {
        "workflow atual",
        "plano duravel atual",
        "mostrar workflow atual",
        "mostrar plano duravel",
        "retomar workflow",
        "retomar plano duravel",
    }:
        return format_workflow_plan()

    if normalized in {
        "listar workflows",
        "listar workflows duraveis",
        "listar planos duraveis",
        "workflows duraveis",
        "planos duraveis",
    }:
        return format_workflow_list()

    step_match = re.match(
        r"^(?:marcar|concluir|finalizar)\s+(?:a\s+)?(?:etapa|tarefa)\s+(\d+)\s+"
        r"(?:do\s+)?(?:workflow|plano)(?:\s+duravel)?$",
        raw,
        flags=re.I,
    )
    if step_match:
        updated = update_workflow_step(int(step_match.group(1)), status="done")
        if not updated:
            return "Nao encontrei essa etapa no workflow atual."
        return "Etapa atualizada. " + format_workflow_plan(updated)

    block_match = re.match(
        r"^(?:bloquear|bloqueie)\s+(?:a\s+)?(?:etapa|tarefa)\s+(\d+)\s+"
        r"(?:do\s+)?(?:workflow|plano)(?:\s+duravel)?$",
        raw,
        flags=re.I,
    )
    if block_match:
        updated = update_workflow_step(int(block_match.group(1)), status="blocked")
        if not updated:
            return "Nao encontrei essa etapa no workflow atual."
        return "Etapa bloqueada. " + format_workflow_plan(updated)

    close_match = re.match(
        r"^(?:fechar|finalizar|concluir)\s+(?:o\s+)?(?:workflow|plano)\s+duravel"
        r"(?:\s+(?:com|porque|pois)\s+(.+))?$",
        raw,
        flags=re.I,
    )
    if close_match:
        closed = close_workflow_plan(close_match.group(1) or "")
        if not closed:
            return "Nao encontrei workflow duravel para fechar."
        return "Workflow duravel fechado. " + format_workflow_plan(closed)

    if normalized in {
        "listar skills",
        "listar skills do axel",
        "skills do axel",
        "quais skills",
        "quais skills do axel",
    }:
        return format_skill_catalog()

    if normalized in {
        "skills acionaveis",
        "skills acionáveis",
        "skills funcionais",
        "status das skills",
        "status das skills do axel",
        "capacidades das skills",
    }:
        return format_actionable_skills_overview()

    actionable_skill_match = re.match(
        r"^(?:detalhar|detalhe|mostrar|mostre|status|validar|valide)\s+"
        r"(?:a\s+)?(?:skill|procedimento)\s+(?P<skill>.+)$",
        raw,
        flags=re.I,
    )
    if actionable_skill_match:
        return format_actionable_skill_detail(actionable_skill_match.group("skill"))

    if normalized in {
        "sugestoes de skills",
        "sugestoes de skill",
        "skills sugeridas",
        "sugestoes procedurais",
    }:
        return format_pending_skill_suggestions()

    create_skill_match = re.match(
        r"^(?:criar|crie|gera|gerar|salvar|salve)\s+"
        r"(?:uma\s+)?(?:nova\s+)?skill\s+"
        r"(?:para|de|sobre)?\s*(.+)$",
        raw,
        flags=re.I,
    )
    if create_skill_match:
        request = create_skill_match.group(1).strip()
        try:
            path = create_skill_from_request(request)
        except ValueError:
            return "Me diga melhor para que essa skill deve servir."
        return f"Skill procedural criada e salva em {path}."

    approve_skill_match = re.match(
        r"^(?:aprovar|aprove|criar|salvar)\s+"
        r"(?:a\s+)?(?:skill|sugestao de skill|sugestao procedural)"
        r"(?:\s+(\d+))?$",
        raw,
        flags=re.I,
    )
    if approve_skill_match:
        index = int(approve_skill_match.group(1) or "1")
        return approve_pending_skill_suggestion(index=index)

    reject_skill_match = re.match(
        r"^(?:rejeitar|rejeite|recusar|descarte|descartar)\s+"
        r"(?:a\s+)?(?:skill|sugestao de skill|sugestao procedural)"
        r"(?:\s+(\d+))?$",
        raw,
        flags=re.I,
    )
    if reject_skill_match:
        index = int(reject_skill_match.group(1) or "1")
        return reject_pending_skill_suggestion(index=index)

    skill_match = re.match(
        r"^(?:qual|quais|mostrar|mostre|busque|procure)\s+"
        r"(?:skill|skills|procedimento|procedimentos)\s+"
        r"(?:para|sobre|de)?\s*(.+)$",
        raw,
        flags=re.I,
    )
    if skill_match:
        return format_relevant_skills(skill_match.group(1), limit=3)

    if normalized in {
        "listar toolsets",
        "listar toolsets do axel",
        "toolsets do axel",
        "quais toolsets",
        "quais toolsets do axel",
    }:
        return format_toolset_catalog()

    toolset_match = re.match(
        r"^(?:qual|quais|mostrar|mostre|busque|procure)\s+"
        r"(?:toolset|toolsets|ferramentas|modo)\s+"
        r"(?:para|sobre|de)?\s*(.+)$",
        raw,
        flags=re.I,
    )
    if toolset_match:
        return format_relevant_toolsets(toolset_match.group(1), limit=3)

    if normalized in {
        "agentes operacionais",
        "agentes operacionais do axel",
        "status dos agentes",
        "status dos agentes do axel",
        "painel dos agentes",
        "painel de agentes",
    }:
        return format_agent_operations_overview()

    agent_detail_match = re.match(
        r"^(?:detalhar|detalhe|mostrar|mostre|status|painel)\s+"
        r"(?:do\s+)?(?:agente\s+)?(?P<agent>[a-zA-Z0-9_-]+(?:_agent)?|programacao|programação|pesquisa|investimentos|navegacao|navegação|sistema|memoria|memória|voz)$",
        raw,
        flags=re.I,
    )
    if agent_detail_match:
        return format_agent_operations_detail(agent_detail_match.group("agent"))

    handoff_match = re.match(
        r"^(?:handoff|planejar agentes|planeje agentes|quais agentes|cadeia de agentes|orquestrar agentes)\s+"
        r"(?:para|pra|sobre|de)?\s*(?P<task>.+)$",
        raw,
        flags=re.I,
    )
    if handoff_match:
        return format_handoff_plan_for_task(handoff_match.group("task"))

    if normalized in {
        "listar agentes",
        "listar agentes do axel",
        "agentes do axel",
        "quais agentes",
        "quais agentes do axel",
    }:
        return format_agent_catalog()

    agent_match = re.match(
        r"^(?:qual|quais|mostrar|mostre|busque|procure)\s+"
        r"(?:agente|agentes|especialista|especialistas)\s+"
        r"(?:para|sobre|de)?\s*(.+)$",
        raw,
        flags=re.I,
    )
    if agent_match:
        return format_relevant_agents(agent_match.group(1), limit=3)

    session_match = re.match(
        r"^(?:lembra|lembre|procure|busque|pesquise)\s+"
        r"(?:(?:quando|se)\s+)?(?:falamos|conversamos|falou|conversei)\s+"
        r"(?:sobre\s+)?(.+)$",
        raw,
        flags=re.I,
    )
    if session_match:
        return format_session_search(session_match.group(1))

    if normalized in {
        "memoria longa",
        "memoria longa do axel",
        "mostrar memoria longa",
        "listar memoria longa",
        "o que tem na memoria longa",
    }:
        return format_long_memory()

    if normalized in {
        "curar memoria",
        "curar memoria longa",
        "atualizar memoria longa",
        "crescer memoria longa",
    }:
        added = curate_recent_ui_history()
        save_operational_context()
        if added:
            return f"Memoria longa curada. Adicionei {added} item(ns) duraveis."
        return "Memoria longa revisada. Nao encontrei nada novo que merecesse virar memoria duravel."

    if normalized in {
        "limpar memoria longa",
        "deduplicar memoria longa",
        "deduplicar memorias",
        "limpar memorias vencidas",
        "limpeza da memoria longa",
    }:
        return format_clean_long_memory_report()

    remember_match = re.match(
        r"^(?:lembre|lembra|memorize|salve)\s+(?:na\s+)?(?:mem.ria longa)\s+(?:que\s+)?(.+)$",
        raw,
        flags=re.I,
    )
    if remember_match:
        added = maybe_remember_from_user_text("lembre que " + remember_match.group(1), source="manual-long-memory")
        save_operational_context()
        return "Memoria longa atualizada." if added else "Isso ja estava na memoria longa, ou ficou curto demais para salvar."

    return None
