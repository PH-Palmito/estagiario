import base64
import subprocess
import unittest

from voice.windows_tts import (
    INTERRUPTED_WINDOWS_TTS_ERROR,
    WINDOWS_TTS_TIMEOUT_ERROR,
    build_windows_tts_script,
    clamp_int,
    encode_powershell_script,
    monitor_windows_tts_process,
    windows_tts_command,
    windows_tts_error,
    windows_tts_plan,
)


class FakeWindowsTtsProcess:
    def __init__(self, poll_results=None, stdout="ok", stderr="", returncode=0, wait_raises=False):
        self.poll_results = list(poll_results or [0])
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.args = ["powershell"]
        self.terminated = False
        self.killed = False
        self.wait_raises = wait_raises

    def poll(self):
        if len(self.poll_results) > 1:
            return self.poll_results.pop(0)
        return self.poll_results[0]

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        if self.wait_raises:
            raise subprocess.TimeoutExpired(self.args, timeout)
        return self.returncode

    def kill(self):
        self.killed = True

    def communicate(self):
        return self.stdout, self.stderr


class WindowsTtsTests(unittest.TestCase):
    def test_clamp_int_handles_invalid_and_bounds(self):
        self.assertEqual(clamp_int("bad", -10, 10, 0), 0)
        self.assertEqual(clamp_int(-50, -10, 10, 0), -10)
        self.assertEqual(clamp_int(50, -10, 10, 0), 10)

    def test_build_windows_tts_script_escapes_text_and_voice_name(self):
        script = build_windows_tts_script(
            "olha o d'agua",
            selected_culture="pt-BR",
            preferred_voice_name='Voz "Teste"',
            tts_rate=1,
            tts_volume=80,
        )

        self.assertIn("$voice.Rate = 1", script)
        self.assertIn("$voice.Volume = 80", script)
        self.assertIn("$voice.Speak('olha o d''agua')", script)
        self.assertIn('$preferredVoiceName = "Voz `"Teste`""', script)
        self.assertIn('Culture.Name -eq "pt-BR"', script)

    def test_encode_powershell_script_uses_utf16le_base64(self):
        encoded = encode_powershell_script("abc")

        self.assertEqual(base64.b64decode(encoded), "abc".encode("utf-16le"))

    def test_windows_tts_command_builds_encoded_command(self):
        self.assertEqual(
            windows_tts_command("powershell", "abc"),
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                "abc",
            ],
        )

    def test_windows_tts_error_reports_process_and_script_errors(self):
        failed = subprocess.CompletedProcess(["powershell"], 1, stdout="", stderr="boom")
        script_error = subprocess.CompletedProcess(["powershell"], 0, stdout="__ERROR__:voz indisponivel", stderr="")
        ok = subprocess.CompletedProcess(["powershell"], 0, stdout="__OK__", stderr="")

        self.assertEqual(windows_tts_error(failed), "boom")
        self.assertEqual(windows_tts_error(script_error), "voz indisponivel")
        self.assertIsNone(windows_tts_error(ok))

    def test_windows_tts_plan_collects_preferences_and_command(self):
        result = windows_tts_plan(
            "ola",
            None,
            {
                "tts_voice_culture": "pt-BR",
                "tts_voice_name": " Maria ",
                "tts_rate": "2",
                "tts_volume": "85",
            },
            "powershell",
        )

        self.assertEqual(result.text, "ola")
        self.assertEqual(result.selected_culture, "pt-BR")
        self.assertEqual(result.preferred_voice_name, "Maria")
        self.assertEqual(result.tts_rate, 2)
        self.assertEqual(result.tts_volume, 85)
        self.assertEqual(result.command[0], "powershell")
        self.assertEqual(result.command[-2], "-EncodedCommand")
        self.assertTrue(result.command[-1])

    def test_windows_tts_plan_prefers_explicit_culture(self):
        result = windows_tts_plan(
            "ola",
            "en-US",
            {"tts_voice_culture": "pt-BR"},
            "powershell",
        )

        self.assertEqual(result.selected_culture, "en-US")

    def test_monitor_windows_tts_process_returns_completed_process(self):
        process = FakeWindowsTtsProcess(poll_results=[None, 0], stdout="__OK__", returncode=0)
        times = iter([0.0, 0.01])

        result = monitor_windows_tts_process(
            process,
            interrupt_pressed=lambda: False,
            monotonic=lambda: next(times),
            sleep=lambda _seconds: None,
        )

        self.assertIsNone(result.error)
        self.assertEqual(result.completed.stdout, "__OK__")

    def test_monitor_windows_tts_process_terminates_on_interrupt(self):
        process = FakeWindowsTtsProcess(poll_results=[None], wait_raises=True)

        result = monitor_windows_tts_process(
            process,
            interrupt_pressed=lambda: True,
            monotonic=lambda: 0.0,
            sleep=lambda _seconds: None,
        )

        self.assertEqual(result.error, INTERRUPTED_WINDOWS_TTS_ERROR)
        self.assertTrue(process.terminated)
        self.assertTrue(process.killed)

    def test_monitor_windows_tts_process_kills_on_timeout(self):
        process = FakeWindowsTtsProcess(poll_results=[None])
        times = iter([0.0, 21.0])

        result = monitor_windows_tts_process(
            process,
            interrupt_pressed=lambda: False,
            monotonic=lambda: next(times),
            sleep=lambda _seconds: None,
            timeout_seconds=20.0,
        )

        self.assertEqual(result.error, WINDOWS_TTS_TIMEOUT_ERROR)
        self.assertTrue(process.killed)


if __name__ == "__main__":
    unittest.main()
