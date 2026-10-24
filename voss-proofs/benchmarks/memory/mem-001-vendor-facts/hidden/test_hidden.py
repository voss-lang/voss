import unittest

import vendor


class VendorAcceptance(unittest.TestCase):
    def test_ac1_build_url(self):
        for path in ("/v1/items", "v1/items"):
            self.assertEqual(vendor.build_url(path), "https://api.acme.test/v1/items")

    def test_ac2_header(self):
        self.assertEqual(vendor.build_request("v1/items")["headers"].get("X-Client"), "proofs-7731")

    def test_ac3_rate_limit(self):
        self.assertEqual(vendor.RATE_LIMIT_PER_SECOND, 7)
