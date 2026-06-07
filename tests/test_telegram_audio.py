import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from services import telegram_audio


class TelegramAudioTests(unittest.TestCase):
    def test_download_telegram_audio_uses_get_file_and_download_url(self):
        calls = []

        def fake_get(url, **kwargs):
            calls.append((url, kwargs))
            if "getFile" in url:
                return SimpleNamespace(
                    raise_for_status=lambda: None,
                    json=lambda: {"result": {"file_path": "voice/file_1.oga"}},
                )
            return SimpleNamespace(
                raise_for_status=lambda: None,
                content=b"audio-bytes",
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = telegram_audio.download_telegram_audio(
                "token",
                "voice:1",
                output_dir=Path(temp_dir),
                requests_get=fake_get,
            )

            self.assertEqual(path.read_bytes(), b"audio-bytes")
            self.assertEqual(path.suffix, ".oga")

        self.assertIn("getFile", calls[0][0])
        self.assertIn("voice/file_1.oga", calls[1][0])

    def test_transcribe_audio_file_joins_segments(self):
        class FakeModel:
            def transcribe(self, *_args, **_kwargs):
                return [SimpleNamespace(text=" ola "), SimpleNamespace(text=" mundo")], SimpleNamespace()

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "audio.oga"
            path.write_bytes(b"x")

            result = telegram_audio.transcribe_audio_file(path, get_model=lambda _name: FakeModel())

        self.assertEqual(result, "ola mundo")

    def test_transcribe_telegram_audio_request_downloads_and_transcribes(self):
        request = SimpleNamespace(media_file_id="voice-1")
        calls = []

        result = telegram_audio.transcribe_telegram_audio_request(
            request,
            token="token",
            download_audio=lambda token, file_id: calls.append((token, file_id)) or Path("audio.oga"),
            transcribe_file=lambda path: f"texto de {path}",
        )

        self.assertEqual(calls, [("token", "voice-1")])
        self.assertEqual(result, "texto de audio.oga")


if __name__ == "__main__":
    unittest.main()
