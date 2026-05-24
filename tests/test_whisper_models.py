import unittest
from unittest.mock import patch

from huggingface_hub.errors import LocalEntryNotFoundError

from voice.whisper_models import clear_model_cache, get_model, model_repo


class WhisperModelsTests(unittest.TestCase):
    def tearDown(self):
        clear_model_cache()

    def test_model_repo_formats_systran_repo_name(self):
        self.assertEqual(model_repo("small"), "Systran/faster-whisper-small")

    def test_get_model_uses_local_snapshot_and_caches_model(self):
        fake_model = object()

        with (
            patch("voice.whisper_models.snapshot_download", return_value="local-path") as snapshot,
            patch("voice.whisper_models.WhisperModel", return_value=fake_model) as whisper_model,
        ):
            first = get_model("tiny")
            second = get_model("tiny")

        self.assertIs(first, fake_model)
        self.assertIs(second, fake_model)
        snapshot.assert_called_once_with("Systran/faster-whisper-tiny", local_files_only=True)
        whisper_model.assert_called_once_with("local-path", device="cpu", compute_type="int8")

    def test_get_model_falls_back_to_remote_snapshot_when_local_missing(self):
        fake_model = object()

        with (
            patch(
                "voice.whisper_models.snapshot_download",
                side_effect=[LocalEntryNotFoundError("missing"), "remote-path"],
            ) as snapshot,
            patch("voice.whisper_models.WhisperModel", return_value=fake_model),
        ):
            result = get_model("base")

        self.assertIs(result, fake_model)
        self.assertEqual(snapshot.call_args_list[0].kwargs, {"local_files_only": True})
        self.assertEqual(snapshot.call_args_list[1].kwargs, {"local_files_only": False})


if __name__ == "__main__":
    unittest.main()
