"""Compatibility endpoint for the existing custom number card."""

import frappe

from container.availability import available_container_filters


@frappe.whitelist()
def available_for_rent_card(filters=None):
	frappe.has_permission("Container", "read", throw=True)
	containers = frappe.get_list(
		"Container", filters=available_container_filters(), pluck="name", limit_page_length=0
	)
	return {
		"value": len(containers),
		"fieldtype": "Int",
		"route": ["List", "Container", "List"],
		"route_options": {"name": ["in", containers or [""]]},
	}

@frappe.whitelist()
def outstanding_card(filters=None):
	"""No value is calculated while custom reporting is disabled."""
	return {"value": None, "fieldtype": "Data"}
