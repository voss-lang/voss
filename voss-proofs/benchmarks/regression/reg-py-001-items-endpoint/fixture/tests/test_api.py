import unittest

from api import handle


class HealthTest(unittest.TestCase):
    def test_health(self):
        self.assertEqual(handle("GET", "/health"), (200, {"status": "ok"}))
