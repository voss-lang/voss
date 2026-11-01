import unittest

from vendor import build_url


class VendorTest(unittest.TestCase):
    def test_build_url(self):
        self.assertEqual(build_url("/v1/items"), "https://api.acme.test/v1/items")
