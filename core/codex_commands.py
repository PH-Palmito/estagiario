from __future__ import annotations

from core.router_utils import normalize_text
from memory.codex_bridge import load_codex_request, save_codex_request
from memory.codex_channel import load_codex_channel, save_codex_channel
from memory.codex_implementation_request import (
    load_codex_implementation_request,
    save_codex_implementation_request,
)
from memory.codex_inbox import add_codex_inbox_item, clear_codex_inbox, load_codex_inbox
from memory.codex_notifications import consume_codex_suggestion, reset_codex_suggestion_memory
from memory.codex_outbox import (
    clear_codex_outbox_pending,
    enqueue_codex_implementation_request,
    enqueue_current_codex_message,
    load_codex_outbox,
    mark_next_codex_message_sent,
)
from memory.handoff_applications import mark_handoff_applied, mark_handoff_failed, mark_handoff_started


def _extract_tail(user_input: str, prefixes: tuple[str, ...]) -> str:
    raw = str(user_input or "").strip()
    raw_lower = raw.lower()
    for prefix in prefixes:
        lowered = prefix.lower()
        if raw_lower.startswith(lowered):
            return raw[len(prefix) :].strip(" :.-")
    return ""


def maybe_handle_codex_implementation_request_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "preparar pedido de implementacao",
        "gerar pedido de implementacao",
        "pedido de implementacao ao codex",
        "mensagem de implementacao ao codex",
        "mensagem para codex implementar",
    }:
        payload = save_codex_implementation_request()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        if status == "blocked":
            return "Ainda nao ha handoff pronto para transformar em pedido de implementacao ao Codex."
        mark_handoff_started("pedido de implementacao preparado para o Codex")
        return f"Preparei o pedido de implementacao para o Codex: {title}. Deixei em memory/codex_implementation_request.md."

    if normalized in {
        "mostrar pedido de implementacao",
        "mostrar mensagem para codex",
        "pedido para codex implementar",
    }:
        payload = load_codex_implementation_request()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        files = payload.get("files") or []
        if status == "blocked":
            return "O pedido de implementacao ainda esta bloqueado. Primeiro gere um handoff pronto."
        files_text = ", ".join(str(file) for file in files[:4])
        return f"Pedido pronto para Codex: {title}. Arquivos alvo: {files_text}."

    if normalized in {
        "enviar pedido de implementacao",
        "enviar pedido de implementacao ao codex",
        "colocar pedido de implementacao na fila",
        "colocar pedido na fila do codex",
        "mandar pedido para o codex",
        "enviar nova tentativa ao codex",
        "mandar nova tentativa para o codex",
    }:
        payload = save_codex_implementation_request()
        if payload.get("status") == "blocked":
            return "Ainda nao ha pedido de implementacao pronto para colocar na fila do Codex."
        outbox = enqueue_codex_implementation_request()
        mark_handoff_started("pedido de implementacao colocado na fila do Codex")
        pending = len(outbox.get("pending", []))
        title = str(payload.get("title", "")).strip()
        return f"Pedido colocado na fila do Codex: {title}. Pendentes agora: {pending}."

    return None


def maybe_handle_codex_channel_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "pedir melhoria ao codex",
        "gerar pedido ao codex",
        "axel falar com codex",
        "axel pedir ao codex",
        "consultar codex para melhorar",
        "preparar conversa com codex",
    }:
        payload = save_codex_request()
        channel = save_codex_channel()
        title = str(payload.get("title", "")).strip()
        status = str(channel.get("status", "")).strip()
        if title:
            return f"Preparei um pedido ao Codex. Foco atual: {title}. Canal atual: {status or 'draft'}."
        return "Preparei um pedido ao Codex."

    if normalized in {
        "mostrar pedido ao codex",
        "qual o pedido ao codex",
        "pedido ao codex",
    }:
        payload = load_codex_request()
        prompt = str(payload.get("prompt", "")).strip()
        if prompt:
            return f"Pedido ao Codex: {prompt}"
        return "Ainda nao ha um pedido ao Codex pronto."

    if normalized in {
        "conversa com codex",
        "mostrar conversa com codex",
        "canal com codex",
        "status do canal com codex",
    }:
        channel = load_codex_channel()
        title = str(channel.get("title", "")).strip()
        status = str(channel.get("status", "")).strip()
        urgency = str(channel.get("urgency", "")).strip()
        next_action = str(channel.get("next_action", "")).strip()
        if not title:
            return "O canal do Axel com o Codex ainda nao tem mensagem pronta."
        return f"Canal com o Codex: {title}. Estado: {status}. Urgencia: {urgency}. Proxima acao: {next_action}."

    if normalized in {
        "sugestao do codex",
        "axel acha que deve chamar codex",
        "vale chamar codex",
        "devo chamar codex",
    }:
        suggestion = consume_codex_suggestion()
        if suggestion:
            return suggestion
        channel = load_codex_channel()
        reason = str(channel.get("notify_reason", "")).strip()
        if reason:
            return f"Ainda nao e o melhor momento para acionar o Codex. Motivo atual: {reason}."
        return "Ainda nao ha recomendacao forte para acionar o Codex."

    if normalized in {
        "atualizar conversa com codex",
        "atualizar canal com codex",
        "sincronizar conversa com codex",
    }:
        channel = save_codex_channel()
        title = str(channel.get("title", "")).strip()
        trigger = str(channel.get("trigger", "")).strip()
        return f"Atualizei o canal com o Codex. Foco: {title}. Gatilho atual: {trigger}."

    if normalized in {
        "limpar sugestao do codex",
        "resetar sugestao do codex",
    }:
        reset_codex_suggestion_memory()
        return "Limpei a memoria da sugestao do Codex. O Axel pode avisar de novo no proximo ciclo forte."

    return None


def maybe_handle_codex_outbox_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "fila do codex",
        "mensagens para o codex",
        "caixa de saida do codex",
        "outbox do codex",
    }:
        outbox = load_codex_outbox()
        pending = outbox.get("pending") or []
        sent = outbox.get("sent") or []
        if not pending and not sent:
            return "A fila do Codex ainda esta vazia."
        parts = [f"Fila do Codex: {len(pending)} pendente(s) e {len(sent)} entregue(s)."]
        if pending:
            first = pending[0] if isinstance(pending[0], dict) else {}
            title = str(first.get("title", "")).strip()
            if title:
                parts.append(f"Proxima mensagem: {title}.")
        return " ".join(parts)

    if normalized in {
        "enfileirar mensagem ao codex",
        "preparar envio ao codex",
        "colocar mensagem na fila do codex",
    }:
        outbox = enqueue_current_codex_message()
        pending = outbox.get("pending") or []
        if not pending:
            return "Nao encontrei mensagem atual forte o suficiente para enfileirar ao Codex."
        first = pending[-1] if isinstance(pending[-1], dict) else {}
        title = str(first.get("title", "")).strip()
        return f"Coloquei uma mensagem na fila do Codex. Alvo atual: {title or 'melhoria sem titulo'}."

    if normalized in {
        "marcar mensagem ao codex como enviada",
        "mensagem enviada ao codex",
        "entreguei ao codex",
    }:
        before = load_codex_outbox()
        if not (before.get("pending") or []):
            return "Nao ha mensagem pendente para marcar como enviada ao Codex."
        outbox = mark_next_codex_message_sent()
        pending = len(outbox.get("pending") or [])
        latest_sent = (outbox.get("sent") or [])[-1] if outbox.get("sent") else {}
        if isinstance(latest_sent, dict) and str(latest_sent.get("kind", "")).strip() == "implementation_request":
            mark_handoff_started("pedido de implementacao entregue ao Codex")
            return f"Registrei a entrega do pedido de implementacao ao Codex. Restam {pending} pendente(s)."
        return f"Registrei a entrega da mensagem ao Codex. Restam {pending} pendente(s)."

    if normalized in {
        "limpar fila do codex",
        "zerar fila do codex",
    }:
        clear_codex_outbox_pending()
        return "Limpei as mensagens pendentes da fila do Codex."

    return None


def maybe_handle_codex_inbox_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "inbox do codex",
        "entrada do codex",
        "respostas do codex",
        "caixa de entrada do codex",
    }:
        inbox = load_codex_inbox()
        items = inbox.get("items") or []
        if not items:
            return "A caixa de entrada do Codex ainda esta vazia."
        latest = items[-1] if isinstance(items[-1], dict) else {}
        kind = str(latest.get("kind", "")).strip()
        text = str(latest.get("text", "")).strip()
        return f"Inbox do Codex: {len(items)} resposta(s) registrada(s). Ultimo tipo: {kind or 'reply'}. Conteudo: {text or 'sem texto'}."

    codex_reply = _extract_tail(user_input, ("codex respondeu", "resposta do codex", "registrar resposta do codex"))
    if codex_reply:
        add_codex_inbox_item("reply", codex_reply)
        return "Registrei a resposta do Codex na caixa de entrada do Axel."

    codex_decision = _extract_tail(user_input, ("decisao do codex", "decisao do codex", "codex decidiu"))
    if codex_decision:
        add_codex_inbox_item("decision", codex_decision)
        return "Registrei a decisao do Codex para o Axel."

    codex_next_step = _extract_tail(
        user_input,
        (
            "proximo passo do codex",
            "proximo passo do codex",
            "codex sugeriu o proximo passo",
            "codex sugeriu o proximo passo",
        ),
    )
    if codex_next_step:
        add_codex_inbox_item("next_step", codex_next_step)
        return "Registrei o proximo passo sugerido pelo Codex."

    codex_applied = _extract_tail(
        user_input,
        (
            "codex aplicou",
            "codex implementou",
            "codex concluiu",
            "codex terminou",
            "resultado do codex",
        ),
    )
    if codex_applied:
        add_codex_inbox_item("implementation_applied", codex_applied)
        state = mark_handoff_applied(codex_applied)
        title = str((state.get("handoff") or {}).get("title", "")).strip()
        if title:
            return f"Registrei que o Codex aplicou o handoff: {title}. Agora falta validar no uso real."
        return "Registrei que o Codex aplicou uma implementacao."

    codex_failed = _extract_tail(
        user_input,
        (
            "codex falhou",
            "codex nao conseguiu",
            "falha do codex",
            "erro do codex",
        ),
    )
    if codex_failed:
        add_codex_inbox_item("implementation_failed", codex_failed)
        state = mark_handoff_failed(codex_failed)
        title = str((state.get("handoff") or {}).get("title", "")).strip()
        if title:
            return f"Registrei falha do Codex no handoff: {title}. Isso entra na proxima tentativa."
        return "Registrei uma falha de implementacao do Codex."

    if normalized in {
        "limpar inbox do codex",
        "limpar caixa de entrada do codex",
        "zerar inbox do codex",
    }:
        clear_codex_inbox()
        return "Limpei a caixa de entrada do Codex."

    return None
