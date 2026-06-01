import unittest

from tools.browser_windows_io import BrowserWindowsIO


class FakeVkKeyScan:
    restype = None

    def __call__(self, code):
        if chr(code) == "A":
            return 0x0100 | 65
        return code


class FakeUser32:
    def __init__(self):
        self.calls = []
        self.VkKeyScanW = FakeVkKeyScan()

    def keybd_event(self, *args):
        self.calls.append(("keybd", args))

    def mouse_event(self, *args):
        self.calls.append(("mouse", args))

    def SetCursorPos(self, *args):
        self.calls.append(("cursor", args))


class BrowserWindowsIOTests(unittest.TestCase):
    def make_io(self):
        user32 = FakeUser32()
        io = BrowserWindowsIO(
            user32=user32,
            browser_names=["chrome"],
            keyup_flag=2,
            leftdown_flag=4,
            leftup_flag=8,
            sleep=lambda _seconds: None,
        )
        return io, user32

    def test_tap_and_shortcut_delegate_to_keyboard(self):
        io, user32 = self.make_io()

        io.tap(65)
        io.shortcut(17, 76)

        self.assertIn(("keybd", (65, 0, 0, 0)), user32.calls)
        self.assertIn(("keybd", (65, 0, 2, 0)), user32.calls)
        self.assertIn(("keybd", (17, 0, 0, 0)), user32.calls)
        self.assertIn(("keybd", (76, 0, 2, 0)), user32.calls)

    def test_click_delegates_to_mouse(self):
        io, user32 = self.make_io()

        io.click(10.8, 20.2)

        self.assertEqual(user32.calls[0], ("cursor", (10, 20)))
        self.assertIn(("mouse", (4, 0, 0, 0, 0)), user32.calls)
        self.assertIn(("mouse", (8, 0, 0, 0, 0)), user32.calls)

    def test_type_text_uses_shift_when_needed(self):
        io, user32 = self.make_io()

        io.type_text("A", vk_shift=16)

        self.assertIn(("keybd", (16, 0, 0, 0)), user32.calls)
        self.assertIn(("keybd", (65, 0, 0, 0)), user32.calls)
        self.assertIn(("keybd", (16, 0, 2, 0)), user32.calls)


if __name__ == "__main__":
    unittest.main()
