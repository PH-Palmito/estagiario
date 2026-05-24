from __future__ import annotations

import argparse
import sys
import winsound
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm.gemini_tts_client import synthesize_gemini_tts_to_wav


def main():
    parser = argparse.ArgumentParser(description="Testa TTS do Gemini e salva um WAV local.")
    parser.add_argument("--text", default="Bom dia. Axel online e pronto para começar.", help="Texto a ser falado.")
    parser.add_argument("--voice", default="Kore", help="Nome da voz prebuilt do Gemini.")
    parser.add_argument("--lang", default="pt-BR", help="Idioma em BCP-47.")
    parser.add_argument("--out", default=str(ROOT / ".tmp" / "gemini_tts_test.wav"), help="Caminho do WAV de saída.")
    parser.add_argument("--play", action="store_true", help="Toca o WAV ao final.")
    args = parser.parse_args()

    output_path = synthesize_gemini_tts_to_wav(
        args.text,
        args.out,
        voice_name=args.voice,
        language_code=args.lang,
    )
    print(output_path)

    if args.play:
        winsound.PlaySound(str(output_path), winsound.SND_FILENAME)


if __name__ == "__main__":
    main()
