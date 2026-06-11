import unittest

from memory.investment_formatting import parse_percent_value


class InvestmentFormattingTests(unittest.TestCase):
    def test_parse_percent_accepts_dot_or_comma_decimal(self):
        self.assertEqual(parse_percent_value("-11.11%"), -11.11)
        self.assertEqual(parse_percent_value("-11,11%"), -11.11)
        self.assertEqual(parse_percent_value("1.234,56%"), 1234.56)


if __name__ == "__main__":
    unittest.main()
