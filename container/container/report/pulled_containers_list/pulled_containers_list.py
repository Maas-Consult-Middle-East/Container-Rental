"""Every container on a pull that has not been cancelled."""

from container.container.report.list_report import get_columns, get_rows

COLUMNS = [
	{"fieldname": "name", "label": "Pull ID", "fieldtype": "Link", "options": "Pull Container", "width": 130},
	{"fieldname": "docstatus", "label": "Document Status", "fieldtype": "Select", "options": "\nDraft\nSubmitted", "width": 130},
	{"fieldname": "container", "label": "Container", "fieldtype": "Link", "options": "Container", "width": 130, "table": "Pull Container Item"},
	{"fieldname": "container_size", "label": "Container Size", "fieldtype": "Data", "width": 120, "table": "Pull Container Item"},
	{"fieldname": "date", "label": "Date", "fieldtype": "Date", "width": 110},
	{"fieldname": "rent_a_container", "label": "Rent ID", "fieldtype": "Link", "options": "Rent A Container", "width": 130},
	{"fieldname": "rent_type", "label": "Rent Type", "fieldtype": "Link", "options": "Rent Type", "width": 120},
	{"fieldname": "client", "label": "Client", "fieldtype": "Link", "options": "Customer", "width": 180},
	{"fieldname": "contact_number", "label": "Contact Number", "fieldtype": "Data", "width": 140},
	{"fieldname": "cr_number", "label": "CR Number", "fieldtype": "Data", "width": 120},
	{"fieldname": "address", "label": "Address", "fieldtype": "Data", "width": 200},
	{"fieldname": "classification", "label": "Classification", "fieldtype": "Link", "options": "Classification", "width": 140},
	{"fieldname": "cost", "label": "Cost", "fieldtype": "Data", "width": 100},
	{"fieldname": "container_contract", "label": "Container Contract", "fieldtype": "Link", "options": "Container Contract", "width": 150},
	{"fieldname": "rent_from", "label": "Rent From", "fieldtype": "Date", "width": 110},
	{"fieldname": "rent_to", "label": "Rent To", "fieldtype": "Date", "width": 110},
	{"fieldname": "driver", "label": "Driver", "fieldtype": "Link", "options": "Driver", "width": 140},
	{"fieldname": "driver_commission", "label": "Driver Commission", "fieldtype": "Data", "width": 140},
	{"fieldname": "supervisor_commission", "label": "Supervisor Commission", "fieldtype": "Data", "width": 150},
	{"fieldname": "supervisor", "label": "Supervisor", "fieldtype": "Link", "options": "Employee", "width": 140},
	{"fieldname": "truck", "label": "Truck", "fieldtype": "Link", "options": "Vehicle", "width": 120},
	{"fieldname": "latitude", "label": "Latitude", "fieldtype": "Data", "width": 110},
	{"fieldname": "longitude", "label": "Longitude", "fieldtype": "Data", "width": 110},
	{"fieldname": "notes", "label": "Notes", "fieldtype": "Small Text", "width": 220},
]


def execute(filters=None):
	rows = get_rows(
		"Pull Container",
		COLUMNS,
		filters or {},
		conditions=[["docstatus", "!=", 2]],
		order_by="`tabPull Container`.date desc, `tabPull Container`.name desc, `tabPull Container Item`.idx asc",
	)
	return get_columns(COLUMNS), rows
