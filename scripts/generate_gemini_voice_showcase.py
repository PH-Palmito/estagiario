from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm.gemini_tts_client import synthesize_gemini_tts_to_wav


DEFAULT_TEXT = (
    "Boa tarde, chefe. Sistemas online. Carteira monitorada, clima sob controle "
    "e Axel pronto para começar."
)

# Lista empírica para teste. O Gemini valida de fato quais vozes estão disponíveis.
MASCULINE_CANDIDATES = [
    "Puck",
    "Charon",
    "Fenrir",
    "Orus",
    "Zephyr",
    "Achird",
    "Algenib",
    "Iapetus",
    "Enceladus",
    "Kore",
]


def sanitize_filename(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")


def main():
    parser = argparse.ArgumentParser(description="Gera amostras de vozes do Gemini para comparação.")
    parser.add_argument("--lang", default="pt-BR", help="Idioma em BCP-47.")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="Texto base para todas as amostras.")
    parser.add_argument(
        "--out-dir",
        default=str(ROOT / ".tmp" / "gemini_voice_showcase"),
        help="Pasta onde os WAVs serão salvos.",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    successes = []
    failures = []

    for voice_name in MASCULINE_CANDIDATES:
        output_path = out_dir / f"{sanitize_filename(voice_name)}.wav"
        try:
            synthesize_gemini_tts_to_wav(
                args.text,
                output_path,
                voice_name=voice_name,
                language_code=args.lang,
            )
            successes.append(
                {
                    "voice": voice_name,
                    "path": str(output_path),
                }
            )
            print(f"OK {voice_name} -> {output_path}")
        except Exception as exc:
            failures.append({"voice": voice_name, "error": str(exc)})
            print(f"FAIL {voice_name} -> {exc}")

    manifest = {
        "language_code": args.lang,
        "text": args.text,
        "successes": successes,
        "failures": failures,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"MANIFEST {manifest_path}")


if __name__ == "__main__":
    main()
