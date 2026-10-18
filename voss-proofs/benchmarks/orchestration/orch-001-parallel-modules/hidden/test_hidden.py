import unittest

from textkit.numbers import parse_int
from textkit.ranges import clamp
from textkit.words import word_count


class TextkitAcceptance(unittest.TestCase):
    def test_ac1_word_count(self):
        self.assertEqual(word_count("one\ttwo\nthree   four"), 4)
        self.assertEqual(word_count(""), 0)
        self.assertEqual(word_count(" \t\n "), 0)
        self.assertEqual(word_count("  lead and trail  "), 3)

    def test_ac2_parse_int(self):
        self.assertEqual(parse_int("  42 "), 42)
        self.assertEqual(parse_int("-1_000_000"), -1000000)
        for bad in ("", "   ", "12a", "1.5"):
            with self.assertRaises(ValueError, msg=bad):
                parse_int(bad)

    def test_ac3_clamp(self):
        self.assertEqual(clamp(-3, 0, 10), 0)
        self.assertEqual(clamp(5, 0, 10), 5)
        self.assertEqual(clamp(4, 4, 4), 4)
        with self.assertRaises(ValueError):
            clamp(1, 10, 0)
