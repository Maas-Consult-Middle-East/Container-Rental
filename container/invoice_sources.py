"""Resolve invoice sources from item rows, including older header-only invoices."""

import frappe


def source_invoices(field, names, fields=None, submitted=False, ignore_permissions=False):
	if field not in ("container_rent", "container_contract"):
		raise ValueError("Invalid invoice source field")
	if not names or (not ignore_permissions and not frappe.has_permission("Sales Invoice", "read")):
		return []
	query = frappe.get_all if ignore_permissions else frappe.get_list
	fields = list(dict.fromkeys(["name", *(fields or [])]))
	conditions = {"docstatus": 1 if submitted else ["!=", 2], "is_return": 0}
	result = {}
	for table in ("Sales Invoice", "Sales Invoice Item"):
		rows = query("Sales Invoice",
			filters=[["Sales Invoice", key, "=", value] if not isinstance(value, list)
				else ["Sales Invoice", key, *value] for key, value in conditions.items()]
				+ [[table, field, "in", sorted(set(names))]],
			fields=[f"`tabSales Invoice`.`{key}`" for key in fields if key != field]
				+ [f"`tab{table}`.`{field}` as `{field}`"],
			order_by="`tabSales Invoice`.posting_date desc, `tabSales Invoice`.creation desc",
			limit_page_length=0)
		for row in rows:
			result[(row.name, row.get(field))] = row
	return list(result.values())


def existing_source_invoice(field, name, exclude=None):
	return next((row.name for row in source_invoices(field, [name], ignore_permissions=True)
		if row.name != exclude), None)
