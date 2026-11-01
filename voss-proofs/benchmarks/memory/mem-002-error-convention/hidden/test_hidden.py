import unittest

from errors import InputError
from parsing import parse_price, parse_qty


class ParsingAcceptance(unittest.TestCase):
    def assert_input_error(self, fn, text):
        with self.assertRaises(InputError, msg=text) as ctx:
            fn(text)
        self.assertNotIsInstance(ctx.exception, ValueError)
        self.assertTrue(str(ctx.exception).startswith(f"{fn.__name__}:"), str(ctx.exception))

    def test_ac1_parse_qty(self):
        self.assertEqual(parse_qty("3"), 3)
        for bad in ("x", "", "-2"):
            self.assert_input_error(parse_qty, bad)

    def test_ac2_parse_price(self):
        self.assertEqual(parse_price("12.50"), 1250)
        self.assertEqual(parse_price("3"), 300)
        self.assertEqual(parse_price("0.07"), 7)

    def test_ac3_parse_price_errors(self):
        for bad in ("abc", "", "-1.00", "1.234", "1.2.3"):
            self.assert_input_error(parse_price, bad)
