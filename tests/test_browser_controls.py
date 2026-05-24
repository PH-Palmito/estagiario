import unittest

from tools.browser_controls import BrowserControls


class BrowserControlsTests(unittest.TestCase):
    def make_controls(self, active=True, rect=(10, 20, 110, 220), text_found=True):
        calls = []

        controls = BrowserControls(
            activate_browser_window=lambda: active,
            shortcut=lambda *keys: calls.append(("shortcut", keys)),
            tap=lambda key: calls.append(("tap", key)),
            click=lambda x, y: calls.append(("click", x, y)),
            get_browser_window_rect=lambda: rect,
            click_first_browser_link=lambda: True,
            click_browser_element_by_text=lambda query: text_found,
            type_text=lambda text: calls.append(("type_text", text)),
            open_url=lambda *args, **kwargs: calls.append(("open_url", args, kwargs)),
            keybd_event=lambda *args: calls.append(("keybd_event", args)),
            mouse_event=lambda *args: calls.append(("mouse_event", args)),
            keyup_flag=2,
            mouse_wheel_flag=0x0800,
            vk_control=17,
            vk_shift=16,
            vk_menu=18,
            vk_tab=9,
            vk_w=87,
            vk_l=76,
            vk_f=70,
            vk_f5=116,
            vk_add=107,
            vk_subtract=109,
            vk_0=48,
            vk_return=13,
            vk_prior=33,
            vk_next=34,
            vk_end=35,
            vk_home=36,
            vk_left=37,
            vk_right=39,
            sleep=lambda _seconds: None,
        )
        return controls, calls

    def test_new_tab_uses_shortcut_when_browser_is_active(self):
        controls, calls = self.make_controls(active=True)

        self.assertEqual(controls.new_tab(), "Abrindo nova aba.")

        self.assertEqual(calls, [("shortcut", (17, 0x54))])

    def test_new_tab_opens_google_when_browser_is_inactive(self):
        controls, calls = self.make_controls(active=False)

        self.assertEqual(controls.new_tab(), "Abrindo nova aba.")

        self.assertEqual(calls, [("open_url", ("https://www.google.com",), {"new": 2})])

    def test_close_tab_rejects_inactive_browser(self):
        controls, calls = self.make_controls(active=False)

        self.assertEqual(controls.close_tab(), "Nao encontrei um navegador aberto para fechar a aba.")
        self.assertEqual(calls, [])

    def test_back_uses_alt_left(self):
        controls, calls = self.make_controls(active=True)

        self.assertEqual(controls.back(), "Voltando pagina.")

        self.assertEqual(
            calls,
            [
                ("keybd_event", (18, 0, 0, 0)),
                ("tap", 37),
                ("keybd_event", (18, 0, 2, 0)),
            ],
        )

    def test_search_uses_current_tab_when_active(self):
        controls, calls = self.make_controls(active=True)

        self.assertEqual(controls.search("python"), "Pesquisando por python na aba atual.")

        self.assertEqual(calls, [("shortcut", (17, 76)), ("type_text", "python"), ("tap", 13)])

    def test_search_opens_google_when_inactive(self):
        controls, calls = self.make_controls(active=False)

        self.assertEqual(controls.search("python basico"), "Pesquisando por python basico em uma nova aba.")

        self.assertEqual(
            calls,
            [("open_url", ("https://www.google.com/search?q=python+basico",), {"new": 2})],
        )

    def test_click_center_uses_window_center(self):
        controls, calls = self.make_controls(rect=(10, 20, 110, 220))

        self.assertEqual(controls.click_center(), "Clicando no centro da pagina.")

        self.assertEqual(calls, [("click", 60.0, 120.0)])

    def test_click_text_reports_found_and_not_found(self):
        controls, _calls = self.make_controls(text_found=True)
        missing_controls, _missing_calls = self.make_controls(text_found=False)

        self.assertEqual(controls.click_text("comprar"), "Clicando em comprar.")
        self.assertEqual(missing_controls.click_text("comprar"), "Nao encontrei comprar visivel na pagina.")

    def test_small_scroll_uses_mouse_wheel(self):
        controls, calls = self.make_controls()

        self.assertEqual(controls.scroll_down_small(), "Descendo um pouco.")
        self.assertEqual(controls.scroll_up_small(), "Subindo um pouco.")

        self.assertEqual(calls, [("mouse_event", (0x0800, 0, 0, -350, 0)), ("mouse_event", (0x0800, 0, 0, 350, 0))])


if __name__ == "__main__":
    unittest.main()
