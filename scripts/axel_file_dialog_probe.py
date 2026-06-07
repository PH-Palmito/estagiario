from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.study_commands import maybe_handle_study_command
from memory.study_context import clear_study_context, load_study_context, save_study_context


DEFAULT_QUESTIONS = [
    "oq tem na pagina 2?",
    "oq tem na pagina 3?",
    "oq tem na pagina 4?",
    "pagina 1?",
    "o arquivo fala sobre bananas?",
    "o arquivo e um slide?",
    "testar arquivo atual",
]


def ask_axel(text: str) -> str:
    response = maybe_handle_study_command(text, show_hud=lambda: "hud")
    return response or "Sem resposta pelo fluxo de estudos."


def run_dialog(path: str, questions: list[str], *, keep_context: bool = False) -> str:
    previous_context = load_study_context()
    transcript: list[str] = []
    try:
        clear_study_context()
        attach_command = f"analisar arquivos anexados: {json.dumps([path])} :: oq tem na pagina 4?"
        commands = [attach_command, *questions]
        for command in commands:
            response = ask_axel(command)
            transcript.append(f"Usuario: {command}")
            transcript.append(f"Axel: {response}")
            transcript.append("")
    finally:
        if not keep_context:
            if previous_context:
                save_study_context(previous_context)
            else:
                clear_study_context()
    return "\n".join(transcript).strip()


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="Conversa com o Axel sobre um arquivo pelo fluxo interno de estudos.")
    parser.add_argument("path", help="Arquivo a ser anexado no dialogo.")
    parser.add_argument("--keep-context", action="store_true", help="Mantem o contexto gerado pelo dialogo.")
    parser.add_argument("--question", action="append", default=[], help="Pergunta extra para fazer ao Axel.")
    args = parser.parse_args()

    path = str(Path(args.path).expanduser())
    questions = args.question or DEFAULT_QUESTIONS
    print(run_dialog(path, questions, keep_context=args.keep_context))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
