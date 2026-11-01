"""Shared query for the workspace list reports: every column is also an optional filter.

A column may name a child `table` and a source `field` when they differ from the report's
doctype and the column fieldname. Date columns are filtered by a DateRange filter.
"""

import frappe
from frappe import _

DOCSTATUS = {"Draft": 0, "Submitted": 1}
TEXT_TYPES = ("Data", "Small Text")
DATE_TYPES = ("Date", "Datetime")


def get_columns(columns):
	return [
		{key: value for key, value in column.items() if key not in ("table", "field")}
		| {"label": _(column["label"])}
		for column in columns
	]


def get_rows(doctype, columns, filters, conditions=None, order_by=None):
	"""Return rows the user may read, applying a filter for each column that has a value."""
	frappe.has_permission(doctype, "read", throw=True)
	conditions = list(conditions or [])
	fields = []
	for column in columns:
		table = column.get("table", doctype)
		field = column.get("field", column["fieldname"])
		fields.append(f"`tab{table}`.`{field}` as `{column['fieldname']}`")
		value = filters.get(column["fieldname"])
		if value in (None, "", []):
			continue
		if field == "docstatus":
			conditions.append([table, field, "=", DOCSTATUS.get(value, -1)])
		elif column["fieldtype"] in DATE_TYPES:
			value = frappe.parse_json(value)
			if isinstance(value, list | tuple) and len(value) == 2 and all(value):
				conditions.append([table, field, "between", list(value)])
		elif column["fieldtype"] in TEXT_TYPES:
			conditions.append([table, field, "like", f"%{value}%"])
		else:
			conditions.append([table, field, "=", value])
	rows = frappe.get_list(doctype, filters=conditions, fields=fields, order_by=order_by, limit_page_length=0)
	labels = {number: label for label, number in DOCSTATUS.items()}
	for row in rows:
		if "docstatus" in row:
			row.docstatus = _(labels.get(row.docstatus, ""))
	return rows
