"""Populate list summaries without resaving rentals or changing their timestamps."""

import frappe


def execute():
	for name in frappe.get_all("Rent A Container", pluck="name"):
		doc = frappe.get_doc("Rent A Container", name)
		doc.update_container_names()
		frappe.db.set_value(
			"Rent A Container", name, "container_names", doc.container_names, update_modified=False
		)
