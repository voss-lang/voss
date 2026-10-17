import unittest

from slug import slugify


class SlugAcceptance(unittest.TestCase):
    def test_ac1_collapses_runs(self):
        self.assertEqual(slugify("Hello,  World!"), "hello-world")
        self.assertEqual(slugify("a -- b __ c"), "a-b-c")

    def test_ac2_edges(self):
        self.assertEqual(slugify("--a--b--"), "a-b")
        self.assertEqual(slugify("!!!"), "")

    def test_ac3_unchanged(self):
        self.assertEqual(slugify("Hello World"), "hello-world")
        self.assertEqual(slugify("already-a-slug"), "already-a-slug")
        self.assertEqual(slugify("Release 2.0"), "release-2-0")
        self.assertEqual(slugify(""), "")
