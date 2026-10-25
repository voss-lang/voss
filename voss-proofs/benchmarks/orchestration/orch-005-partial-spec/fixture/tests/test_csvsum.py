import unittest

from csvsum import column_total


class CsvSumTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(column_total("name,amount\na,1\nb,2.5\n", "amount"), 3.5)
