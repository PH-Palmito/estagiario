from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import core.router_conversation as router_conversation
from core.command_schema import Command
from core.golden_commands import GOLDEN_COMMANDS_V1, GOLDEN_UI_COMMANDS_V2
from core.normalizer import normalize_action
from core.router import iter_detectors, route, route_trace
from core.shared_commands import maybe_handle_shared_command
from core.study_commands import maybe_handle_study_command
from core.validator import validate_command
from core.voice_command_classifier import normalize_voice_command
from memory.study_context import clear_study_context, load_study_context, save_study_context


@dataclass
class AuditCase:
    category: str
    phrase: str
    expected_action: str | None = None
    expected_contains: str | None = None
    source: str = "custom"
    use_voice_normalizer: bool = False


@dataclass
class AuditResult:
    category: str
    phrase: str
    effective_phrase: str
    source: str
    pre_handler: str | None
    intent: str | None
    action: str | None
    params: dict[str, Any]
    valid: bool | None
    validation_error: str | None
    expected_action: str | None
    matched_expected: bool | None
    response_preview: str
    flags: list[str]
    trace: list[str]


def _fake_chat_response(text: str) -> str:
    normalized = text.strip().rstrip("?")
    if not normalized:
        return ""
    return f"[chat simulado] Resposta geral para: {normalized}."


def _safe_normalize(raw_action: dict[str, Any]) -> tuple[Command | None, str | None]:
    try:
        return normalize_action(raw_action), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _safe_validate(command: Command | None) -> tuple[bool | None, str | None]:
    if command is None:
        return None, "comando nao normalizado"
    try:
        return validate_command(command)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _trace_detector_names(text: str) -> list[str]:
    try:
        trace = route_trace(text)
    except Exception as exc:
        return [f"trace_error:{type(exc).__name__}"]
    if hasattr(trace, "match"):
        match = trace.match
        if not match:
            return [f"no_match:{getattr(trace, 'checked_detectors', 0)}"]
        return [f"{match.group_name}.{match.detector_name}"]
    names: list[str] = []
    for item in trace or []:
        if not isinstance(item, dict):
            continue
        detector = item.get("detector") or item.get("name")
        group = item.get("group")
        matched = item.get("matched")
        if matched:
            names.append(f"{group}.{detector}")
    return names


def _preview(text: str, limit: int = 220) -> str:
    compact = " ".join(str(text or "").split())
    return compact[:limit] + ("..." if len(compact) > limit else "")


def _pre_handle(text: str) -> tuple[str | None, str | None]:
    shared = maybe_handle_shared_command(text)
    if shared:
        return "shared", shared
    study = maybe_handle_study_command(text, show_hud=lambda: "hud")
    if study:
        return "study", study
    return None, None


def _evaluate_case(case: AuditCase, *, include_trace: bool = False) -> AuditResult:
    effective = normalize_voice_command(case.phrase) if case.use_voice_normalizer else case.phrase
    pre_handler, pre_response = _pre_handle(effective)
    flags: list[str] = []
    raw_action: dict[str, Any] | None = None
    command: Command | None = None
    validation_error: str | None = None
    valid: bool | None = None
    response_preview = _preview(pre_response or "")

    if pre_handler:
        action = f"pre:{pre_handler}"
        intent = "respond"
        params: dict[str, Any] = {}
        matched_expected = None
        if case.expected_contains and case.expected_contains.lower() not in str(pre_response).lower():
            flags.append("expected_text_missing")
        if case.expected_action and case.expected_action != action:
            flags.append("expected_action_mismatch")
    else:
        try:
            raw_action = route(effective)
        except Exception as exc:
            raw_action = {"intent": "error", "target": None, "response": f"{type(exc).__name__}: {exc}"}
            flags.append("route_exception")

        command, normalize_error = _safe_normalize(raw_action)
        if normalize_error:
            flags.append("normalize_error")
            validation_error = normalize_error
        else:
            valid, validation_error = _safe_validate(command)
            if valid is False:
                flags.append("validation_failed")

        intent = str(raw_action.get("intent") or "")
        action = command.action if command else None
        params = dict(command.params) if command else {}
        response_preview = _preview((raw_action or {}).get("response") or params.get("message") or "")

        matched_expected = None
        if case.expected_action:
            matched_expected = action == case.expected_action
            if not matched_expected:
                flags.append("expected_action_mismatch")

        if intent == "respond" and not response_preview:
            flags.append("empty_response")
        if response_preview and "NÃ" in response_preview:
            flags.append("mojibake_response")
        if action == "browser_describe_screen" and "arquivo" in effective.lower():
            flags.append("file_question_fell_to_screen")
        if action in {"browser_describe_screen", "image_analyze_screen"} and effective.lower() in {"esta ai?", "está aí?", "ta ai?", "tá aí?", "axel?"}:
            flags.append("presence_fell_to_screen")
        if action == "respond" and response_preview in {"Pode repetir?", "Nao entendi.", "NÃ£o entendi."} and len(effective) > 8:
            flags.append("low_utility_response")

    return AuditResult(
        category=case.category,
        phrase=case.phrase,
        effective_phrase=effective,
        source=case.source,
        pre_handler=pre_handler,
        intent=intent,
        action=action,
        params=params,
        valid=valid,
        validation_error=validation_error,
        expected_action=case.expected_action,
        matched_expected=matched_expected,
        response_preview=response_preview,
        flags=flags,
        trace=_trace_detector_names(effective) if include_trace else [],
    )


def _golden_cases() -> list[AuditCase]:
    cases: list[AuditCase] = []
    for item in GOLDEN_COMMANDS_V1:
        cases.append(
            AuditCase(
                category="golden_v1",
                phrase=str(item["phrase"]),
                expected_action=str(item.get("expected_action") or ""),
                source=str(item.get("id") or "golden_v1"),
            )
        )
    for item in GOLDEN_UI_COMMANDS_V2:
        cases.append(
            AuditCase(
                category="golden_ui_v2",
                phrase=str(item["phrase"]),
                expected_contains=str(item.get("expected_response_contains") or item.get("expected_response") or ""),
                source=str(item.get("id") or "golden_ui_v2"),
            )
        )
    try:
        from tests.test_golden_commands import GOLDEN_COMMANDS as TEST_GOLDEN_COMMANDS

        for phrase, action, _params in TEST_GOLDEN_COMMANDS:
            cases.append(
                AuditCase(
                    category="golden_tests",
                    phrase=str(phrase),
                    expected_action=str(action),
                    source="tests.test_golden_commands",
                )
            )
    except Exception:
        pass
    return cases


def _custom_cases(file_path: str | None) -> list[AuditCase]:
    cases = [
        AuditCase("presence", "esta ai?", expected_action="respond"),
        AuditCase("presence", "está aí?", expected_action="respond"),
        AuditCase("presence", "ta ai?", expected_action="respond"),
        AuditCase("presence", "axel?", expected_action="respond"),
        AuditCase("presence_voice", "o que esta ai", use_voice_normalizer=True),
        AuditCase("general_question", "quem é alanzoca?", expected_action="respond"),
        AuditCase("general_question", "oq é tesla?", expected_action="respond"),
        AuditCase("general_question", "me explique recursão em python", expected_action="respond"),
        AuditCase("general_question", "qual a capital do Japão?", expected_action="respond"),
        AuditCase("general_question", "o que acontece se eu fizer uma pergunta muito aleatoria?", expected_action="respond"),
        AuditCase("ambiguous", "nao", expected_action="respond"),
        AuditCase("ambiguous", "pode repetir?", expected_action="respond"),
        AuditCase("ambiguous", "faz aquilo", expected_action="respond"),
        AuditCase("screen", "o que tem na tela?", expected_action="browser_describe_screen"),
        AuditCase("screen", "resuma a tela", expected_action="browser_summarize_screen"),
        AuditCase("screen", "detalha a tela", expected_action="browser_explain_screen"),
        AuditCase("apps", "abrir spotify", expected_action="open_app"),
        AuditCase("apps", "abre o chrome", expected_action="open_app"),
        AuditCase("apps", "fecha spotify", expected_action="close_app"),
        AuditCase("media", "pausar musica", expected_action="media_play_pause"),
        AuditCase("media", "proxima musica", expected_action="media_next"),
        AuditCase("browser", "nova aba", expected_action="browser_new_tab"),
        AuditCase("browser", "pesquisar notebook no mercado livre", expected_action="browser_search_site"),
        AuditCase("memory", "listar memorias", expected_action="action_memory_list"),
        AuditCase("shared", "status", expected_action="pre:shared"),
        AuditCase("shared", "skills", expected_action="pre:shared"),
        AuditCase("shared", "modelo atual", expected_action="pre:shared"),
    ]
    if file_path:
        attach = f"analisar arquivos anexados: {json.dumps([file_path], ensure_ascii=False)} :: oq tem na pagina 4?"
        cases.extend(
            [
                AuditCase("study_attach", attach, expected_action="pre:study"),
                AuditCase("study_followup", "oq tem na pagina 2?", expected_action="pre:study"),
                AuditCase("study_followup", "pagina 3?", expected_action="pre:study"),
                AuditCase("study_followup", "o arquivo fala sobre bananas?", expected_action="pre:study"),
                AuditCase("study_followup", "o slide fala sobre frutas?", expected_action="pre:study"),
                AuditCase("study_followup", "o arquivo é um slide?", expected_action="pre:study"),
                AuditCase("study_followup", "testar arquivo atual", expected_action="pre:study"),
                AuditCase("study_repeat", attach, expected_action="pre:study"),
                AuditCase("study_repeat", attach, expected_action="pre:study"),
            ]
        )
    return cases


def _write_reports(results: list[AuditResult], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"axel_command_audit_{stamp}.json"
    md_path = output_dir / f"axel_command_audit_{stamp}.md"

    json_path.write_text(
        json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    flags = Counter(flag for result in results for flag in result.flags)
    actions = Counter(result.action or "" for result in results)
    by_category: dict[str, list[AuditResult]] = defaultdict(list)
    for result in results:
        by_category[result.category].append(result)

    lines = [
        "# Auditoria de comandos do Axel",
        "",
        f"- Casos testados: {len(results)}",
        f"- Casos com flags: {sum(1 for result in results if result.flags)}",
        f"- Ações distintas: {len(actions)}",
        "",
        "## Flags",
    ]
    if flags:
        lines.extend(f"- {name}: {count}" for name, count in flags.most_common())
    else:
        lines.append("- Nenhuma flag encontrada.")

    lines.extend(["", "## Resumo por categoria"])
    for category, items in sorted(by_category.items()):
        bad = [item for item in items if item.flags]
        lines.append(f"- {category}: {len(items)} testados, {len(bad)} com flag")

    lines.extend(["", "## Casos com alerta"])
    alerted = [result for result in results if result.flags]
    if not alerted:
        lines.append("- Nenhum.")
    else:
        for result in alerted[:120]:
            lines.append(
                f"- [{result.category}] `{result.phrase}` -> `{result.action}` "
                f"flags={','.join(result.flags)} resposta=\"{result.response_preview}\""
            )

    lines.extend(["", "## Amostra completa"])
    for result in results[:220]:
        lines.append(
            f"- [{result.category}] `{result.phrase}` -> `{result.action}` "
            f"valid={result.valid} resposta=\"{result.response_preview}\""
        )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Audita comandos do Axel sem executar ações reais.")
    parser.add_argument("--file", help="Arquivo real para testar fluxo de análise/follow-up.")
    parser.add_argument("--output-dir", default=str(ROOT / "reports"), help="Diretório dos relatórios.")
    parser.add_argument("--trace", action="store_true", help="Inclui rastreamento detalhado dos detectores.")
    args = parser.parse_args()

    router_conversation.chat_response = _fake_chat_response

    previous_context = load_study_context()
    try:
        clear_study_context()
        cases = _golden_cases() + _custom_cases(args.file)
        results = [_evaluate_case(case, include_trace=args.trace) for case in cases]
    finally:
        if previous_context:
            save_study_context(previous_context)
        else:
            clear_study_context()

    json_path, md_path = _write_reports(results, Path(args.output_dir))

    flags = Counter(flag for result in results for flag in result.flags)
    summary = {
        "tested": len(results),
        "flagged": sum(1 for result in results if result.flags),
        "flags": dict(flags.most_common()),
        "json": str(json_path),
        "markdown": str(md_path),
        "detectors": [getattr(detector, "__name__", str(detector)) for detector in iter_detectors()],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
