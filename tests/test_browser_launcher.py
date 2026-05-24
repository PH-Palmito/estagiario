import unittest

from tools.browser_launcher import (
    first_existing_browser,
    open_url_in_wallet_browser,
    preferred_wallet_browser,
)


class BrowserLauncherTests(unittest.TestCase):
    def test_first_existing_browser_returns_first_existing_path(self):
        self.assertEqual(
            first_existing_browser(["", "edge", "chrome"], path_exists=lambda path: path == "edge"),
            "edge",
        )
        self.assertEqual(first_existing_browser(["edge"], path_exists=lambda path: False), "")

    def test_preferred_wallet_browser_prefers_edge_over_chrome(self):
        result = preferred_wallet_browser(
            edge_candidates=("edge",),
            chrome_candidates=("chrome",),
            path_exists=lambda path: path in {"edge", "chrome"},
        )

        self.assertEqual(result, ("edge", "msedge"))

        result = preferred_wallet_browser(
            edge_candidates=("edge",),
            chrome_candidates=("chrome",),
            path_exists=lambda path: path == "chrome",
        )

        self.assertEqual(result, ("chrome", "chrome"))

    def test_open_url_in_wallet_browser_uses_preferred_browser(self):
        calls = []

        def fake_popen(args, **kwargs):
            calls.append((args, kwargs))

        result = open_url_in_wallet_browser(
            "https://example.com",
            preferred_browser_func=lambda: ("edge", "msedge"),
            popen=fake_popen,
        )

        self.assertEqual(result, "msedge")
        self.assertEqual(calls[0][0], ["edge", "--new-tab", "https://example.com"])

    def test_open_url_in_wallet_browser_falls_back_to_webbrowser(self):
        opened = []

        result = open_url_in_wallet_browser(
            "https://example.com",
            preferred_browser_func=lambda: ("", ""),
            open_url=lambda url, **kwargs: opened.append((url, kwargs)),
        )

        self.assertEqual(result, "")
        self.assertEqual(opened, [("https://example.com", {"new": 2})])


if __name__ == "__main__":
    unittest.main()
