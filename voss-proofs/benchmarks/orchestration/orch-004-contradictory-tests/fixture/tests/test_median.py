import unittest

from stats import median


class MedianTest(unittest.TestCase):
    def test_median_of_empty_raises(self):
        with self.assertRaises(ValueError):
            median([])

    def test_median_of_empty_is_zero(self):
        self.assertEqual(median([]), 0)
