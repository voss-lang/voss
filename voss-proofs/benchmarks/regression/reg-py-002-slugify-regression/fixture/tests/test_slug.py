import unittest

from slug import slugify


class SlugTest(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_strips_edges(self):
        self.assertEqual(slugify(" Title "), "title")
