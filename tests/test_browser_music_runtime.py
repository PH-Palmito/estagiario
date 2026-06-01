import unittest
from types import SimpleNamespace

from tools.browser_music_runtime import BrowserMusicRuntime


class FakeBrowserMusicRuntimeDeps:
    def __init__(self):
        self.stdout = ""
        self.commands = []
        self.clicks = []
        self.cursor = []
        self.focused = []
        self.opened = []
        self.started = []

    def run_powershell(self, script, **kwargs):
        self.commands.append((script, kwargs))
        return SimpleNamespace(stdout=self.stdout, returncode=0)

    def click(self, x, y, clicks=1):
        self.clicks.append((x, y, clicks))

    def set_cursor_pos(self, x, y):
        self.cursor.append((x, y))

    def focus_app(self, app):
        self.focused.append(app)

    def open_url(self, *args, **kwargs):
        self.opened.append((args, kwargs))

    def os_startfile(self, url):
        self.started.append(url)


def make_runtime(deps: FakeBrowserMusicRuntimeDeps) -> BrowserMusicRuntime:
    return BrowserMusicRuntime(
        normalize_text=lambda text: " ".join(str(text or "").lower().split()),
        run_powershell=deps.run_powershell,
        click=deps.click,
        set_cursor_pos=deps.set_cursor_pos,
        sleep=lambda _seconds: None,
        focus_app=deps.focus_app,
        open_url=deps.open_url,
        os_startfile=deps.os_startfile,
    )


class BrowserMusicRuntimeTests(unittest.TestCase):
    def test_reuses_music_and_spotify_instances(self):
        runtime = make_runtime(FakeBrowserMusicRuntimeDeps())

        self.assertIs(runtime.spotify_ui(), runtime.spotify_ui())
        self.assertIs(runtime.browser_music(), runtime.browser_music())

    def test_music_commands_delegate_to_browser_music(self):
        deps = FakeBrowserMusicRuntimeDeps()
        runtime = make_runtime(deps)

        result = runtime.search_music("spotify", "musicas curtidas")

        self.assertEqual(result, "Abrindo suas musicas curtidas no Spotify.")
        self.assertEqual(deps.started, ["spotify:collection:tracks"])

    def test_spotify_diagnostic_delegates_to_spotify_ui(self):
        deps = FakeBrowserMusicRuntimeDeps()
        deps.stdout = "Track | Text | x=1 y=2 w=3 h=4"
        runtime = make_runtime(deps)

        result = runtime.spotify_diagnostic()

        self.assertEqual(result, "Diagnostico Spotify:\nTrack | Text | x=1 y=2 w=3 h=4")
        self.assertEqual(deps.focused, ["spotify"])
        self.assertEqual(deps.commands[0][1]["timeout_seconds"], 12)


if __name__ == "__main__":
    unittest.main()
