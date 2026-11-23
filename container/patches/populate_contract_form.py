"""Preserve legacy location text in the replacement form without changing timestamps."""

import frappe


def execute():
	for contract in frappe.get_all("Container Contract", fields=["name", "location", "address"]):
		if contract.location and not contract.address:
			frappe.db.set_value("Container Contract", contract.name, "address", contract.location, update_modified=False)
