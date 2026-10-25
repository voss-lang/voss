import unittest

from csvsum import column_total


class CsvSumAcceptance(unittest.TestCase):
    def test_ac1_named_column(self):
        self.assertEqual(column_total("a,b\n1,10\n2,20\n", "b"), 30)
        with self.assertRaises(KeyError):
            column_total("a,b\n1,2\n", "c")

    def test_ac2_blank_lines(self):
        self.assertEqual(column_total("a,b\n\n1,2\n   \n3,4\n\n", "a"), 4)

    def test_ac3_quoted_commas(self):
        text = 'desc,amount\n"bolts, small",1.25\n"nuts, ""hex""",2\n'
        self.assertEqual(column_total(text, "amount"), 3.25)

    def test_ac4_line_number(self):
        with self.assertRaises(ValueError) as ctx:
            column_total("a,b\n1,2\n\n3,x\n", "b")
        self.assertIn("4", str(ctx.exception))
