from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.golden_commands import GOLDEN_COMMANDS_V1, GOLDEN_UI_COMMANDS_V2
from core.normalizer import normalize_action
from core.router import route
from core.shared_commands import maybe_handle_shared_command
from core.study_commands import maybe_handle_study_command
from core.ui_bridge import UIBridge
from core.validator import validate_command
from core.work_mode_commands import maybe_handle_work_mode_command
from memory.study_context import clear_study_context, load_study_context, save_study_context


GENERAL_QUESTIONS = [
    "quem e alanzoca?",
    "oq e tesla?",
    "me explique recursao em python",
    "qual o nome do projeto?",
    "essa pergunta e bem aleatoria, voce responde?",
]

STUDY_QUESTIONS = [
    "oq tem na pagina 2?",
    "o arquivo fala sobre bananas?",
    "o arquivo e um slide?",
    "testar arquivo atual",
]

SHARED_COMMANDS = [
    "/status",
    "/usage",
    "/insights",
    "/skills",
    "/model",
    "/model local",
    "/reset",
    "/stop",
    "/retry",
    "/undo",
    "/help",
]


def _line(title: str) -> str:
    return f"\n== {title} =="


def probe_router_contract() -> list[str]:
    lines = [_line("Comandos dourados: roteamento sem execucao")]
    passed = 0
    for item in GOLDEN_COMMANDS_V1:
        command = normalize_action(route(item["phrase"]))
        ok, error = validate_command(command)
        matches = (
            ok
            and command.action == item["expected_action"]
            and command.requires_confirmation == item["requires_confirmation"]
            and all(command.params.get(key) == value for key, value in item["expected_params"].items())
        )
        status = "OK" if matches else "FALHOU"
        if matches:
            passed += 1
        lines.append(
            f"{status} {item['id']}: '{item['phrase']}' -> {command.action} "
            f"{json.dumps(command.params, ensure_ascii=False)}"
            + ("" if ok else f" | {error}")
        )
    lines.append(f"Resumo: {passed}/{len(GOLDEN_COMMANDS_V1)} comandos passaram no contrato.")
    return lines


def _make_bridge() -> UIBridge:
    return UIBridge(
        root_dir=Path("."),
        python_executable="python.exe",
        runtime_patch=lambda: {"assistant_name": "Axel", "status": "INATIVO"},
        normalize_text=lambda text: " ".join(str(text or "").lower().split()),
        route=lambda text: {"intent": "ui_show_map", "target": {"label": "Salvador"}}
        if "mapa" in str(text).lower()
        else {"intent": "respond", "target": None},
        process_action=lambda _raw: Mock(params={"target": {"label": "Salvador"}}),
        training_snapshot=lambda: {"workout": {"label": "hoje", "title": "superior"}},
    )


def probe_ui_contract() -> list[str]:
    lines = [_line("Interface e modos: conversa simulada")]
    passed = 0
    total = 0
    with patch("core.ui_bridge.subprocess.Popen"), patch(
        "core.ui_bridge.load_ui_state", return_value={"visible": True}
    ), patch("core.ui_bridge.update_ui_state"), patch(
        "core.ui_bridge.build_project_health_snapshot", return_value={"status": "saudavel"}
    ), patch(
        "core.work_mode_commands.update_ui_state"
    ):
        bridge = _make_bridge()
        for item in GOLDEN_UI_COMMANDS_V2:
            total += 1
            if item["surface"] == "ui_bridge":
                response = bridge.maybe_handle_command(item["phrase"])
            else:
                response = maybe_handle_work_mode_command(item["phrase"], Mock())
            expected = item.get("expected_response")
            contains = item.get("expected_response_contains")
            matches = bool(
                (expected and response == expected)
                or (contains and response and contains in response)
            )
            if matches:
                passed += 1
            lines.append(f"{'OK' if matches else 'FALHOU'} {item['id']}: '{item['phrase']}' -> {response}")
    lines.append(f"Resumo: {passed}/{total} comandos de UI/modo passaram.")
    return lines


def probe_shared_commands() -> list[str]:
    lines = [_line("Comandos compartilhados: leitura segura")]
    passed = 0
    for command in SHARED_COMMANDS:
        response = maybe_handle_shared_command(command)
        ok = bool(response)
        if ok:
            passed += 1
        lines.append(f"{'OK' if ok else 'FALHOU'} Usuario: {command}\nAxel: {response or '[sem resposta]'}")
    lines.append(f"Resumo: {passed}/{len(SHARED_COMMANDS)} comandos compartilhados responderam.")
    return lines


WEAK_GENERAL_RESPONSES = {
    "Nao entendi.",
    "Não entendi.",
    "Pode repetir?",
    "Não consegui confirmar uma resposta boa agora. Posso tentar de novo com mais contexto ou usando pesquisa.",
    "Nao consegui confirmar uma resposta boa agora. Posso tentar de novo com mais contexto ou usando pesquisa.",
}


def probe_general_routing() -> list[str]:
    lines = [_line("Perguntas gerais: roteamento e resposta")]
    passed = 0
    for question in GENERAL_QUESTIONS:
        raw = route(question)
        response = str(raw.get("response") or "").strip()
        ok = raw.get("intent") == "respond" and bool(response) and response not in WEAK_GENERAL_RESPONSES
        if ok:
            passed += 1
        lines.append(
            f"{'OK' if ok else 'ATENCAO'} Usuario: {question}\n"
            f"Axel: {response or '[sem resposta textual]'}\n"
            f"Rota: intent={raw.get('intent')} target={json.dumps(raw.get('target'), ensure_ascii=False)}"
        )
    lines.append(f"Resumo: {passed}/{len(GENERAL_QUESTIONS)} perguntas gerais tiveram resposta textual util.")
    return lines


def probe_study_file(path: str) -> list[str]:
    lines = [_line("Arquivo: conversa real pelo fluxo de estudos")]
    previous_context = load_study_context()
    try:
        clear_study_context()
        attach_command = f"analisar arquivos anexados: {json.dumps([path])} :: oq tem na pagina 4?"
        for command in [attach_command, *STUDY_QUESTIONS]:
            response = maybe_handle_study_command(command, show_hud=lambda: "hud")
            lines.append(f"Usuario: {command}\nAxel: {response or 'Sem resposta pelo fluxo de estudos.'}")
    finally:
        if previous_context:
            save_study_context(previous_context)
        else:
            clear_study_context()
    return lines


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Probe seguro de conversa/contratos do Axel.")
    parser.add_argument("--file", default="", help="Arquivo para testar no fluxo de estudos.")
    args = parser.parse_args()

    output: list[str] = ["Probe seguro do Axel"]
    if args.file:
        output.extend(probe_study_file(str(Path(args.file).expanduser())))
    output.extend(probe_router_contract())
    output.extend(probe_ui_contract())
    output.extend(probe_shared_commands())
    output.extend(probe_general_routing())
    print("\n".join(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
