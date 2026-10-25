import unittest

from calendar_utils import is_leap_year


class LeapAcceptance(unittest.TestCase):
    def test_ac1_every_fourth(self):
        for y in (1996, 2004, 2024):
            self.assertTrue(is_leap_year(y))
        for y in (2019, 2023):
            self.assertFalse(is_leap_year(y))

    def test_ac2_centuries(self):
        for y in (1700, 1800, 1900, 2100):
            self.assertFalse(is_leap_year(y))
        for y in (1600, 2000, 2400):
            self.assertTrue(is_leap_year(y))
