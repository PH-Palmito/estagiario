import unittest
from types import SimpleNamespace

from tools.spotify_ui_automation import SpotifyUiAutomation


class FakeSpotifyUiDeps:
    def __init__(self):
        self.stdout = ""
        self.error = None
        self.commands = []
        self.clicks = []
        self.cursor = []
        self.sleeps = []
        self.focused = []

    def run_powershell(self, script, **kwargs):
        if self.error:
            raise self.error
        self.commands.append((script, kwargs))
        return SimpleNamespace(stdout=self.stdout, returncode=0)

    def click(self, x, y, clicks=1):
        self.clicks.append((x, y, clicks))

    def set_cursor_pos(self, x, y):
        self.cursor.append((x, y))

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def focus_app(self, app):
        self.focused.append(app)


def make_ui(deps: FakeSpotifyUiDeps) -> SpotifyUiAutomation:
    return SpotifyUiAutomation(
        run_powershell=deps.run_powershell,
        click=deps.click,
        set_cursor_pos=deps.set_cursor_pos,
        sleep=deps.sleep,
        focus_app=deps.focus_app,
    )


class SpotifyUiAutomationTests(unittest.TestCase):
    def test_click_track_by_name_uses_point_output(self):
        deps = FakeSpotifyUiDeps()
        deps.stdout = "__POINT__:10,20,2"

        self.assertTrue(make_ui(deps).click_track_by_name("Song Name"))
        self.assertIn("'song'", deps.commands[0][0])
        self.assertEqual(deps.cursor, [(10, 20)])
        self.assertEqual(deps.clicks, [(10, 20, 2)])

    def test_click_track_by_name_returns_false_without_query_or_point(self):
        deps = FakeSpotifyUiDeps()
        self.assertFalse(make_ui(deps).click_track_by_name("a"))

        deps = FakeSpotifyUiDeps()
        deps.stdout = "__NO_TRACK_TEXT__"
        self.assertFalse(make_ui(deps).click_track_by_name("Song Name"))

    def test_click_first_visible_track_uses_point_output(self):
        deps = FakeSpotifyUiDeps()
        deps.stdout = "__POINT__:30,40"

        self.assertTrue(make_ui(deps).click_first_visible_track())
        self.assertEqual(deps.cursor, [(30, 40)])
        self.assertEqual(deps.clicks, [(30, 40, 2)])

    def test_diagnostic_formats_common_results(self):
        deps = FakeSpotifyUiDeps()
        deps.stdout = "Track | Text | x=1 y=2 w=3 h=4"

        result = make_ui(deps).diagnostic()

        self.assertEqual(result, "Diagnostico Spotify:\nTrack | Text | x=1 y=2 w=3 h=4")
        self.assertEqual(deps.focused, ["spotify"])
        self.assertEqual(deps.commands[0][1]["timeout_seconds"], 12)

    def test_diagnostic_handles_missing_spotify_root_empty_and_errors(self):
        deps = FakeSpotifyUiDeps()
        deps.stdout = "__NO_SPOTIFY__"
        self.assertEqual(make_ui(deps).diagnostic(), "Nao encontrei uma janela aberta do Spotify.")

        deps = FakeSpotifyUiDeps()
        deps.stdout = "__NO_ROOT__"
        self.assertEqual(make_ui(deps).diagnostic(), "Nao consegui ler a janela do Spotify.")

        deps = FakeSpotifyUiDeps()
        self.assertEqual(make_ui(deps).diagnostic(), "O diagnostico nao encontrou textos visiveis no Spotify.")

        deps = FakeSpotifyUiDeps()
        deps.error = RuntimeError("boom")
        self.assertIn("Erro no diagnostico do Spotify", make_ui(deps).diagnostic())


if __name__ == "__main__":
    unittest.main()
