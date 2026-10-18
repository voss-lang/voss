import unittest

from stats import mean, median


class StatsAcceptance(unittest.TestCase):
    def test_ac1_mean(self):
        self.assertEqual(mean([1, 2]), 1.5)
        self.assertEqual(mean([2.5, 3.5]), 3.0)
        self.assertEqual(mean([-1, 2]), 0.5)
        with self.assertRaises(ValueError):
            mean([])

    def test_ac2_median_unchanged(self):
        self.assertEqual(median([3, 1, 2]), 2)
        self.assertEqual(median([4, 1, 3, 2]), 2.5)
        with self.assertRaises(ValueError):
            median([])
