import unittest

from core.router_fast_path import detect_fast_path_command


class RouterFastPathTests(unittest.TestCase):
    def test_open_spotify(self):
        self.assertEqual(detect_fast_path_command("abrir spotify"), {"intent": "open_app", "target": "spotify"})

    def test_like_current_track(self):
        self.assertEqual(
            detect_fast_path_command("gostei dessa"),
            {"intent": "spotify_like_current_track", "target": None},
        )

    def test_next_music_is_not_dislike(self):
        self.assertIsNone(detect_fast_path_command("proxima musica"))

    def test_less_music_vibe(self):
        self.assertEqual(
            detect_fast_path_command("menos triste"),
            {"intent": "spotify_less_music_vibe", "target": {"vibe": "triste"}},
        )

    def test_marketplace_search(self):
        self.assertEqual(
            detect_fast_path_command("pesquise notebook no mercado livre"),
            {
                "intent": "browser_search_site",
                "target": {"query": "notebook", "site": "https://www.mercadolivre.com.br"},
            },
        )

    def test_youtube_search(self):
        self.assertEqual(
            detect_fast_path_command("pesquise aulas de python no youtube"),
            {
                "intent": "browser_search_site",
                "target": {"query": "aulas python", "site": "https://www.youtube.com"},
            },
        )

    def test_spotify_standalone_song_alias(self):
        self.assertEqual(
            detect_fast_path_command("filho mil"),
            {"intent": "browser_search_music", "target": {"service": "spotify", "query": "filho meu"}},
        )

    def test_direct_music_search(self):
        self.assertEqual(
            detect_fast_path_command("toca radiohead"),
            {"intent": "browser_search_music", "target": {"service": "spotify", "query": "radiohead"}},
        )


if __name__ == "__main__":
    unittest.main()
