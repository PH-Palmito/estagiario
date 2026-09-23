from __future__ import annotations

import re
from dataclasses import dataclass

from core.router_utils import normalize_text
from core.toolsets import select_toolsets
from memory.adaptive_preferences import adaptive_rules_for_domain, get_current_adaptive_context

DECISION_KNOWN_CAPABILITY = "KNOWN_CAPABILITY"
DECISION_INFORMATION = "INFORMATION"
DECISION_PLANNING = "PLANNING"
DECISION_CLARIFICATION = "CLARIFICATION"
DECISION_UNKNOWN = "UNKNOWN"
DECISION_BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class UnknownIntentInterpretation:
    decision_type: str
    raw_action: dict
    capability: str = ""
    capability_source: str = ""
    reason: str = ""
    confidence: float = 0.45
    context_used: tuple[str, ...] = ()

    def metadata(self) -> dict:
        return {
            "decision_type": self.decision_type,
            "capability": self.capability,
            "capability_source": self.capability_source,
            "reason": self.reason,
            "confidence": self.confidence,
            "context_used": list(self.context_used),
        }


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _has_phrase_or_word(text: str, terms: tuple[str, ...]) -> bool:
    for term in terms:
        if " " in term:
            if term in text:
                return True
            continue
        if re.search(rf"\b{re.escape(term)}\b", text):
            return True
    return False


def _blocked_action(reason: str) -> dict:
    return {
        "intent": "respond",
        "target": None,
        "response": (
            "Bloqueei esse pedido: o escopo ou o risco e amplo demais para uma confirmacao simples. "
            "Se quiser uma acao segura, diga exatamente o alvo, o limite e o que deve acontecer."
        ),
        "__blocked_reason": reason,
    }


def _clarification_action(message: str) -> dict:
    return {
        "intent": "respond",
        "target": None,
        "response": message,
    }


def _best_toolset_capability(user_input: str) -> tuple[str, str]:
    matches = select_toolsets(user_input, limit=1)
    if not matches:
        return "", ""
    match = matches[0]
    capabilities = match.get("capabilities") or []
    capability = str(capabilities[0] if capabilities else match.get("title") or match.get("name") or "").strip()
    return str(match.get("name") or "").strip(), capability


def _adaptive_context_for(user_input: str) -> tuple[str, ...]:
    used: list[str] = []
    try:
        current = get_current_adaptive_context()
        label = str(current.get("label") or current.get("context") or "").strip()
        if label:
            used.append(f"contexto_adaptativo:{label}")
    except Exception:
        pass

    for domain in ("studies", "training", "briefing", "response_tone", "investments"):
        try:
            rules = adaptive_rules_for_domain(domain, text=user_input)
        except Exception:
            rules = []
        if rules:
            used.append(f"memoria_adaptativa:{domain}")
    return tuple(used[:4])


def _annotate(action: dict, interpretation: UnknownIntentInterpretation) -> dict:
    payload = dict(action)
    payload["__semantic_fallback"] = interpretation.metadata()
    payload["__decision_type"] = interpretation.decision_type
    payload["__capability"] = interpretation.capability
    payload["__capability_source"] = interpretation.capability_source
    payload["__fallback_reason"] = interpretation.reason
    payload["__confidence"] = interpretation.confidence
    return payload


def interpret_unknown_intent(user_input: str) -> UnknownIntentInterpretation:
    text = normalize_text(user_input)
    context_used = _adaptive_context_for(user_input)
    toolset, capability = _best_toolset_capability(user_input)

    if not text:
        return UnknownIntentInterpretation(
            DECISION_UNKNOWN,
            {"intent": "respond", "target": None, "response": "Nao recebi texto suficiente para interpretar."},
            reason="entrada vazia",
            confidence=0.2,
            context_used=context_used,
        )

    destructive_scope = _has_any(
        text,
        (
            "apague tudo",
            "apagar tudo",
            "apague todos",
            "apagar todos",
            "apague os arquivos",
            "delete tudo",
            "deletar tudo",
            "delete todos",
            "deletar todos",
            "delete os arquivos",
            "remova tudo",
            "remover tudo",
            "remova todos",
            "remover todos",
            "limpa tudo",
            "limpar tudo",
            "format c:",
            "formatar c:",
        ),
    )
    prompt_injection = _has_any(
        text,
        (
            "ignore suas regras",
            "ja confirmei",
            "nao precisa pedir confirmacao",
            "finja que essa acao e segura",
            "autorizacao permanente",
            "execute como administrador",
        ),
    )
    if destructive_scope:
        action = _blocked_action("pedido destrutivo amplo ou prompt injection")
        return UnknownIntentInterpretation(
            DECISION_BLOCKED,
            action,
            capability="file_delete",
            capability_source="politica_de_seguranca",
            reason="pedido destrutivo amplo bloqueado antes de virar action executavel",
            confidence=0.93,
            context_used=context_used,
        )
    if prompt_injection and _has_any(text, ("apague", "delete", "remova", "execute", "format")):
        action = _blocked_action("tentativa de contornar politica de seguranca")
        return UnknownIntentInterpretation(
            DECISION_BLOCKED,
            action,
            capability="security_policy",
            capability_source="politica_de_seguranca",
            reason="instrucao do usuario tentou substituir regras de seguranca",
            confidence=0.91,
            context_used=context_used,
        )

    organization_terms = ("organiza", "organize", "organizar", "arruma", "arrume", "arrumar", "limpa", "limpe", "limpar", "melhora", "melhore", "melhorar", "deixa")
    ambiguous_targets = (
        "area de trabalho",
        "desktop",
        "computador",
        "ambiente",
        "meus arquivos",
        "minha tela",
        "isso",
        "tudo",
    )
    if _has_phrase_or_word(text, ambiguous_targets) and _has_phrase_or_word(text, organization_terms):
        action = _clarification_action(
            "Posso ajudar, mas preciso separar o sentido: voce quer organizar janelas, arquivos, atalhos, tela visual "
            "ou fazer um plano? Diga uma dessas opcoes antes de eu agir."
        )
        return UnknownIntentInterpretation(
            DECISION_CLARIFICATION,
            action,
            capability="organizacao de ambiente",
            capability_source="fallback_semantico",
            reason="pedido de organizacao tem multiplas interpretacoes plausiveis",
            confidence=0.62,
            context_used=context_used,
        )

    if _has_any(text, ("ignore o que esta na tela", "ignore a tela", "ignora a tela")) and _has_any(text, ("estudar", "estudos", "me ajude", "me ajuda")):
        action = _clarification_action(
            "Vou ignorar a tela. Para ajudar nos estudos sem contexto visual, me diga o tema, prazo e prioridade."
        )
        return UnknownIntentInterpretation(
            DECISION_PLANNING,
            action,
            capability="planejamento assistido",
            capability_source="fallback_semantico",
            reason="usuario proibiu uso do contexto visual",
            confidence=0.72,
            context_used=context_used,
        )

    if _has_any(
        text,
        (
            "ouvir musica",
            "ouvir uma musica",
            "ouvir alguma coisa",
            "escutar alguma coisa",
            "escutar uma musica",
            "coloca alguma musica",
            "coloque alguma musica",
            "toca alguma musica",
            "toque alguma musica",
            "bota alguma musica",
            "bota uma musica",
            "comeca uma musica",
            "comece uma musica",
            "manda uma musica",
            "quero ouvir algo",
            "quero ouvir alguma coisa",
            "to afim de ouvir",
        ),
    ):
        action = {
            "intent": "browser_surprise_music",
            "target": {"service": "spotify"},
        }
        return UnknownIntentInterpretation(
            DECISION_KNOWN_CAPABILITY,
            action,
            capability="browser_surprise_music",
            capability_source="normalizer/actions",
            reason="pedido natural de musica corresponde a capability existente",
            confidence=0.82,
            context_used=context_used,
        )

    if _has_any(text, ("continua aquilo", "continuar aquilo", "continua aquele", "continuar aquele", "de ontem", "que eu estava fazendo")):
        action = {
            "intent": "respond",
            "target": None,
            "response": (
                "Consigo continuar, mas preciso de um ponto de referencia. Diga se e projeto, estudo, arquivo, conversa "
                "ou tarefa; se houver contexto salvo, eu uso esse caminho sem inventar memoria."
            ),
        }
        return UnknownIntentInterpretation(
            DECISION_CLARIFICATION,
            action,
            capability="recuperacao de contexto",
            capability_source="memoria/contexto",
            reason="pedido depende de contexto anterior insuficiente",
            confidence=0.58,
            context_used=context_used,
        )

    if _has_phrase_or_word(text, ("teletransporte", "teletransportar", "teleportar", "teleporte")):
        target = "um monitor" if "monitor" in text else "isso"
        if "spotify" in text:
            target = "o Spotify"
        elif "janela" in text:
            target = "uma janela"
        action = {
            "intent": "respond",
            "target": None,
            "response": (
                f"Ainda nao tenho capacidade para teletransportar fisicamente {target}. "
                "Se voce quis dizer mover uma janela ou abrir um aplicativo, diga isso explicitamente."
            ),
        }
        return UnknownIntentInterpretation(
            DECISION_UNKNOWN,
            action,
            capability="",
            capability_source="",
            reason="teletransporte nao corresponde a uma capacidade disponivel",
            confidence=0.42,
            context_used=context_used,
        )

    if (
        _has_any(text, ("use essa pagina", "use esta pagina", "usa essa pagina", "usa esta pagina"))
        and _has_any(text, ("estudar", "estudos", "me ajudar", "me ajuda", "me ajude"))
    ) or (_has_any(text, ("estudar usando", "estudar com", "me ajuda a estudar usando", "me ajuda a estudar com")) and _has_any(
        text,
        ("nessa pagina", "nesta pagina", "essa pagina", "esta pagina", "nessa tela", "nesta tela", "essa tela", "esta tela"),
    )):
        action = {
            "intent": "vision_answer_question",
            "target": user_input.strip(),
        }
        return UnknownIntentInterpretation(
            DECISION_KNOWN_CAPABILITY,
            action,
            capability="study_assistance_with_screen",
            capability_source="router/vision",
            reason="usuario referenciou explicitamente pagina ou tela como contexto de estudo",
            confidence=0.78,
            context_used=tuple(dict.fromkeys((*context_used, "screen"))),
        )

    if _has_any(text, ("organizar meus estudos", "organize meus estudos", "organizar melhor meus estudos", "melhorar minha rotina", "estruturar esse projeto", "estruturar o projeto", "montar um plano", "planejar", "plano de estudo")):
        action = {
            "intent": "respond",
            "target": None,
            "response": (
                "Vou tratar isso como planejamento, nao execucao. Posso montar um plano curto com objetivo, restricoes, "
                "primeiros passos e criterios de sucesso; para deixar preciso, me diga prazo e prioridade."
            ),
        }
        return UnknownIntentInterpretation(
            DECISION_PLANNING,
            action,
            capability=capability or "planejamento assistido",
            capability_source=toolset or "fallback_semantico",
            reason="pedido pede estruturacao antes de qualquer acao",
            confidence=0.74,
            context_used=context_used,
        )

    if _has_any(text, ("o que aconteceu", "aconteceu alguma coisa", "noticia", "noticias", "mercado hoje", "coisa importante no mercado", "fato relevante", "compara", "compare", "me ajuda a decidir", "o que voce acha", "pesquisa", "pesquisar", "procura", "procurar")):
        if _has_any(text, ("mercado", "ativo", "ativos", "carteira", "investimento", "investimentos", "fii", "fiis", "ticker")):
            action = {
                "intent": "investment_memory_answer",
                "target": user_input,
            }
            return UnknownIntentInterpretation(
                DECISION_INFORMATION,
                action,
                capability="investment_memory_answer",
                capability_source="normalizer/actions",
                reason="pergunta informacional de mercado usa capacidade existente de investimentos",
                confidence=0.78,
                context_used=context_used,
            )
        action = {
            "intent": "respond",
            "target": None,
            "response": (
                "Entendi como pedido informacional. Posso responder com o contexto que voce mandar ou pesquisar por fontes; "
                "nao vou transformar isso em acao de sistema sem um comando claro."
            ),
        }
        return UnknownIntentInterpretation(
            DECISION_INFORMATION,
            action,
            capability=capability or "resposta informacional",
            capability_source=toolset or "fallback_semantico",
            reason="pedido busca informacao, comparacao ou analise",
            confidence=0.66,
            context_used=context_used,
        )

    if _has_any(text, ("tem alguma coisa estranha", "computador estranho", "pc estranho", "diagnostica meu computador", "diagnostico do computador")):
        action = {
            "intent": "respond",
            "target": None,
            "response": (
                "Posso ajudar a diagnosticar, mas primeiro preciso saber o sintoma: lentidao, janela estranha, audio, rede, "
                "processo suspeito ou erro especifico? Sem isso eu nao vou executar verificacoes aleatorias no sistema."
            ),
        }
        return UnknownIntentInterpretation(
            DECISION_CLARIFICATION,
            action,
            capability="diagnostico local",
            capability_source="toolset:sistema",
            reason="diagnostico de sistema precisa de sintoma ou escopo",
            confidence=0.61,
            context_used=context_used,
        )

    action = {
        "intent": "respond",
        "target": None,
        "response": (
            "Nao tenho uma forma segura de fazer isso ainda. Posso tentar de novo se voce disser se quer informacao, "
            "planejamento, abrir algo, mexer em arquivo ou controlar o sistema."
        ),
    }
    return UnknownIntentInterpretation(
        DECISION_UNKNOWN,
        action,
        capability=capability,
        capability_source=toolset,
        reason="nenhum roteador direto ou fallback semantico confiavel",
        confidence=0.35,
        context_used=context_used,
    )


def action_from_unknown_intent(user_input: str) -> dict:
    interpretation = interpret_unknown_intent(user_input)
    return _annotate(interpretation.raw_action, interpretation)
