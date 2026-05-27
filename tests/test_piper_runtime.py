import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from voice.piper_runtime import PiperRuntimeResult, run_piper_synthesis
from voice.piper_utils import piper_tts_settings


class PiperRuntimeTests(unittest.TestCase):
    def test_run_piper_synthesis_uses_cli_when_worker_disabled(self):
        calls = []
        settings = piper_tts_settings({"piper_exe_path": "piper.exe"})

        def fake_run(command, **kwargs):
            calls.append((command, kwargs))
            return SimpleNamespace(returncode=0, stderr="", stdout="")

        with tempfile.TemporaryDirectory() as tmpdir:
            output = str(Path(tmpdir) / "out.wav")
            result = run_piper_synthesis(
                "ola",
                output,
                settings,
                Path("voice.onnx"),
                preferences={"piper_persistent_worker_enabled": False},
                interrupt_pressed=lambda: False,
                run_process=fake_run,
            )

        self.assertIsNone(result)
        self.assertEqual(calls[0][0][:4], ["piper.exe", "--model", "voice.onnx", "--output_file"])
        self.assertEqual(calls[0][1]["input"], "ola")

    def test_run_piper_synthesis_reports_cli_error(self):
        settings = piper_tts_settings({})

        result = run_piper_synthesis(
            "ola",
            "out.wav",
            settings,
            Path("voice.onnx"),
            preferences={"piper_persistent_worker_enabled": False},
            interrupt_pressed=lambda: False,
            run_process=lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stderr="erro cli", stdout=""),
        )

        self.assertEqual(result, PiperRuntimeResult(error="erro cli"))

    def test_run_piper_synthesis_reports_timeout(self):
        settings = piper_tts_settings({})

        def fake_run(*_args, **_kwargs):
            raise subprocess.TimeoutExpired(cmd="piper", timeout=30)

        result = run_piper_synthesis(
            "ola",
            "out.wav",
            settings,
            Path("voice.onnx"),
            preferences={"piper_persistent_worker_enabled": False},
            interrupt_pressed=lambda: False,
            run_process=fake_run,
        )

        self.assertEqual(result, PiperRuntimeResult(error="Tempo limite atingido ao falar com Piper."))

    def test_run_piper_synthesis_reports_worker_error_when_fallback_disabled(self):
        settings = piper_tts_settings({})

        result = run_piper_synthesis(
            "ola",
            "out.wav",
            settings,
            Path("voice.onnx"),
            preferences={
                "piper_persistent_worker_enabled": True,
                "piper_worker_fallback_to_cli": False,
            },
            interrupt_pressed=lambda: False,
            popen=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("falhou")),
        )

        self.assertEqual(result, PiperRuntimeResult(error="Worker persistente do Piper falhou: falhou"))


if __name__ == "__main__":
    unittest.main()
