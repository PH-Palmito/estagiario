import unittest
from unittest.mock import patch

from tools.browser_music import BrowserMusic, spotify_track_label


def make_music(**overrides):
    calls = []
    music = BrowserMusic(
        normalize_text=lambda text: " ".join(str(text or "").lower().split()),
        os_startfile=lambda url: calls.append(("startfile", url)),
        sleep=lambda seconds: calls.append(("sleep", seconds)),
        focus_app=lambda name: calls.append(("focus", name)),
        open_url=lambda *args, **kwargs: calls.append(("open", args, kwargs)),
        click_track_by_name=lambda _query: overrides.get("click_track", False),
        click_first_visible_track=lambda: overrides.get("click_first", False),
    )
    return music, calls


class BrowserMusicTests(unittest.TestCase):
    def test_track_label_includes_artist(self):
        self.assertEqual(spotify_track_label({"name": "Oceano", "artists": "Djavan"}), "Oceano, de Djavan")

    def test_search_music_opens_liked_songs(self):
        music, calls = make_music()

        result = music.search_music("spotify", "musicas curtidas")

        self.assertEqual(result, "Abrindo suas musicas curtidas no Spotify.")
        self.assertEqual(calls[0], ("startfile", "spotify:collection:tracks"))

    def test_search_music_falls_back_to_youtube_for_other_service(self):
        music, calls = make_music()

        result = music.search_music("youtube", "bohemian rhapsody")

        self.assertEqual(result, "Procurando bohemian rhapsody no YouTube.")
        self.assertEqual(calls, [("open", ("https://www.youtube.com/results?search_query=bohemian+rhapsody",), {})])

    @patch("tools.browser_music.spotify_search_track", return_value={"uri": "spotify:track:1", "name": "Oceano", "artists": "Djavan"})
    @patch("tools.browser_music.spotify_start_playback", return_value=True)
    def test_search_music_plays_best_track(self, _start, _search):
        music, _calls = make_music()

        result = music.search_music("spotify", "oceano")

        self.assertEqual(result, "Tocando Oceano, de Djavan, no Spotify.")

    @patch("tools.browser_music.spotify_search_track", return_value={"uri": "spotify:track:1", "name": "Oceano", "artists": "Djavan"})
    @patch("tools.browser_music.spotify_add_to_queue", return_value=True)
    def test_queue_music_adds_track(self, _queue, _search):
        music, _calls = make_music()

        result = music.queue_music("spotify", "oceano")

        self.assertEqual(result, "Adicionei Oceano, de Djavan, a fila do Spotify.")

    @patch("tools.browser_music.spotify_current_playback", return_value={"id": "1", "name": "Oceano", "artists": "Djavan"})
    @patch("tools.browser_music.spotify_save_track", return_value=True)
    def test_like_current_track_saves_track(self, _save, _current):
        music, _calls = make_music()

        result = music.like_current_track()

        self.assertEqual(result, "Gostei do seu gosto. Salvei Oceano, de Djavan nas suas musicas curtidas.")


if __name__ == "__main__":
    unittest.main()
