import unittest

from parsing import parse_qty


class ParsingTest(unittest.TestCase):
    def test_parse_qty(self):
        self.assertEqual(parse_qty("3"), 3)
