"""Regression coverage for container counts versus historical document counts."""

import unittest

import frappe

from container.reporting import available_for_rent_card, pull_containers_card, rented_containers_card


class TestInventoryCards(unittest.TestCase):
	def test_counts_partition_inventory_across_cycles(self):
		frappe.db.savepoint("inventory_cards_test")
		try:
			baseline = self.counts()
			containers = []
			for _ in range(2):
				name = "TEST-CARD-" + frappe.generate_hash(length=10)
				# Inventory fixture only: Item/Item Price creation is unrelated to these counts.
				doc = frappe.get_doc({"doctype": "Container", "name": name,
					"container_number": name, "status": "Empty"})
				doc.db_insert()
				containers.append(name)
			rent_type = frappe.get_doc({"doctype": "Rent Type",
				"rent_type": "TEST-CARD-" + frappe.generate_hash(length=10)}).insert()

			def rental(names):
				return frappe.get_doc({"doctype": "Rent A Container", "rent_type": rent_type.name,
					"containers": [{"container": name} for name in names]}).insert()

			def expect(rented, pulled, available):
				self.assertEqual(self.counts(), tuple(
					base + delta for base, delta in zip(baseline, (rented, pulled, available))
				))

			rent = rental(containers)
			expect(0, 0, 2)  # Draft rentals do not block availability.
			rent.submit()
			expect(2, 0, 0)  # One rental document contains two rented containers.
			pull = frappe.get_doc({"doctype": "Pull Container",
				"containers": [{"container": containers[0]}]}).insert()
			expect(1, 1, 0)  # Pulled container is no longer counted as rented.
			emptying = frappe.get_doc({"doctype": "Emptying Container",
				"container": containers[0]}).insert()
			expect(1, 0, 1)  # Historical rental and pull do not inflate counts.
			frappe.delete_doc("Emptying Container", emptying.name)
			expect(1, 1, 0)
			pull.submit()
			pull.cancel()
			expect(2, 0, 0)
			duplicate = rental([containers[0]])
			duplicate.submit()
			expect(2, 0, 0)  # Distinct containers, even with overlapping rental records.
			duplicate.cancel()
			rent.cancel()
			expect(0, 0, 2)
		finally:
			frappe.db.rollback(save_point="inventory_cards_test")

	def counts(self):
		cards = [rented_containers_card(), pull_containers_card(), available_for_rent_card()]
		values = tuple(card["value"] for card in cards)
		total = len(frappe.get_list("Container", pluck="name", limit_page_length=0))
		self.assertEqual(sum(values), total)
		self.assertEqual(cards[0]["route"], ["List", "Rent A Container", "List"])
		self.assertEqual(cards[1]["route"], ["List", "Pull Container", "List"])
		return values
