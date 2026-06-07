import unittest

from core.router_media import detect_media_command


class RouterMediaTests(unittest.TestCase):
    def test_detects_target_pause(self):
        result = detect_media_command("pausar spotify")

        self.assertEqual(result, {"intent": "media_pause_target", "target": "spotify"})

    def test_detects_target_play_alias(self):
        result = detect_media_command("tocar you tube")

        self.assertEqual(result, {"intent": "media_play_target", "target": "youtube"})

    def test_detects_media_swap_routine(self):
        result = detect_media_command("pausa spotify e play youtube")

        self.assertEqual(result["intent"], "run_routine")
        self.assertEqual(result["target"], ["pausar spotify", "play youtube"])
        self.assertEqual(result["name"], "troca de midia")

    def test_detects_global_pause(self):
        result = detect_media_command("pausa")

        self.assertEqual(result, {"intent": "media_play_pause", "target": None})

    def test_detects_volume_up(self):
        result = detect_media_command("aumenta volume")

        self.assertEqual(result, {"intent": "volume_up", "target": None})

    def test_mute_requires_whole_word(self):
        self.assertEqual(detect_media_command("mudo"), {"intent": "volume_mute", "target": None})
        self.assertIsNone(detect_media_command("o que mudou na carteira desde ontem"))


if __name__ == "__main__":
    unittest.main()
