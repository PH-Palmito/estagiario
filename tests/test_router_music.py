import unittest

from core.router_music import detect_music_command


class RouterMusicTests(unittest.TestCase):
    def test_detects_spotify_diagnostic(self):
        self.assertEqual(detect_music_command("diagnosticar spotify"), {"intent": "spotify_diagnostic", "target": None})

    def test_detects_like_current_track(self):
        self.assertEqual(detect_music_command("salvar nas musicas curtidas"), {"intent": "spotify_like_current_track", "target": None})

    def test_detects_song_alias(self):
        self.assertEqual(
            detect_music_command("filho mil"),
            {"intent": "browser_search_music", "target": {"service": "spotify", "query": "filho meu"}},
        )

    def test_detects_music_session_vibe(self):
        self.assertEqual(
            detect_music_command("toca algo pra foco"),
            {"intent": "browser_music_session", "target": {"service": "spotify", "vibe": "foco"}},
        )

    def test_detects_surprise_music(self):
        self.assertEqual(
            detect_music_command("me surpreenda"),
            {"intent": "browser_surprise_music", "target": {"service": "spotify"}},
        )

    def test_detects_queue_music(self):
        self.assertEqual(
            detect_music_command("adicione filho meu na fila"),
            {"intent": "browser_queue_music", "target": {"service": "spotify", "query": "filho meu"}},
        )

    def test_detects_service_music_search(self):
        self.assertEqual(
            detect_music_command("toque bohemian rhapsody no youtube"),
            {"intent": "browser_search_music", "target": {"service": "youtube", "query": "bohemian rhapsody"}},
        )

    def test_detects_liked_songs_playlist(self):
        self.assertEqual(
            detect_music_command("abrir musicas curtidas"),
            {"intent": "browser_search_music", "target": {"service": "spotify", "query": "musicas curtidas"}},
        )


if __name__ == "__main__":
    unittest.main()
