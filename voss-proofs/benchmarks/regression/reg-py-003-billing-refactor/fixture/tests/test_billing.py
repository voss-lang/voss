import unittest

from billing import invoice_line, receipt_line


class BillingTest(unittest.TestCase):
    def test_invoice(self):
        self.assertEqual(invoice_line("Widget", 1999), "Widget" + " " * 24 + "      $19.99")

    def test_receipt(self):
        self.assertEqual(receipt_line("Refund", -250), "Refund: -$2.50")
