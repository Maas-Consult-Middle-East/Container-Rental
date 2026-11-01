"""Every container on a submitted rental."""

from container.container.report.list_report import get_columns, get_rows

COLUMNS = [
	{"fieldname": "name", "label": "Rent ID", "fieldtype": "Link", "options": "Rent A Container", "width": 130},
	{"fieldname": "container", "label": "Container", "fieldtype": "Link", "options": "Container", "width": 130, "table": "Rent A Container Item"},
	{"fieldname": "container_size", "label": "Container Size", "fieldtype": "Data", "width": 120, "table": "Rent A Container Item"},
	{"fieldname": "rent_type", "label": "Rent Type", "fieldtype": "Link", "options": "Rent Type", "width": 120},
	{"fieldname": "classification", "label": "Classification", "fieldtype": "Link", "options": "Classification", "width": 140},
	{"fieldname": "client", "label": "Client", "fieldtype": "Link", "options": "Customer", "width": 180},
	{"fieldname": "contact_number", "label": "Contact Number", "fieldtype": "Data", "width": 140},
	{"fieldname": "cr_number", "label": "CR Number", "fieldtype": "Data", "width": 120},
	{"fieldname": "address", "label": "Address", "fieldtype": "Data", "width": 200},
	{"fieldname": "from", "label": "From", "fieldtype": "Date", "width": 110},
	{"fieldname": "to", "label": "To", "fieldtype": "Date", "width": 110},
	{"fieldname": "cost", "label": "Cost", "fieldtype": "Data", "width": 100},
	{"fieldname": "container_contract", "label": "Container Contract", "fieldtype": "Link", "options": "Container Contract", "width": 150},
	{"fieldname": "supervisor", "label": "Supervisor", "fieldtype": "Link", "options": "Employee", "width": 140},
	{"fieldname": "supervisor_commission", "label": "Supervisor Commission", "fieldtype": "Data", "width": 150},
	{"fieldname": "driver", "label": "Driver", "fieldtype": "Link", "options": "Driver", "width": 140},
	{"fieldname": "driver_commission", "label": "Driver Commission", "fieldtype": "Data", "width": 140},
	{"fieldname": "truck", "label": "Truck", "fieldtype": "Link", "options": "Vehicle", "width": 120},
	{"fieldname": "latitude", "label": "Latitude", "fieldtype": "Data", "width": 110},
	{"fieldname": "longitude", "label": "Longitude", "fieldtype": "Data", "width": 110},
]


def execute(filters=None):
	rows = get_rows(
		"Rent A Container",
		COLUMNS,
		filters or {},
		conditions=[["docstatus", "=", 1]],
		order_by="`tabRent A Container`.`from` desc, `tabRent A Container`.name desc, `tabRent A Container Item`.idx asc",
	)
	return get_columns(COLUMNS), rows
