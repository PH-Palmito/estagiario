import unittest

from tools.browser_wallet_commands import BrowserWalletCommands


class FakeWalletDeps:
    def __init__(self):
        self.private_wallet_url = ""
        self.default_wallet_url = "https://investidor10.com.br/wallet/my-wallet"
        self.configured_wallet_url = ""
        self.opened_wallet_app = "msedge"
        self.foreground_reads = []
        self.browser_reads = []
        self.clicks = []
        self.activated = []
        self.shortcuts = []
        self.closed_tabs = 0
        self.parsed = []
        self.refresh_result = {"summary": "Resumo publico"}
        self.refresh_error = None
        self.public_format = "Resumo formatado"
        self.web_opened = []
        self.investment_summary = "Resumo pela tela"
        self.sleeps = []
        self.current_time = 100.0

    def open_url_in_wallet_browser(self, url):
        self.opened_url = url
        return self.opened_wallet_app

    def read_foreground(self, **kwargs):
        if self.foreground_reads:
            return self.foreground_reads.pop(0)
        return ""

    def read_browser(self, **kwargs):
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

    def refresh_wallet(self, **kwargs):
        if self.refresh_error:
            raise self.refresh_error
        return self.refresh_result

    def format_public(self, **kwargs):
        return self.public_format

    def web_open(self, url, *args, **kwargs):
        self.web_opened.append((url, args, kwargs))

    def investment_snapshot(self):
        return self.investment_summary

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def now(self):
        self.current_time += 0.5
        return self.current_time


def make_commands(deps: FakeWalletDeps) -> BrowserWalletCommands:
    return BrowserWalletCommands(
        private_wallet_url=deps.private_wallet_url,
        default_wallet_url=deps.default_wallet_url,
        configured_wallet_url=deps.configured_wallet_url,
        open_url_in_wallet_browser=deps.open_url_in_wallet_browser,
        read_full_page_text_from_foreground=deps.read_foreground,
        read_full_page_text_from_browser=deps.read_browser,
        click_browser_element_by_text=deps.click,
        activate_window_names=deps.activate,
        shortcut=deps.shortcut,
        browser_close_tab=deps.close_tab,
        parse_wallet_text_blob=deps.parse_wallet,
        refresh_wallet_snapshot_auto=deps.refresh_wallet,
        format_public_wallet_refresh_result=deps.format_public,
        webbrowser_open=deps.web_open,
        investment_snapshot=deps.investment_snapshot,
        vk_control=1,
        vk_w=87,
        sleep=deps.sleep,
        now=deps.now,
    )


class BrowserWalletCommandsTests(unittest.TestCase):
    def test_visible_capture_summary_reads_and_closes_named_browser(self):
        deps = FakeWalletDeps()
        deps.foreground_reads = ["Patrimonio total\nR$ 8.409,14", "Patrimonio total\nR$ 8.409,14\nProventos"]

        result = make_commands(deps).visible_capture_summary("https://investidor10.com.br/wallet/private")

        self.assertEqual(result, "Carteira resumida")
        self.assertEqual(deps.parsed[0][1], "https://investidor10.com.br/wallet/private")
        self.assertEqual(deps.activated, [["msedge"]])
        self.assertEqual(deps.shortcuts, [(1, 87)])

    def test_visible_capture_summary_falls_back_to_browser_reader(self):
        deps = FakeWalletDeps()
        deps.foreground_reads = [""]
        deps.browser_reads = ["Patrimônio total\nR$ 8.409,14"]

        result = make_commands(deps).visible_capture_summary("https://investidor10.com.br/wallet/private")

        self.assertEqual(result, "Carteira resumida")
        self.assertTrue(deps.parsed)

    def test_visible_capture_summary_uses_generic_close_when_app_name_empty(self):
        deps = FakeWalletDeps()
        deps.opened_wallet_app = ""
        deps.foreground_reads = ["Patrimonio total\nR$ 8.409,14"]

        make_commands(deps).visible_capture_summary("https://investidor10.com.br/wallet/private")

        self.assertEqual(deps.closed_tabs, 1)

    def test_open_wallet_uses_private_visible_summary_first(self):
        deps = FakeWalletDeps()
        deps.private_wallet_url = "https://investidor10.com.br/wallet/private"
        deps.foreground_reads = ["Patrimonio total\nR$ 8.409,14"]

        result = make_commands(deps).open_wallet_and_summarize()

        self.assertEqual(result, "Abri sua carteira do Investidor10. Carteira resumida")
        self.assertEqual(deps.opened_url, deps.private_wallet_url)

    def test_open_wallet_uses_public_refresh_when_available(self):
        deps = FakeWalletDeps()

        result = make_commands(deps).open_wallet_and_summarize()

        self.assertEqual(result, "Abri sua carteira do Investidor10. Resumo publico")
        self.assertFalse(deps.web_opened)

    def test_open_wallet_falls_back_to_visible_summary_after_refresh_error(self):
        deps = FakeWalletDeps()
        deps.refresh_error = RuntimeError("offline")
        deps.foreground_reads = ["Patrimonio total\nR$ 8.409,14"]

        result = make_commands(deps).open_wallet_and_summarize()

        self.assertEqual(result, "Abri sua carteira do Investidor10. Carteira resumida")

    def test_open_wallet_final_fallback_opens_url_and_uses_investment_snapshot(self):
        deps = FakeWalletDeps()
        deps.default_wallet_url = "https://investidor10.com.br/carteira"

        result = make_commands(deps).open_wallet_and_summarize()

        self.assertIn("Abri a area da carteira do Investidor10", result)
        self.assertEqual(deps.web_opened[0][0], deps.default_wallet_url)
        self.assertIn("Resumo pela tela", result)


if __name__ == "__main__":
    unittest.main()
