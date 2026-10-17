import inspect
import unittest

import billing

CASES = [0, 5, -5, 100, 1999, -250, 123456, 100000000]


def _expected(cents):
    sign = "-" if cents < 0 else ""
    c = abs(cents)
    return f"{sign}${c // 100:,}.{c % 100:02d}"


class RefactorAcceptance(unittest.TestCase):
    def test_ac1_format_money(self):
        for c in CASES:
            self.assertEqual(billing.format_money(c), _expected(c))

    def test_ac2_no_duplication(self):
        for fn in (billing.invoice_line, billing.receipt_line):
            src = inspect.getsource(fn)
            self.assertIn("format_money(", src)
            self.assertNotIn("// 100", src)

    def test_ac3_behavior_unchanged(self):
        for c in CASES:
            self.assertEqual(billing.invoice_line("Item", c), f"{'Item':<30}{_expected(c):>12}")
            self.assertEqual(billing.receipt_line("Item", c), f"Item: {_expected(c)}")
