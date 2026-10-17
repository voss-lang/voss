import unittest

from pagination import page_count


class PaginationTest(unittest.TestCase):
    def test_exact_multiple(self):
        self.assertEqual(page_count(20, 10), 2)
