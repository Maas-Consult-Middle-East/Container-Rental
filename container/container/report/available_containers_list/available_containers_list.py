"""Containers with status Empty, ready to rent."""

from container.container.report.list_report import get_columns, get_rows

COLUMNS = [
	{"fieldname": "name", "label": "Container", "fieldtype": "Link", "options": "Container", "width": 150},
	{"fieldname": "container_size", "label": "Container Size", "fieldtype": "Data", "width": 130},
	{"fieldname": "classification", "label": "Classification", "fieldtype": "Link", "options": "Classification", "width": 150},
	{"fieldname": "branch_name", "label": "Branch", "fieldtype": "Link", "options": "Branch", "width": 150},
]


def execute(filters=None):
	rows = get_rows(
		"Container",
		COLUMNS,
		filters or {},
		conditions=[["status", "=", "Empty"]],
		order_by="`tabContainer`.name asc",
	)
	return get_columns(COLUMNS), rows
