# Copyright (c) 2026, Salman Adayatt and Contributors
# See license.txt

import unittest

import frappe


class TestContainerContract(unittest.TestCase):
	def test_contract_invoice_draft_and_existing_invoice_reuse(self):
		from container.workflows import make_sales_invoice_from_container_contract, fetch_container_invoice_items

		frappe.db.savepoint("contract_invoice_test")
		try:
			contract = frappe.get_doc({
				"doctype": "Container Contract", "name": "TEST-INVOICE-" + frappe.generate_hash(length=10),
				"rent_type": frappe.db.get_value("Rent Type", {}, "name"),
				"customer": frappe.db.get_value("Customer", {}, "name"), "total": 500,
				"containers": [{"container": "Typed container <A>"}],
			}).insert()
			with self.assertRaises(frappe.ValidationError):
				make_sales_invoice_from_container_contract(contract.name)
			contract.submit()
			invoice = make_sales_invoice_from_container_contract(contract.name)
			self.assertTrue(invoice.is_new())
			self.assertEqual(invoice.docstatus, 0)
			self.assertEqual(invoice.container_contract, contract.name)
			self.assertEqual(invoice.customer, contract.customer)
			self.assertEqual(len(invoice.items), 1)
			self.assertEqual(invoice.items[0].rate, 500)
			self.assertEqual(invoice.items[0].qty, 1)
			self.assertIn("Typed container &lt;", invoice.items[0].description)
			self.assertNotIn("<", invoice.items[0].description)
			target = frappe.new_doc("Sales Invoice")
			target.company = invoice.company
			target.customer = contract.customer
			target.currency = invoice.currency
			target.append("items", {"item_name": "Existing service", "description": "Keep this service",
				"qty": 1, "rate": 25, "uom": invoice.items[0].uom,
				"income_account": invoice.items[0].income_account, "cost_center": invoice.items[0].cost_center})
			fetched = fetch_container_invoice_items("Container Contract", contract.name, target.as_json())
			self.assertEqual(len(fetched.items), 2)
			self.assertEqual(fetched.items[0].description, "Keep this service")
			self.assertEqual(fetched.items[1].rate, 500)
			self.assertEqual(fetched.container_contract, contract.name)
			with self.assertRaises(frappe.ValidationError):
				fetch_container_invoice_items("Container Contract", contract.name, fetched.as_json())
			invoice.insert()
			self.assertEqual(make_sales_invoice_from_container_contract(contract.name).name, invoice.name)
		finally:
			frappe.db.rollback(save_point="contract_invoice_test")

	def test_free_text_containers_save_and_submit_without_inventory_changes(self):
		frappe.db.savepoint("contract_form_test")
		try:
			rent_type = frappe.db.get_value("Rent Type", {}, "name")
			self.assertTrue(rent_type, "A Rent Type is required for the form test")
			inventory = frappe.get_all("Container", fields=["name", "status"], order_by="name")
			contract = frappe.get_doc({
				"doctype": "Container Contract",
				"name": "TEST-CONTRACT-" + frappe.generate_hash(length=10),
				"rent_type": rent_type,
				"contract_from": "2026-11-22",
				"contract_to": "2026-12-02",
				"containers": [{"container": "Free text container A", "classification": "12"},
					{"container": "Free text container B", "classification": "20"}],
			}).insert()
			contract.submit()
			contract.reload()
			self.assertEqual(contract.container_names, "Free text container A, Free text container B")
			self.assertEqual(contract.docstatus, 1)
			self.assertEqual(frappe.get_all("Container", fields=["name", "status"], order_by="name"), inventory)
		finally:
			frappe.db.rollback(save_point="contract_form_test")

	def test_rental_container_link_is_unchanged(self):
		self.assertEqual(frappe.get_meta("Contract Container").get_field("container").fieldtype, "Data")
		self.assertEqual(frappe.get_meta("Rent A Container Item").get_field("container").fieldtype, "Link")
		meta = frappe.get_meta("Container Contract")
		self.assertTrue(meta.get_field("location").hidden)
		self.assertEqual(meta.get_field("map_location").fieldtype, "Geolocation")
		self.assertEqual(meta.get_field("containers").options, "Contract Container")
