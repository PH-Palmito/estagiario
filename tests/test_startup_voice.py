import unittest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from core.startup_voice import (
    common_tts_cache_phrases,
    startup_greeting_message,
    warm_common_tts_cache_async,
)
from memory.assistant_phrases import (
    contextual_startup_phrase,
    generate_and_save_startup_phrases,
    load_learned_startup_phrases,
    save_learned_startup_phrases,
)


class StartupVoiceTests(unittest.TestCase):
    def test_uses_configured_greeting_when_variants_disabled(self):
        result = startup_greeting_message(
            argv=["main.py"],
            voice_preferences={
                "startup_voice_greeting": "Pronto.",
                "startup_voice_greeting_variants_enabled": False,
            },
            greeting_variants={"study_code": ("fallback",)},
            contextual_startup_phrase=lambda *_args, **_kwargs: "",
            next_phrase=lambda *_args, **_kwargs: "fallback",
        )

        self.assertEqual(result, "Pronto.")

    def test_compact_interactive_startup_uses_short_ready_context(self):
        calls = []

        result = startup_greeting_message(
            argv=["main.py", "--voice", "--ui"],
            voice_preferences={"assistant_address_user": "chefe"},
            greeting_variants={"short_ready": ("short",), "study_code": ("study",)},
            contextual_startup_phrase=lambda category, **kwargs: calls.append((category, kwargs)) or "contextual",
            next_phrase=lambda *_args, **_kwargs: "fallback",
            now=datetime(2026, 5, 18, 14, 0),
        )

        self.assertEqual(result, "contextual")
        self.assertEqual(calls[0][0], "short_ready")
        self.assertEqual(calls[0][1]["greeting"], "Boa tarde")

    def test_computer_startup_context_stays_operational_without_nudge(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("memory.assistant_phrases.PHRASE_STATE_PATH", Path(tmpdir) / "phrases.json"):
                result = contextual_startup_phrase(
                    "computer_startup",
                    address_user="senhor",
                    greeting="Bom dia",
                )

        self.assertNotIn("próximo avanço", result.lower())
        self.assertNotIn("progresso concreto", result.lower())
        self.assertNotIn("tarefa pequena", result.lower())

    def test_computer_startup_context_avoids_generic_system_phrases(self):
        blocked = (
            "sistema est",
            "rotinas operacionais",
            "pronto para comandos",
            "pronto para consultas",
            "monitoramento de agenda",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("memory.assistant_phrases.PHRASE_STATE_PATH", Path(tmpdir) / "phrases.json"):
                results = [
                    contextual_startup_phrase("computer_startup", address_user="senhor", greeting="Bom dia")
                    for _ in range(8)
                ]

        joined = " ".join(results).lower()
        for marker in blocked:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, joined)
        self.assertGreaterEqual(len(set(results)), 6)

    def test_startup_context_can_use_learned_phrases(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("memory.assistant_phrases.PHRASE_STATE_PATH", Path(tmpdir) / "phrases.json"),
                patch("memory.assistant_phrases.STARTUP_PHRASES_PATH", Path(tmpdir) / "startup_phrases.json"),
                patch("memory.assistant_phrases.random.choice", side_effect=lambda items: items[0]),
            ):
                accepted = save_learned_startup_phrases(
                    "computer_startup",
                    ["A casa acendeu por dentro.", "Sistema estavel e pronto para comandos.", "Estou."],
                    source="unit",
                )
                result = contextual_startup_phrase("computer_startup", address_user="senhor", greeting="Bom dia")

        self.assertEqual(accepted, ["A casa acendeu por dentro."])
        self.assertEqual(result, "A casa acendeu por dentro.")
        self.assertNotIn("Sistema estavel", result)

    def test_generate_and_save_startup_phrases_filters_model_output(self):
        raw = """
        - A mesa ja esta posta.
        - Sistema pronto para comandos.
        - Aqui estou.
        - Pronto para o que.
        - Vamos pelo detalhe que destrava.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("memory.assistant_phrases.STARTUP_PHRASES_PATH", Path(tmpdir) / "startup_phrases.json"):
                accepted = generate_and_save_startup_phrases(
                    "computer_startup",
                    ask_model_fn=lambda *_args, **_kwargs: raw,
                )
                learned = load_learned_startup_phrases("computer_startup")

        self.assertEqual(accepted, ["A mesa já está posta.", "Vamos pelo detalhe que destrava."])
        self.assertEqual(learned, tuple(accepted))

    def test_night_sleep_phrases_avoid_cutoff_style(self):
        raw = """
        - Já está tarde. Salva o progresso antes de dormir.
        - A noite chegou, que tal salvar e.
        - Que tal guardar o trabalho e ter uma boa.
        - Salva o progresso antes de encerrar por hoje.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("memory.assistant_phrases.STARTUP_PHRASES_PATH", Path(tmpdir) / "startup_phrases.json"):
                accepted = generate_and_save_startup_phrases(
                    "night_sleep_prompt",
                    ask_model_fn=lambda *_args, **_kwargs: raw,
                )

        self.assertEqual(accepted, ["Salva o progresso antes de encerrar por hoje."])

    def test_falls_back_to_next_phrase_when_contextual_is_empty(self):
        result = startup_greeting_message(
            argv=["main.py"],
            voice_preferences={
                "startup_voice_greeting_category": "unknown",
                "startup_voice_autonomous_variation_enabled": False,
            },
            greeting_variants={"study_code": ("study",)},
            contextual_startup_phrase=lambda *_args, **_kwargs: "",
            next_phrase=lambda key, options, default="": f"{key}:{options[0]}",
        )

        self.assertEqual(result, "startup_greeting_study_code:study")

    def test_common_tts_cache_phrases_are_styled_and_deduplicated(self):
        result = common_tts_cache_phrases(
            voice_preferences={"startup_voice_greeting": "Pode falar."},
            style_response=lambda text: text.upper(),
        )

        self.assertEqual(result.count("PODE FALAR."), 1)
        self.assertIn("ENCERRANDO.", result)

    def test_warm_cache_starts_thread_only_for_enabled_piper(self):
        started = []

        class FakeThread:
            def __init__(self, target, daemon):
                self.target = target
                self.daemon = daemon

            def start(self):
                started.append(self.daemon)
                self.target()

        warmed = warm_common_tts_cache_async(
            voice_preferences={
                "tts_engine": "piper",
                "tts_cache_enabled": True,
                "tts_warm_cache_on_startup": True,
            },
            common_tts_cache_phrases=lambda: ["oi"],
            prime_piper_cache=lambda phrases: started.append(phrases),
            thread_factory=FakeThread,
        )

        self.assertTrue(warmed)
        self.assertEqual(started, [True, ["oi"]])

    def test_warm_cache_skips_non_piper(self):
        warmed = warm_common_tts_cache_async(
            voice_preferences={"tts_engine": "system"},
            common_tts_cache_phrases=lambda: ["oi"],
            prime_piper_cache=lambda phrases: None,
        )

        self.assertFalse(warmed)


if __name__ == "__main__":
    unittest.main()
