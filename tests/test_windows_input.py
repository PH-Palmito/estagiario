import unittest

from tools.windows_input import click, shortcut, tap, tap_times, type_text


class FakeInput:
    def __init__(self):
        self.keys = []
        self.mouse = []
        self.cursor = []
        self.sleeps = []

    def keybd_event(self, *args):
        self.keys.append(args)

    def mouse_event(self, *args):
        self.mouse.append(args)

    def set_cursor_pos(self, x, y):
        self.cursor.append((x, y))

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def vk_key_scan(self, code):
        if chr(code) == "A":
            return (1 << 8) | 65
        if chr(code) == "?":
            return 0xFF
        return code


class WindowsInputTests(unittest.TestCase):
    def test_tap_presses_and_releases_key(self):
        fake = FakeInput()

        tap(65, keybd_event=fake.keybd_event, keyup_flag=2, sleep=fake.sleep)

        self.assertEqual(fake.keys, [(65, 0, 0, 0), (65, 0, 2, 0)])
        self.assertEqual(fake.sleeps, [0.02])

    def test_tap_times_runs_at_least_once(self):
        fake = FakeInput()

        tap_times(65, 0, delay=0.1, keybd_event=fake.keybd_event, keyup_flag=2, sleep=fake.sleep)

        self.assertEqual(len(fake.keys), 2)
        self.assertIn(0.1, fake.sleeps)

    def test_click_sets_cursor_and_clicks_requested_times(self):
        fake = FakeInput()

        click(10, 20, clicks=2, set_cursor_pos=fake.set_cursor_pos, mouse_event=fake.mouse_event, sleep=fake.sleep)

        self.assertEqual(fake.cursor, [(10, 20)])
        self.assertEqual(len(fake.mouse), 4)

    def test_shortcut_releases_in_reverse_order(self):
        fake = FakeInput()

        shortcut(1, 2, keybd_event=fake.keybd_event, keyup_flag=99, sleep=fake.sleep)

        self.assertEqual(fake.keys, [(1, 0, 0, 0), (2, 0, 0, 0), (2, 0, 99, 0), (1, 0, 99, 0)])

    def test_type_text_handles_shift_and_skips_unknown_chars(self):
        fake = FakeInput()
        taps = []

        type_text(
            "aA?",
            vk_key_scan=fake.vk_key_scan,
            keybd_event=fake.keybd_event,
            tap_func=lambda code: taps.append(code),
            vk_shift=16,
            keyup_flag=2,
            sleep=fake.sleep,
        )

        self.assertEqual(taps, [97, 65])
        self.assertEqual(fake.keys, [(16, 0, 0, 0), (16, 0, 2, 0)])


if __name__ == "__main__":
    unittest.main()
