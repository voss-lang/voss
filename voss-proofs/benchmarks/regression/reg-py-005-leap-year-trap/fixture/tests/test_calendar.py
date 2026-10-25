import unittest

from calendar_utils import is_leap_year


class LeapTest(unittest.TestCase):
    def test_recent_years(self):
        self.assertTrue(is_leap_year(2024))
        self.assertFalse(is_leap_year(2023))
