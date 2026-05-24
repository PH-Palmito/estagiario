import unittest

from core.direct_response import is_confirmation_no, is_confirmation_yes, smart_open_choice_kind


class DirectResponseTests(unittest.TestCase):
    def test_confirmation_yes_variants(self):
        self.assertTrue(is_confirmation_yes("sim"))
        self.assertTrue(is_confirmation_yes("pode sim"))
        self.assertFalse(is_confirmation_yes("talvez"))

    def test_confirmation_no_variants(self):
        self.assertTrue(is_confirmation_no("não"))
        self.assertTrue(is_confirmation_no("deixa quieto"))
        self.assertTrue(is_confirmation_no("cancele isso agora"))
        self.assertFalse(is_confirmation_no("sim"))

    def test_smart_open_choice_explicit_words(self):
        self.assertEqual(smart_open_choice_kind("abrir como aplicativo"), "app")
        self.assertEqual(smart_open_choice_kind("abrir como site"), "site")

    def test_smart_open_choice_aliases_and_fuzzy(self):
        self.assertEqual(smart_open_choice_kind("ap"), "app")
        self.assertEqual(smart_open_choice_kind("saite"), "site")
        self.assertEqual(smart_open_choice_kind("ehapp"), "app")

    def test_smart_open_choice_unknown(self):
        self.assertIsNone(smart_open_choice_kind("nao sei"))


if __name__ == "__main__":
    unittest.main()
