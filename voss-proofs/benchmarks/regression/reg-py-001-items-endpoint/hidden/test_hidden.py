import unittest

import api


class ItemsAcceptance(unittest.TestCase):
    def setUp(self):
        api.reset()

    def test_ac1_create_sequential_ids(self):
        self.assertEqual(api.handle("POST", "/items", {"name": "a"}), (201, {"id": 1, "name": "a"}))
        self.assertEqual(api.handle("POST", "/items", {"name": "b"}), (201, {"id": 2, "name": "b"}))

    def test_ac2_name_required(self):
        for body in (None, {}, {"name": ""}, {"name": 3}):
            self.assertEqual(api.handle("POST", "/items", body), (400, {"error": "name required"}))

    def test_ac3_list_in_order(self):
        api.handle("POST", "/items", {"name": "x"})
        api.handle("POST", "/items", {"name": "y"})
        status, body = api.handle("GET", "/items")
        self.assertEqual(status, 200)
        self.assertEqual([i["name"] for i in body["items"]], ["x", "y"])

    def test_ac4_method_not_allowed_and_unknown(self):
        self.assertEqual(api.handle("DELETE", "/items"), (405, {"error": "method not allowed"}))
        self.assertEqual(api.handle("POST", "/health"), (405, {"error": "method not allowed"}))
        self.assertEqual(api.handle("GET", "/nope"), (404, {"error": "not found"}))

    def test_ac5_reset_and_health(self):
        api.handle("POST", "/items", {"name": "z"})
        api.reset()
        self.assertEqual(api.handle("GET", "/items"), (200, {"items": []}))
        self.assertEqual(api.handle("GET", "/health"), (200, {"status": "ok"}))
