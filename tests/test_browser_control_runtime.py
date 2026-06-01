import unittest
from types import SimpleNamespace

from tools.browser_control_runtime import BrowserControlRuntime


class FakeBrowserControlRuntimeDeps:
    def __init__(self):
        self.active = True
        self.stdout = ""
        self.commands = []
        self.calls = []
        self.rect = (10, 20, 110, 220)

    def activate(self):
        return self.active

    def run_powershell(self, script, **kwargs):
        self.commands.append((script, kwargs))
        return SimpleNamespace(stdout=self.stdout, returncode=0)

    def shortcut(self, *keys):
        self.calls.append(("shortcut", keys))

    def tap(self, key):
        self.calls.append(("tap", key))

    def click(self, x, y, clicks=1):
        self.calls.append(("click", x, y, clicks))

    def get_rect(self):
        return self.rect

    def type_text(self, text):
        self.calls.append(("type_text", text))

    def open_url(self, *args, **kwargs):
        self.calls.append(("open_url", args, kwargs))

    def keybd_event(self, *args):
        self.calls.append(("keybd_event", args))

    def mouse_event(self, *args):
        self.calls.append(("mouse_event", args))


def make_runtime(deps: FakeBrowserControlRuntimeDeps) -> BrowserControlRuntime:
    return BrowserControlRuntime(
        browser_names=["chrome", "msedge"],
        activate_browser_window=deps.activate,
        run_powershell=deps.run_powershell,
        shortcut=deps.shortcut,
        tap=deps.tap,
        click=deps.click,
        get_browser_window_rect=deps.get_rect,
        type_text=deps.type_text,
        open_url=deps.open_url,
        keybd_event=deps.keybd_event,
        mouse_event=deps.mouse_event,
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


class BrowserControlRuntimeTests(unittest.TestCase):
    def test_reuses_ui_and_controls_instances(self):
        runtime = make_runtime(FakeBrowserControlRuntimeDeps())

        self.assertIs(runtime.ui(), runtime.ui())
        self.assertIs(runtime.controls(), runtime.controls())

    def test_normalizes_text(self):
        runtime = make_runtime(FakeBrowserControlRuntimeDeps())

        self.assertEqual(runtime.normalize_text("OlÃ¡, Mundo!"), "ola mundo")

    def test_click_first_browser_link_delegates_to_ui(self):
        deps = FakeBrowserControlRuntimeDeps()
        deps.stdout = "__POINT__:30,40"
        runtime = make_runtime(deps)

        self.assertTrue(runtime.click_first_browser_link())
        self.assertIn("'chrome'", deps.commands[0][0])
        self.assertEqual(deps.calls, [("click", 30, 40, 1)])

    def test_search_delegates_to_controls(self):
        deps = FakeBrowserControlRuntimeDeps()
        runtime = make_runtime(deps)

        result = runtime.search("python")

        self.assertEqual(result, "Pesquisando por python na aba atual.")
        self.assertEqual(deps.calls, [("shortcut", (17, 76)), ("type_text", "python"), ("tap", 13)])

    def test_small_scroll_delegates_to_controls(self):
        deps = FakeBrowserControlRuntimeDeps()
        runtime = make_runtime(deps)

        self.assertEqual(runtime.scroll_down_small(), "Descendo um pouco.")
        self.assertEqual(deps.calls, [("mouse_event", (0x0800, 0, 0, -350, 0))])


if __name__ == "__main__":
    unittest.main()
