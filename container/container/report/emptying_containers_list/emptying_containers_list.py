"""Every emptying that has not been cancelled."""

from container.container.report.list_report import get_columns, get_rows

COLUMNS = [
	{"fieldname": "name", "label": "Emptying ID", "fieldtype": "Link", "options": "Emptying Container", "width": 130},
	{"fieldname": "docstatus", "label": "Document Status", "fieldtype": "Select", "options": "\nDraft\nSubmitted", "width": 130},
	{"fieldname": "container", "label": "Container", "fieldtype": "Link", "options": "Container", "width": 130},
	{"fieldname": "emptying_date", "label": "Emptying Date", "fieldtype": "Date", "width": 120},
	{"fieldname": "baladiayya", "label": "Baladiyya", "fieldtype": "Link", "options": "Baladiyya", "width": 140},
	{"fieldname": "driver", "label": "Driver", "fieldtype": "Link", "options": "Driver", "width": 140},
	{"fieldname": "driver_commission", "label": "Driver Commission", "fieldtype": "Data", "width": 140},
	{"fieldname": "supervisor", "label": "Supervisor", "fieldtype": "Link", "options": "Employee", "width": 140},
	{"fieldname": "truck", "label": "Truck", "fieldtype": "Link", "options": "Vehicle", "width": 120},
	{"fieldname": "journal_entry", "label": "Journal Entry", "fieldtype": "Link", "options": "Journal Entry", "width": 150},
	{"fieldname": "notes", "label": "Notes", "fieldtype": "Small Text", "width": 220},
]


def execute(filters=None):
	rows = get_rows(
		"Emptying Container",
		COLUMNS,
		filters or {},
		conditions=[["docstatus", "!=", 2]],
		order_by="`tabEmptying Container`.emptying_date desc, `tabEmptying Container`.name desc",
	)
	return get_columns(COLUMNS), rows
