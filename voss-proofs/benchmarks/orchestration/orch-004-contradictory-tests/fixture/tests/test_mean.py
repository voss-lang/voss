import unittest

from stats import mean


class MeanTest(unittest.TestCase):
    def test_mean(self):
        self.assertEqual(mean([1, 2]), 1.5)
