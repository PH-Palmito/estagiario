from __future__ import annotations

from collections.abc import Callable


RouteFunc = Callable[[str], dict]
SharedFunc = Callable[[str], str | None]


ROUTE_SMOKE_CASES = (
    {
        "name": "presenca",
        "phrase": "axel esta ai?",
        "expected_intent": "respond",
        "response_contains": "Estou aqui",
    },
    {
        "name": "pergunta geral",
        "phrase": "oq e tesla?",
        "expected_intent": "respond",
        "blocked_intents": {"browser_describe_screen", "investment_memory_answer"},
    },
    {
        "name": "aprendizado util",
        "phrase": "me ajuda a estudar redes",
        "expected_intent": "respond",
        "response_contains": "perguntas de fixação",
        "blocked_intents": {"browser_describe_screen", "investment_memory_answer"},
    },
    {
        "name": "presente cotidiano",
        "phrase": "me da uma ideia de presente para minha mãe",
        "expected_intent": "respond",
        "response_contains": "sinal de cuidado",
        "blocked_intents": {"browser_describe_screen", "investment_memory_answer", "open_url", "open_app"},
    },
    {
        "name": "treino cotidiano",
        "phrase": "dicas de treino sem equipamento",
        "expected_intent": "respond",
        "response_contains": "sem equipamento",
        "blocked_intents": {"browser_describe_screen", "investment_memory_answer", "open_url", "open_app"},
    },
    {
        "name": "alimentacao cotidiana",
        "phrase": "quero comer melhor sem fazer dieta",
        "expected_intent": "respond",
        "response_contains": "sem chamar isso de dieta",
        "blocked_intents": {"browser_describe_screen", "investment_memory_answer", "open_url", "open_app"},
    },
    {
        "name": "followup exemplos",
        "phrase": "me da exemplos",
        "expected_intent": "respond",
        "blocked_intents": {"browser_describe_screen", "investment_memory_answer", "open_url", "open_app"},
    },
    {
        "name": "ingles significado",
        "phrase": "I'm doing well significa o que?",
        "expected_intent": "respond",
        "response_contains": "Estou bem",
        "blocked_intents": {"browser_describe_screen", "investment_memory_answer"},
    },
    {
        "name": "leitura de tela explicita",
        "phrase": "o que tem na tela?",
        "expected_intent": "browser_describe_screen",
    },
    {
        "name": "investimento com ticker",
        "phrase": "como o el nino afeta o VGIA11?",
        "expected_intent": "investment_memory_answer",
    },
    {
        "name": "briefing",
        "phrase": "briefing",
        "expected_intent": "daily_briefing",
    },
    {
        "name": "lembrete natural",
        "phrase": "me lembre todo dia 2 de junho do presente do dia dos namorados dia 12/06",
        "expected_intent": "reminder_add",
    },
    {
        "name": "arquivo anexado",
        "phrase": 'analisar arquivos anexados: ["C:/fake/RedesBasico.pdf"] :: oq tem na pagina 2?',
        "expected_intent": "study.analyze_files",
    },
    {
        "name": "musica com conversa",
        "phrase": "toca rock e depois me da uma dica de treino",
        "expected_intent": "browser_music_session",
    },
    {
        "name": "site com conversa",
        "phrase": "abre youtube e depois me explica redes",
        "expected_intent": "open_url",
    },
    {
        "name": "conversa antes da musica",
        "phrase": "me explica redes e toca musica para estudar",
        "expected_intent": "browser_music_session",
    },
    {
        "name": "conversa antes do lembrete",
        "phrase": "me explica redes e depois me lembre de revisar redes amanha",
        "expected_intent": "reminder_add",
    },
    {
        "name": "conversa antes da pesquisa",
        "phrase": "me explica redes e pesquise tcp no youtube",
        "expected_intent": "browser_search_site",
    },
)

SHARED_SMOKE_CASES = (
    {
        "name": "status compartilhado",
        "phrase": "/status",
        "response_contains": "Status do Axel",
    },
    {
        "name": "personalidade compartilhada",
        "phrase": "personalidade",
        "response_contains": "Personalidade do Axel",
    },
    {
        "name": "modelo compartilhado",
        "phrase": "/model",
        "response_contains": "Modelo do Axel",
    },
    {
        "name": "skills compartilhadas",
        "phrase": "/skills",
        "response_contains": "Skills",
    },
    {
        "name": "auditoria de capacidades",
        "phrase": "capacidades reais do axel",
        "response_contains": "Regra prática",
    },
    {
        "name": "uso compartilhado",
        "phrase": "/usage",
        "response_contains": "Lat",
    },
    {
        "name": "ajuda compartilhada",
        "phrase": "/help",
        "response_contains": "Comandos comuns",
    },
)


def _route_func() -> RouteFunc:
    from core.router import route

    return route


def _shared_func() -> SharedFunc:
    from core.shared_commands import maybe_handle_shared_command

    return maybe_handle_shared_command


def _check_route_case(case: dict, route_func: RouteFunc) -> tuple[bool, str]:
    phrase = str(case.get("phrase") or "")
    result = route_func(phrase) or {}
    intent = str(result.get("intent") or "")
    expected = str(case.get("expected_intent") or "")
    name = str(case.get("name") or phrase)

    if expected and intent != expected:
        return False, f"{name}: esperava {expected}, veio {intent or 'sem intent'}"

    blocked = set(case.get("blocked_intents") or set())
    if intent in blocked:
        return False, f"{name}: caiu em rota bloqueada {intent}"

    response_contains = str(case.get("response_contains") or "")
    if response_contains:
        response = str(result.get("response") or "")
        if response_contains not in response:
            return False, f"{name}: resposta inesperada"

    return True, f"{name}: {intent}"


def _check_shared_case(case: dict, shared_func: SharedFunc) -> tuple[bool, str]:
    phrase = str(case.get("phrase") or "")
    response = str(shared_func(phrase) or "")
    expected = str(case.get("response_contains") or "")
    name = str(case.get("name") or phrase)
    if expected and expected not in response:
        return False, f"{name}: resposta compartilhada inesperada"
    return True, f"{name}: ok"


def run_axel_self_check(route_func: RouteFunc | None = None, shared_func: SharedFunc | None = None) -> str:
    route_callable = route_func or _route_func()
    shared_callable = shared_func or _shared_func()
    checks = [_check_route_case(case, route_callable) for case in ROUTE_SMOKE_CASES]
    checks.extend(_check_shared_case(case, shared_callable) for case in SHARED_SMOKE_CASES)
    passed = [detail for ok, detail in checks if ok]
    failed = [detail for ok, detail in checks if not ok]
    total = len(checks)

    if not failed:
        return (
            f"Autoteste rápido do Axel: {len(passed)}/{total} rotas essenciais OK. "
            "Presença, pergunta geral, aprendizado, conselho cotidiano, inglês, tela, investimentos, briefing, lembretes, arquivos, comandos misturados, comandos compartilhados, auditoria de capacidades e personalidade estão no trilho."
        )

    return (
        f"Autoteste rápido do Axel: {len(passed)}/{total} rotas essenciais OK. "
        "Atenção em: " + "; ".join(failed[:3]) + "."
    )
