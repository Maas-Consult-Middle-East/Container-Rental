import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from container import workflows


def source(**values):
	doc = frappe._dict(values)
	doc.check_permission = lambda permission: None
	return doc


class TestWorkflowMapping(unittest.TestCase):
	def test_container_rent_maps_to_trip(self):
		rent = source(
			doctype="Rent A Container",
			name="CR-0001",
			docstatus=1,
			containers=[frappe._dict(container="R11")],
			client="DEMO",
			classification="20 Yard",
			truck="TRUCK-1",
			driver="DRIVER-1",
			supervisor="EMP-1",
			address="Riyadh",
			cost=500,
			driver_commission=20,
			supervisor_commission=10,
			**{"from": "2026-10-12 10:00:00", "to": "2026-10-13 10:00:00"},
		)
		with patch.object(frappe, "has_permission", return_value=True), \
			patch.object(frappe, "get_doc", return_value=rent), \
			patch.object(frappe, "db", SimpleNamespace(exists=lambda *args, **kwargs: False)), \
			patch.object(frappe, "new_doc", return_value=frappe._dict()), \
			patch.object(workflows, "_find_contract", return_value=frappe._dict(name="CON-1")):
			trip = workflows._make_trip("Rent A Container", "CR-0001")
		self.assertEqual(trip.container, "R11")
		self.assertEqual(trip.customer, "DEMO")
		self.assertEqual(trip.contract, "CON-1")
		self.assertEqual(trip.source_doctype, "Rent A Container")
		self.assertEqual(trip.driver_commission, 20)
		self.assertEqual(trip.supervisor_commission, 10)

	def test_multi_container_rent_uses_selected_container(self):
		rent = source(
			doctype="Rent A Container",
			name="CR-0001",
			docstatus=1,
			containers=[frappe._dict(container="R11"), frappe._dict(container="R12")],
		)
		with patch.object(frappe, "has_permission", return_value=True), \
			patch.object(frappe, "get_doc", return_value=rent), \
			patch.object(frappe, "db", SimpleNamespace(exists=lambda *args, **kwargs: False)), \
			patch.object(frappe, "new_doc", return_value=frappe._dict()), \
			patch.object(workflows, "_find_contract", return_value=None), \
			patch.object(workflows, "_", side_effect=lambda text: text), \
			patch.object(frappe, "throw", side_effect=ValueError):
			with patch.object(frappe, "flags", frappe._dict(args=frappe._dict(container="R12"))):
				self.assertEqual(workflows._make_trip("Rent A Container", "CR-0001").container, "R12")
			for args in (None, frappe._dict(container="OTHER")):
				with patch.object(frappe, "flags", frappe._dict(args=args)), self.assertRaises(ValueError):
					workflows._make_trip("Rent A Container", "CR-0001")

	def test_replacement_uses_new_container_and_current_rental(self):
		replacement = source(
			doctype="Container Replacement",
			name="REP-1",
			docstatus=1,
			new_container_number="NEW-1",
			rented_container_number="OLD-1",
			replace_date="2026-10-12",
			truck="TRUCK-1",
			driver="DRIVER-1",
			supervisor="EMP-1",
			driver_commission=15,
			supervisor_commission=5,
		)
		rental = frappe._dict(client="DEMO", classification="20 Yard", address="Riyadh")
		with patch.object(frappe, "has_permission", return_value=True), \
			patch.object(frappe, "get_doc", return_value=replacement), \
			patch.object(frappe, "db", SimpleNamespace(exists=lambda *args, **kwargs: False)), \
			patch.object(frappe, "new_doc", return_value=frappe._dict()), \
			patch.object(workflows, "_rental_for_container", return_value=rental) as find_rental, \
			patch.object(workflows, "_find_contract", return_value=frappe._dict(name="CON-1")):
			trip = workflows._make_trip("Container Replacement", "REP-1")
		self.assertEqual(trip.container, "NEW-1")
		self.assertEqual(trip.customer, "DEMO")
		self.assertEqual(trip.pickup_date, "2026-10-12")
		find_rental.assert_called_once_with("OLD-1", "2026-10-12")

	def test_pull_maps_to_trip(self):
		pull = source(
			doctype="Pull Container",
			name="PULL-1",
			docstatus=1,
			containers=[frappe._dict(container="R11")],
			date="2026-10-12",
			truck="TRUCK-1",
			driver="DRIVER-1",
			supervisor=None,
			driver_commission=12,
			supervisor_commission=0,
		)
		with patch.object(frappe, "has_permission", return_value=True), \
			patch.object(frappe, "get_doc", return_value=pull), \
			patch.object(frappe, "db", SimpleNamespace(exists=lambda *args, **kwargs: False)), \
			patch.object(frappe, "new_doc", return_value=frappe._dict()), \
			patch.object(workflows, "_rental_for_container", return_value=frappe._dict(client="DEMO")), \
			patch.object(workflows, "_find_contract", return_value=frappe._dict(name="CON-1")):
			trip = workflows._make_trip("Pull Container", "PULL-1")
		self.assertEqual(trip.container, "R11")
		self.assertEqual(trip.source_doctype, "Pull Container")

	def test_trip_maps_driver_and_supervisor_commissions_separately(self):
		trip = source(
			doctype="Container Trip",
			name="CT-00001",
			docstatus=1,
			driver="DRIVER-1",
			supervisor="EMP-1",
			driver_commission=20,
			supervisor_commission=10,
		)
		with patch.object(frappe, "has_permission", return_value=True), \
			patch.object(frappe, "get_doc", return_value=trip), \
			patch.object(frappe, "db", SimpleNamespace(exists=lambda *args, **kwargs: False)), \
			patch.object(frappe, "new_doc", side_effect=lambda doctype: frappe._dict()):
			driver = workflows._make_commission("CT-00001", "Driver")
			supervisor = workflows._make_commission("CT-00001", "Supervisor")
		self.assertEqual((driver.commission_type, driver.driver, driver.amount), ("Driver", "DRIVER-1", 20))
		self.assertEqual(
			(supervisor.commission_type, supervisor.supervisor, supervisor.amount),
			("Supervisor", "EMP-1", 10),
		)

	def test_duplicate_trip_is_rejected(self):
		rent = source(
			doctype="Rent A Container", name="CR-0001", docstatus=1, containers=[frappe._dict(container="R11")]
		)
		with patch.object(frappe, "has_permission", return_value=True), \
			patch.object(frappe, "get_doc", return_value=rent), \
			patch.object(frappe, "db", SimpleNamespace(exists=lambda *args, **kwargs: "CT-00001")), \
			patch.object(workflows, "_", side_effect=lambda text: text), \
			patch.object(frappe, "throw", side_effect=ValueError):
			with self.assertRaises(ValueError):
				workflows._make_trip("Rent A Container", "CR-0001")

	def test_draft_source_is_rejected(self):
		rent = source(doctype="Rent A Container", name="CR-0001", docstatus=0)
		with patch.object(frappe, "has_permission", return_value=True), \
			patch.object(frappe, "get_doc", return_value=rent), \
			patch.object(workflows, "_", side_effect=lambda text: text), \
			patch.object(frappe, "throw", side_effect=ValueError):
			with self.assertRaises(ValueError):
				workflows._make_trip("Rent A Container", "CR-0001")
