import unittest

from textkit.numbers import parse_int
from textkit.ranges import clamp
from textkit.words import word_count


class TextkitTest(unittest.TestCase):
    def test_word_count(self):
        self.assertEqual(word_count("one two  three"), 3)

    def test_parse_int(self):
        self.assertEqual(parse_int("1_000"), 1000)
        with self.assertRaises(ValueError):
            parse_int("12a")

    def test_clamp(self):
        self.assertEqual(clamp(15, 0, 10), 10)
        with self.assertRaises(ValueError):
            clamp(1, 10, 0)
