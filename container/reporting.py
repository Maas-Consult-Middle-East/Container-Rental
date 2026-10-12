"""Compatibility endpoint for the existing custom number card."""

import frappe


@frappe.whitelist()
def outstanding_card(filters=None):
	"""No value is calculated while custom reporting is disabled."""
	return {"value": None, "fieldtype": "Data"}
