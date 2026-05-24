import tempfile
import unittest
from pathlib import Path

from voice.piper_utils import (
    append_piper_audio_chunk,
    load_piper_sample_rate,
    piper_cache_settings,
    piper_cli_command,
    piper_effective_worker_idle,
    piper_synthesis_plan,
    piper_tts_settings,
    piper_worker_command,
    piper_worker_payload,
    piper_worker_read_size,
    piper_worker_runtime_settings,
    piper_worker_should_stop_reading,
    piper_worker_signature,
    read_piper_worker_audio_loop,
    split_tts_text_for_piper,
    validate_piper_tts_settings,
    write_piper_worker_payload,
)


class FakeWorkerStdin:
    def __init__(self):
        self.written = b""
        self.flushed = False

    def write(self, payload: bytes):
        self.written += payload

    def flush(self):
        self.flushed = True


class FakeWorkerProcess:
    def __init__(self, poll_result=None, stdin=None, stdout=None):
        self._poll_result = poll_result
        self.stdin = stdin
        self.stdout = stdout

    def poll(self):
        return self._poll_result


class FakeClock:
    def __init__(self, values=None):
        self.values = list(values or [0.0])

    def monotonic(self):
        if len(self.values) > 1:
            return self.values.pop(0)
        return self.values[0]


class PiperUtilsTests(unittest.TestCase):
    def test_piper_tts_settings_normalizes_paths_and_numeric_values(self):
        result = piper_tts_settings(
            {
                "piper_exe_path": " ",
                "piper_model_path": " model.onnx ",
                "piper_config_path": " config.json ",
                "piper_speaker_id": " 2 ",
                "piper_length_scale": "1.15",
                "piper_noise_scale": "invalid",
                "piper_noise_w": 0.7,
            },
        )

        self.assertEqual(result.piper_exe, "piper")
        self.assertEqual(result.model_path, "model.onnx")
        self.assertEqual(result.config_path, "config.json")
        self.assertEqual(result.speaker_id, "2")
        self.assertEqual(result.length_scale, "1.15")
        self.assertEqual(result.noise_scale, "0.667")
        self.assertEqual(result.noise_w, "0.7")

    def test_validate_piper_tts_settings_reports_missing_model(self):
        settings = piper_tts_settings({})

        result = validate_piper_tts_settings(settings)

        self.assertIsNone(result.model)
        self.assertEqual(result.error, "Modelo do Piper nao configurado.")

    def test_validate_piper_tts_settings_returns_existing_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            model = Path(tmpdir) / "voice.onnx"
            config = Path(tmpdir) / "voice.json"
            model.write_bytes(b"model")
            config.write_text("{}", encoding="utf-8")
            settings = piper_tts_settings(
                {
                    "piper_model_path": str(model),
                    "piper_config_path": str(config),
                },
            )

            result = validate_piper_tts_settings(settings)

            self.assertEqual(result.model, model)
            self.assertIsNone(result.error)

    def test_validate_piper_tts_settings_reports_missing_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            model = Path(tmpdir) / "voice.onnx"
            config = Path(tmpdir) / "missing.json"
            model.write_bytes(b"model")
            settings = piper_tts_settings(
                {
                    "piper_model_path": str(model),
                    "piper_config_path": str(config),
                },
            )

            result = validate_piper_tts_settings(settings)

            self.assertIsNone(result.model)
            self.assertEqual(result.error, f"Config do Piper nao encontrado: {config}")

    def test_piper_cli_command_includes_output_and_optional_args(self):
        settings = piper_tts_settings(
            {
                "piper_exe_path": "piper.exe",
                "piper_config_path": "voice.json",
                "piper_speaker_id": "2",
                "piper_length_scale": "1.2",
                "piper_noise_scale": "0.5",
                "piper_noise_w": "0.9",
            },
        )

        result = piper_cli_command(settings, "voice.onnx", "out.wav")

        self.assertEqual(
            result,
            [
                "piper.exe",
                "--model",
                "voice.onnx",
                "--output_file",
                "out.wav",
                "--length_scale",
                "1.2",
                "--noise_scale",
                "0.5",
                "--noise_w",
                "0.9",
                "--config",
                "voice.json",
                "--speaker",
                "2",
            ],
        )

    def test_piper_worker_command_uses_raw_json_mode_without_empty_optional_args(self):
        settings = piper_tts_settings(
            {
                "piper_exe_path": "piper.exe",
                "piper_length_scale": "1.2",
                "piper_noise_scale": "0.5",
                "piper_noise_w": "0.9",
            },
        )

        result = piper_worker_command(settings, "voice.onnx")

        self.assertEqual(
            result,
            [
                "piper.exe",
                "--model",
                "voice.onnx",
                "--output_raw",
                "--json-input",
                "--quiet",
                "--length_scale",
                "1.2",
                "--noise_scale",
                "0.5",
                "--noise_w",
                "0.9",
            ],
        )

    def test_piper_worker_payload_serializes_utf8_json_line(self):
        self.assertEqual(piper_worker_payload("ol\u00e1 mundo"), b'{"text": "ol\xc3\xa1 mundo"}\n')

    def test_piper_worker_runtime_settings_clamps_numeric_values(self):
        result = piper_worker_runtime_settings(
            {
                "piper_persistent_worker_enabled": False,
                "piper_worker_fallback_to_cli": False,
                "piper_worker_timeout_seconds": 999,
                "piper_worker_idle_seconds": "invalid",
            },
        )

        self.assertFalse(result.enabled)
        self.assertFalse(result.fallback_to_cli)
        self.assertEqual(result.timeout_seconds, 60.0)
        self.assertEqual(result.idle_seconds, 0.12)

    def test_piper_worker_runtime_settings_uses_defaults(self):
        result = piper_worker_runtime_settings({})

        self.assertTrue(result.enabled)
        self.assertTrue(result.fallback_to_cli)
        self.assertEqual(result.timeout_seconds, 20.0)
        self.assertEqual(result.idle_seconds, 0.12)

    def test_piper_effective_worker_idle_waits_longer_before_worker_is_warm(self):
        self.assertEqual(piper_effective_worker_idle(0.12, worker_warm=False), 0.35)
        self.assertEqual(piper_effective_worker_idle(0.12, worker_warm=True), 0.12)
        self.assertEqual(piper_effective_worker_idle(0.5, worker_warm=False), 0.5)

    def test_piper_worker_read_size_caps_available_bytes(self):
        self.assertEqual(piper_worker_read_size(0), 0)
        self.assertEqual(piper_worker_read_size(-5), 0)
        self.assertEqual(piper_worker_read_size(128), 128)
        self.assertEqual(piper_worker_read_size(70000), 65536)

    def test_piper_worker_should_stop_reading_on_total_timeout(self):
        self.assertTrue(
            piper_worker_should_stop_reading(
                now=11.1,
                started=1.0,
                timeout_seconds=10.0,
                last_data_at=None,
                effective_idle_seconds=0.35,
            ),
        )

    def test_piper_worker_should_stop_reading_after_idle_when_data_was_seen(self):
        self.assertTrue(
            piper_worker_should_stop_reading(
                now=5.36,
                started=1.0,
                timeout_seconds=10.0,
                last_data_at=5.0,
                effective_idle_seconds=0.35,
            ),
        )
        self.assertFalse(
            piper_worker_should_stop_reading(
                now=5.34,
                started=1.0,
                timeout_seconds=10.0,
                last_data_at=5.0,
                effective_idle_seconds=0.35,
            ),
        )

    def test_piper_worker_should_stop_reading_ignores_idle_before_first_data(self):
        self.assertFalse(
            piper_worker_should_stop_reading(
                now=5.0,
                started=1.0,
                timeout_seconds=10.0,
                last_data_at=None,
                effective_idle_seconds=0.35,
            ),
        )

    def test_append_piper_audio_chunk_appends_data_and_returns_timestamp(self):
        chunks = []

        result = append_piper_audio_chunk(chunks, b"abc", now=3.5)

        self.assertEqual(chunks, [b"abc"])
        self.assertEqual(result, 3.5)

    def test_append_piper_audio_chunk_ignores_empty_data(self):
        chunks = []

        result = append_piper_audio_chunk(chunks, b"", now=3.5)

        self.assertEqual(chunks, [])
        self.assertIsNone(result)

    def test_read_piper_worker_audio_loop_collects_until_idle(self):
        process = FakeWorkerProcess(stdout=object())
        clock = FakeClock([0.0, 0.0, 0.1, 0.1, 0.2, 0.5, 0.56])
        reads = [b"abc", b"def", b""]
        sleeps = []

        result = read_piper_worker_audio_loop(
            process,
            timeout_seconds=10.0,
            idle_seconds=0.35,
            worker_warm=True,
            interrupt_pressed=lambda: False,
            stop_worker=lambda: None,
            read_stdout_chunk=lambda _stdout: reads.pop(0) if reads else b"",
            monotonic=clock.monotonic,
            sleep=sleeps.append,
        )

        self.assertIsNone(result.error)
        self.assertEqual(result.audio_bytes, b"abcdef")
        self.assertTrue(result.worker_warm)
        self.assertEqual(sleeps, [0.01])

    def test_read_piper_worker_audio_loop_reports_missing_stdout(self):
        process = FakeWorkerProcess(stdout=None)

        result = read_piper_worker_audio_loop(
            process,
            timeout_seconds=10.0,
            idle_seconds=0.35,
            worker_warm=False,
            interrupt_pressed=lambda: False,
            stop_worker=lambda: None,
            read_stdout_chunk=lambda _stdout: b"",
            monotonic=lambda: 0.0,
            sleep=lambda _seconds: None,
        )

        self.assertEqual(result.error, "Worker Piper sem stdout.")
        self.assertEqual(result.audio_bytes, b"")
        self.assertFalse(result.worker_warm)

    def test_read_piper_worker_audio_loop_stops_worker_on_interrupt(self):
        process = FakeWorkerProcess(stdout=object())
        stopped = []

        result = read_piper_worker_audio_loop(
            process,
            timeout_seconds=10.0,
            idle_seconds=0.35,
            worker_warm=False,
            interrupt_pressed=lambda: True,
            stop_worker=lambda: stopped.append(True),
            read_stdout_chunk=lambda _stdout: b"",
            monotonic=lambda: 0.0,
            sleep=lambda _seconds: None,
        )

        self.assertEqual(result.error, "Fala interrompida.")
        self.assertEqual(result.audio_bytes, b"")
        self.assertEqual(stopped, [True])

    def test_read_piper_worker_audio_loop_keeps_warm_state_without_new_audio(self):
        process = FakeWorkerProcess(poll_result=0, stdout=object())

        result = read_piper_worker_audio_loop(
            process,
            timeout_seconds=10.0,
            idle_seconds=0.35,
            worker_warm=True,
            interrupt_pressed=lambda: False,
            stop_worker=lambda: None,
            read_stdout_chunk=lambda _stdout: b"",
            monotonic=lambda: 0.0,
            sleep=lambda _seconds: None,
        )

        self.assertIsNone(result.error)
        self.assertEqual(result.audio_bytes, b"")
        self.assertTrue(result.worker_warm)

    def test_write_piper_worker_payload_writes_and_flushes_stdin(self):
        stdin = FakeWorkerStdin()
        process = FakeWorkerProcess(stdin=stdin)

        write_piper_worker_payload(process, b'{"text": "oi"}\n')

        self.assertEqual(stdin.written, b'{"text": "oi"}\n')
        self.assertTrue(stdin.flushed)

    def test_write_piper_worker_payload_rejects_dead_process(self):
        process = FakeWorkerProcess(poll_result=1, stdin=FakeWorkerStdin())

        with self.assertRaisesRegex(RuntimeError, "morreu antes da escrita"):
            write_piper_worker_payload(process, b"payload")

    def test_write_piper_worker_payload_rejects_missing_stdin(self):
        process = FakeWorkerProcess(stdin=None)

        with self.assertRaisesRegex(RuntimeError, "sem stdin"):
            write_piper_worker_payload(process, b"payload")

    def test_load_piper_sample_rate_reads_config_or_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Path(tmpdir) / "voice.json"
            config.write_text('{"audio": {"sample_rate": 24000}}', encoding="utf-8")

            self.assertEqual(load_piper_sample_rate(str(config)), 24000)
            self.assertEqual(load_piper_sample_rate(str(Path(tmpdir) / "missing.json")), 22050)

    def test_piper_worker_signature_includes_runtime_inputs(self):
        result = piper_worker_signature("piper", "model.onnx", "config.json", "1", "1.0", "0.6", "0.8")

        self.assertEqual(result, ("piper", "model.onnx", "config.json", "1", "1.0", "0.6", "0.8"))

    def test_piper_cache_settings_include_voice_effect_preferences(self):
        result = piper_cache_settings(
            "model",
            "config",
            "speaker",
            "1.0",
            "0.667",
            "0.8",
            {
                "assistant_voice_effect": " Jarvis ",
                "assistant_voice_effect_strength": 0.35,
            },
        )

        self.assertEqual(result[-2:], ["jarvis", "0.35"])

    def test_piper_synthesis_plan_uses_cache_and_keeps_single_short_text(self):
        result = piper_synthesis_plan(
            "texto curto",
            ["model", "config"],
            {"tts_cache_enabled": True},
        )

        self.assertEqual(result.text, "texto curto")
        self.assertTrue(result.cache_enabled)
        self.assertEqual(result.cache_settings, ["model", "config"])
        self.assertEqual(result.chunks, ("texto curto",))
        self.assertFalse(result.should_chunk)

    def test_piper_synthesis_plan_can_disable_cache(self):
        result = piper_synthesis_plan(
            "texto curto",
            ["model"],
            {"tts_cache_enabled": False},
        )

        self.assertFalse(result.cache_enabled)

    def test_piper_synthesis_plan_chunks_long_text_above_threshold(self):
        text = (
            "Primeira parte com conteudo suficiente para virar uma fala separada, "
            "segunda parte tambem longa o bastante para passar do limite configurado, "
            "terceira parte com mais detalhes para ultrapassar o tamanho interno de quebra, "
            "quarta parte mantendo a frase natural e ainda assim extensa."
        )

        result = piper_synthesis_plan(
            text,
            ["model"],
            {},
            chunk_threshold=80,
        )

        self.assertGreater(len(result.chunks), 1)
        self.assertTrue(result.should_chunk)

    def test_piper_synthesis_plan_does_not_chunk_short_text_below_threshold(self):
        text = "Primeira parte, segunda parte"

        result = piper_synthesis_plan(
            text,
            ["model"],
            {},
            chunk_threshold=200,
        )

        self.assertFalse(result.should_chunk)

    def test_split_tts_text_for_piper_chunks_long_text_and_keeps_tiny_prefix_with_next_part(self):
        text = "1.\n234 reais, agora com uma frase longa o bastante para precisar quebrar em partes pequenas"

        result = split_tts_text_for_piper(text, max_chars=38)

        self.assertEqual(result[0], "1. 234 reais,")
        self.assertTrue(all(len(part) <= 38 for part in result))


if __name__ == "__main__":
    unittest.main()
