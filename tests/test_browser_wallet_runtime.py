import unittest

from tools.browser_wallet_runtime import BrowserWalletRuntime


class FakeBrowserWalletRuntimeDeps:
    def __init__(self):
        self.opened_wallet_app = "msedge"
        self.foreground_reads = []
        self.browser_reads = []
        self.clicks = []
        self.activated = []
        self.shortcuts = []
        self.closed_tabs = 0
        self.parsed = []
        self.refresh_result = {"summary": "Resumo publico"}
        self.web_opened = []
        self.investment_summary = "Resumo pela tela"
        self.sleeps = []
        self.current_time = 100.0

    def open_url_in_wallet_browser(self, url):
        self.opened_url = url
        return self.opened_wallet_app

    def read_foreground(self, **_kwargs):
        if self.foreground_reads:
            return self.foreground_reads.pop(0)
        return ""

    def read_browser(self, **_kwargs):
        if self.browser_reads:
            return self.browser_reads.pop(0)
        return ""

    def click(self, text, **kwargs):
        self.clicks.append((text, kwargs))
        return True

    def activate(self, names):
        self.activated.append(names)
        return True

    def shortcut(self, *codes):
        self.shortcuts.append(codes)

    def close_tab(self):
        self.closed_tabs += 1
        return "fechada"

    def parse_wallet(self, text, url):
        self.parsed.append((text, url))
        return {"summary": "Carteira resumida"}

    def refresh_wallet(self, **_kwargs):
        return self.refresh_result

    def format_public(self, **_kwargs):
        return "Resumo formatado"

    def web_open(self, url, *args, **kwargs):
        self.web_opened.append((url, args, kwargs))

    def investment_snapshot(self):
        return self.investment_summary

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def now(self):
        self.current_time += 0.5
        return self.current_time


def make_runtime(deps: FakeBrowserWalletRuntimeDeps) -> BrowserWalletRuntime:
    return BrowserWalletRuntime(
        open_url_in_wallet_browser=deps.open_url_in_wallet_browser,
        read_full_page_text_from_foreground=deps.read_foreground,
        read_full_page_text_from_browser=deps.read_browser,
        click_browser_element_by_text=deps.click,
        activate_window_names=deps.activate,
        shortcut=deps.shortcut,
        browser_close_tab=deps.close_tab,
        investment_snapshot=deps.investment_snapshot,
        vk_control=1,
        vk_w=87,
        private_wallet_url="",
        default_wallet_url="https://investidor10.com.br/wallet/my-wallet",
        configured_wallet_url="",
        parse_wallet_text_blob=deps.parse_wallet,
        refresh_wallet_snapshot_auto=deps.refresh_wallet,
        format_public_wallet_refresh_result=deps.format_public,
        webbrowser_open=deps.web_open,
        sleep=deps.sleep,
        now=deps.now,
    )


class BrowserWalletRuntimeTests(unittest.TestCase):
    def test_reuses_commands_instance(self):
        runtime = make_runtime(FakeBrowserWalletRuntimeDeps())

        self.assertIs(runtime.commands(), runtime.commands())

    def test_visible_capture_summary_delegates_to_wallet_commands(self):
        deps = FakeBrowserWalletRuntimeDeps()
        deps.foreground_reads = ["Patrimonio total\nR$ 8.409,14"]
        runtime = make_runtime(deps)

        result = runtime.visible_capture_summary("https://investidor10.com.br/wallet/private")

        self.assertEqual(result, "Carteira resumida")
        self.assertEqual(deps.parsed[0][1], "https://investidor10.com.br/wallet/private")
        self.assertEqual(deps.activated, [["msedge"]])
        self.assertEqual(deps.shortcuts, [(1, 87)])

    def test_open_wallet_and_summarize_delegates_to_wallet_commands(self):
        deps = FakeBrowserWalletRuntimeDeps()
        runtime = make_runtime(deps)

        result = runtime.open_wallet_and_summarize()

        self.assertEqual(result, "Abri sua carteira do Investidor10. Resumo publico")
        self.assertFalse(deps.web_opened)


if __name__ == "__main__":
    unittest.main()
