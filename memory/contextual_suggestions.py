from __future__ import annotations

import re
from datetime import date, datetime


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    normalized = _normalized(text)
    return any(term in normalized for term in terms)


def agenda_contextual_suggestion(text: str, target_day: date, due_at: datetime | None = None) -> str:
    normalized = _normalized(text)
    if not normalized:
        return ""

    when = "antes"
    today = datetime.now().date()
    if target_day > today:
        days = (target_day - today).days
        if days >= 7:
            when = "uma semana antes e na vespera"
        elif days >= 2:
            when = "na vespera"

    if _contains_any(normalized, ("prova", "avaliacao", "simulado", "vestibular", "concurso", "teste")):
        if target_day <= today + date.resolution:
            target_label = "hoje" if target_day <= today else "amanha"
            return (
                f" Prova {target_label}. O cronograma entrou no modo coragem, mas ainda da para salvar o basico: "
                "quer que eu te lembre de separar material, dormir cedo e revisar so os pontos-chave?"
            )
        return f" Quer que eu adicione lembretes para estudar {when}?"

    if _contains_any(normalized, ("entrevista", "processo seletivo")):
        return " Quer que eu te lembre de revisar a vaga, separar perguntas e chegar com antecedencia?"

    if _contains_any(normalized, ("reuniao", "call", "alinhamento", "apresentacao")):
        return " Quer que eu te lembre de preparar pauta, material e pontos importantes antes?"

    if _contains_any(normalized, ("familia", "aniversario", "casamento", "festa", "almoco", "jantar", "evento")):
        return " Quer que eu adicione um lembrete para confirmar horario, presente ou deslocamento?"

    if due_at is not None:
        return " Quer que eu adicione um lembrete antes desse compromisso?"

    return ""


def agenda_follow_up_prompt(text: str) -> str:
    normalized = _normalized(text)
    if not normalized:
        return ""

    if _contains_any(normalized, ("prova", "avaliacao", "simulado", "vestibular", "concurso", "teste")):
        return " Depois me conta como foi; posso sugerir um dia de revisao da materia."

    if _contains_any(normalized, ("entrevista", "processo seletivo")):
        return " Depois me conta como foi; posso te ajudar a registrar aprendizados e proximos passos."

    if _contains_any(normalized, ("reuniao", "call", "alinhamento", "apresentacao")):
        return " Depois posso te ajudar a transformar os pontos da conversa em tarefas."

    if _contains_any(normalized, ("familia", "aniversario", "casamento", "festa", "almoco", "jantar", "evento")):
        return " Depois posso salvar detalhes importantes para os proximos encontros."

    return ""


def place_dislike_memory_prompt(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""

    match = re.search(
        r"\bfui\s+(?:a|ao|a\s+o|na|no|em|num|numa)\s+(.+?)\s+e\s+(?:nao|n)\s+gostei\b",
        raw,
        flags=re.I,
    )
    if not match:
        return ""

    place = match.group(1).strip(" .,:;-")
    if not place:
        return ""
    return f"Entendi. Quer que eu salve na memoria que voce nao gostou de {place}?"


def exam_result_prompt(text: str) -> str:
    normalized = _normalized(text)
    if not normalized:
        return ""

    took_exam = re.search(r"\b(?:fiz|tive)\s+(?:uma\s+)?(?:prova|avaliacao|teste|simulado)\b", normalized)
    bad_result = _contains_any(
        normalized,
        ("fui mal", "foi mal", "me dei mal", "ruim", "horrivel", "péssimo", "pessimo"),
    )
    if not took_exam or not bad_result:
        return ""

    return (
        "Poxa. Quer que eu marque uma revisao curta dessa materia para entender onde pegou "
        "e evitar que essa prova vire misterio historico?"
    )
