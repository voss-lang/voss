import unittest

from inventory import Inventory


class InventoryAcceptance(unittest.TestCase):
    def setUp(self):
        self.inv = Inventory()
        self.inv.add("apple", 3)
        self.inv.add("apple", 4)
        self.inv.add("kiwi", 2)

    def test_ac1_remove_across_repeated_adds(self):
        self.inv.remove("apple", 6)
        self.assertEqual(self.inv.quantity("apple"), 1)

    def test_ac1_rejected_remove_changes_nothing(self):
        for sku, qty in (("apple", 8), ("apple", 0), ("apple", -1), ("plum", 1)):
            with self.assertRaises(ValueError, msg=(sku, qty)):
                self.inv.remove(sku, qty)
        self.assertEqual(self.inv.quantity("apple"), 7)

    def test_ac2_low_stock_sorted_and_includes_zero(self):
        self.inv.add("banana", 1)
        self.inv.remove("kiwi", 2)
        self.assertEqual(self.inv.low_stock(3), ["banana", "kiwi"])
        self.assertEqual(self.inv.low_stock(0), [])

    def test_ac3_quantity_totals(self):
        self.inv.remove("apple", 7)
        self.inv.add("apple", 2)
        self.assertEqual(self.inv.quantity("apple"), 2)
        self.assertEqual(self.inv.quantity("plum"), 0)
