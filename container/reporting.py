"""Compatibility endpoint for the existing custom number card."""

import frappe

from container.availability import active_container_operations, available_container_filters


def _active_operation_card(operation, doctype):
	frappe.has_permission("Container", "read", throw=True)
	frappe.has_permission(doctype, "read", throw=True)
	visible = set(frappe.get_list("Container", pluck="name", limit_page_length=0))
	rows = [
		row for row in active_container_operations()
		if row.operation == operation and row.container in visible
	]
	# Count containers, while retaining navigation to the relevant source documents.
	sources = sorted({row.source_name for row in rows})
	readable_sources = frappe.get_list(
		doctype, filters={"name": ["in", sources]}, pluck="name", limit_page_length=0
	) if sources else []
	return {
		"value": len({row.container for row in rows}),
		"fieldtype": "Int",
		"route": ["List", doctype, "List"],
		"route_options": {"name": ["in", readable_sources or [""]]},
	}


@frappe.whitelist()
def rented_containers_card(filters=None):
	return _active_operation_card("rental", "Rent A Container")


@frappe.whitelist()
def pull_containers_card(filters=None):
	return _active_operation_card("pull", "Pull Container")


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
