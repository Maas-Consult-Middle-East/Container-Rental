import unittest
from unittest.mock import patch

import frappe

from container import workflows


class TestInvoiceSources(unittest.TestCase):
	def test_combined_invoice_keeps_all_source_links(self):
		from container.invoice_sources import source_invoices, existing_source_invoice
		frappe.db.savepoint("combined_invoice_test")
		try:
			template_name = frappe.db.get_value("Rent A Container", {"docstatus": 1}, "name")
			self.assertTrue(template_name, "A rental with priced container Items is required")
			template = frappe.get_doc("Rent A Container", template_name)
			rentals = []
			for _ in range(2):
				rental = frappe.copy_doc(template)
				rental.docstatus = 0
				rental.insert()
				rental.submit()
				rentals.append(rental)
			contracts = []
			for _ in range(2):
				contract = frappe.get_doc({"doctype": "Container Contract",
					"name": "TEST-MULTI-" + frappe.generate_hash(length=10),
					"customer": template.client, "rent_type": template.rent_type, "total": 500,
					"containers": [{"container": "Typed contract container"}]}).insert()
				contract.submit()
				contracts.append(contract)
			invoice = frappe.new_doc("Sales Invoice")
			for source in rentals + contracts:
				invoice = workflows.fetch_container_invoice_items(source.doctype, source.name, invoice.as_json())
				with self.assertRaises(frappe.ValidationError):
					workflows.fetch_container_invoice_items(source.doctype, source.name, invoice.as_json())
			self.assertEqual({row.container_rent for row in invoice.items if row.container_rent}, {r.name for r in rentals})
			self.assertEqual({row.container_contract for row in invoice.items if row.container_contract}, {c.name for c in contracts})
			invoice.insert()
			invoice.reload()
			for field, sources in (("container_rent", rentals), ("container_contract", contracts)):
				links = source_invoices(field, [source.name for source in sources])
				self.assertEqual({row.get(field) for row in links}, {source.name for source in sources})
				self.assertEqual(len(links), 2)
				for source in sources:
					self.assertEqual(existing_source_invoice(field, source.name), invoice.name)
			self.assertEqual(workflows.make_sales_invoice_from_container_contract(contracts[1].name).name, invoice.name)
		finally:
			frappe.db.rollback(save_point="combined_invoice_test")

	def test_rental_mapping_checks_source_and_preserves_target(self):
		source = frappe._dict(name="RENT-TEST", client="CLIENT-TEST", docstatus=1)
		source.check_permission = lambda permission: None
		target = frappe.new_doc("Sales Invoice")
		target.customer = source.client
		get_doc = frappe.get_doc
		with patch.object(frappe, "get_doc", side_effect=lambda *args, **kwargs:
			source if args[0] == "Rent A Container" else get_doc(*args, **kwargs)), \
			patch.object(frappe, "has_permission", return_value=True), \
			patch.object(workflows, "existing_source_invoice", return_value=None), \
			patch.object(workflows, "_build_rental_invoice", side_effect=lambda source, invoice: invoice) as builder:
			result = workflows.fetch_container_invoice_items("Rent A Container", source.name, target.as_json())
			self.assertEqual(result.customer, source.client)
			builder.assert_called_once()
			self.assertEqual(builder.call_args.args[0], source)
			for values in ({"customer": "OTHER"}, {"docstatus": 1}, {"is_return": 1},
				{"container_rent": source.name}):
				with self.subTest(values=values):
					data = target.as_dict()
					data.update(values)
					with self.assertRaises(frappe.ValidationError):
						workflows.fetch_container_invoice_items("Rent A Container", source.name, data)
			for status in (0, 2):
				source.docstatus = status
				with self.assertRaises(frappe.ValidationError):
					workflows.fetch_container_invoice_items("Rent A Container", source.name, target.as_json())

	def test_invoice_create_permission_is_required(self):
		target = frappe.new_doc("Sales Invoice")
		with patch.object(frappe, "has_permission", side_effect=frappe.PermissionError):
			with self.assertRaises(frappe.PermissionError):
				workflows.fetch_container_invoice_items("Rent A Container", "RENT", target.as_json())
