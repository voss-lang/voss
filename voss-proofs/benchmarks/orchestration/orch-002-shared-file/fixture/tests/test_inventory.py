import unittest

from inventory import Inventory


class InventoryTest(unittest.TestCase):
    def test_remove(self):
        inv = Inventory()
        inv.add("apple", 5)
        inv.remove("apple", 2)
        self.assertEqual(inv.quantity("apple"), 3)

    def test_low_stock(self):
        inv = Inventory()
        inv.add("pear", 1)
        inv.add("fig", 9)
        self.assertEqual(inv.low_stock(5), ["pear"])
