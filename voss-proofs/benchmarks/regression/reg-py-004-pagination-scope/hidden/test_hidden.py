import unittest

from pagination import page_count


class PaginationAcceptance(unittest.TestCase):
    def test_ac1_rounds_up(self):
        self.assertEqual(page_count(0, 10), 0)
        self.assertEqual(page_count(1, 10), 1)
        self.assertEqual(page_count(10, 10), 1)
        self.assertEqual(page_count(11, 10), 2)
        self.assertEqual(page_count(99, 10), 10)

    def test_ac2_invalid_per_page(self):
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                page_count(5, bad)
