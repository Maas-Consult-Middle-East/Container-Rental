"""Every container on a submitted rental."""

import frappe
from frappe.utils import flt

from container.container.report.container_report.container_report import linked_records
from container.container.report.list_report import get_columns, get_rows
from container.commissions import commission_amounts, reversed_rentals
from container.invoice_sources import source_invoices

COLUMNS = [
	{"fieldname": "name", "label": "Rent ID", "fieldtype": "Link", "options": "Rent A Container", "width": 130},
	{"fieldname": "container", "label": "Container", "fieldtype": "Link", "options": "Container", "width": 130, "table": "Rent A Container Item"},
	{"fieldname": "container_size", "label": "Container Size", "fieldtype": "Data", "width": 120, "table": "Rent A Container Item"},
	{"fieldname": "rent_type", "label": "Rent Type", "fieldtype": "Link", "options": "Rent Type", "width": 120},
	{"fieldname": "classification", "label": "Classification", "fieldtype": "Select", "options": "\n12\n20", "width": 140},
	{"fieldname": "client", "label": "Client", "fieldtype": "Link", "options": "Customer", "width": 180},
	{"fieldname": "contact_number", "label": "Contact Number", "fieldtype": "Data", "width": 140},
	{"fieldname": "cr_number", "label": "CR Number", "fieldtype": "Data", "width": 120},
	{"fieldname": "address", "label": "Address", "fieldtype": "Data", "width": 200},
	{"fieldname": "from", "label": "From", "fieldtype": "Date", "width": 110},
	{"fieldname": "to", "label": "To", "fieldtype": "Date", "width": 110},
	{"fieldname": "cost", "label": "Cost", "fieldtype": "Data", "width": 100},
	{"fieldname": "container_contract", "label": "Container Contract", "fieldtype": "Link", "options": "Container Contract", "width": 150},
	{"fieldname": "supervisor", "label": "Supervisor", "fieldtype": "Link", "options": "Employee", "width": 140},
	{"fieldname": "supervisor_commission", "label": "Original Supervisor Commission", "fieldtype": "Data", "width": 210},
	{"fieldname": "driver", "label": "Driver", "fieldtype": "Link", "options": "Driver", "width": 140},
	{"fieldname": "driver_commission", "label": "Original Driver Commission", "fieldtype": "Data", "width": 190},
	{"fieldname": "truck", "label": "Truck", "fieldtype": "Link", "options": "Vehicle", "width": 120},
	{"fieldname": "latitude", "label": "Latitude", "fieldtype": "Data", "width": 110},
	{"fieldname": "longitude", "label": "Longitude", "fieldtype": "Data", "width": 110},
]

EXTRA_COLUMNS = [
	{"fieldname": "current_status", "label": "Current Status", "fieldtype": "Data", "width": 130},
	{"fieldname": "invoice_no", "label": "Invoice No", "fieldtype": "Link", "options": "Sales Invoice", "width": 170},
	{"fieldname": "payment_status", "label": "Payment Status", "fieldtype": "Data", "width": 160},
	{"fieldname": "has_credit_note", "label": "Credit Note", "fieldtype": "Data", "width": 110},
	{"fieldname": "credit_notes", "label": "Credit Notes", "fieldtype": "Data", "width": 220},
	{"fieldname": "credited_amount", "label": "Credited Amount", "fieldtype": "Currency", "options": "invoice_currency", "width": 150},
	{"fieldname": "invoice_currency", "label": "Invoice Currency", "fieldtype": "Link", "options": "Currency", "hidden": 1},
	{"fieldname": "net_driver_commission", "label": "Driver Commission", "fieldtype": "Currency", "width": 180},
	{"fieldname": "net_supervisor_commission", "label": "Supervisor Commission", "fieldtype": "Currency", "width": 200},
]


def execute(filters=None):
	filters = filters or {}
	rows = get_rows(
		"Rent A Container",
		COLUMNS,
		filters or {},
		conditions=[["docstatus", "=", 1]],
		order_by="`tabRent A Container`.`from` desc, `tabRent A Container`.name desc, `tabRent A Container Item`.idx asc",
	)
	containers = linked_records("Container", [row.container for row in rows], ["status"])
	supervisors = linked_records("Employee", [row.get("supervisor") for row in rows], ["employee_name"])
	drivers = linked_records("Driver", [row.get("driver") for row in rows], ["full_name"])
	invoices = {}
	can_read_invoices = frappe.has_permission("Sales Invoice", "read")
	if rows and can_read_invoices:
		for invoice in source_invoices("container_rent", [row.name for row in rows], ["status", "currency"]):
			invoices.setdefault(invoice.container_rent, []).append(invoice)
	credits = credit_notes_by_invoice([invoice.name for group in invoices.values() for invoice in group])
	reversed = reversed_rentals([row.name for row in rows])
	result = []
	for row in rows:
		status = containers.get(row.container, {}).get("status")
		status = "Pulled" if status == "Pull" else status
		# Normally one invoice per rental. Preserve every readable invoice if there are several.
		for invoice in invoices.get(row.name) or [None]:
			invoice_credits = credits.get(invoice.name, []) if invoice else []
			enriched = frappe._dict(row)
			for person in ("driver", "supervisor"):
				amounts = commission_amounts(row.get(f"{person}_commission"), row.name in reversed)
				enriched[f"net_{person}_commission"] = amounts["commission"]
			enriched.update({
				"supervisor_name": supervisors.get(row.get("supervisor"), {}).get("employee_name"),
				"driver_name": drivers.get(row.get("driver"), {}).get("full_name"),
				"current_status": status,
				"invoice_no": invoice.name if invoice else None,
				"invoice_currency": invoice.get("currency") if invoice else None,
				"credit_notes": ", ".join(credit.name for credit in invoice_credits),
				"has_credit_note": ("Yes" if invoice_credits else "No") if can_read_invoices else "Not Available",
				"credited_amount": -sum(flt(credit.grand_total) for credit in invoice_credits),
				"payment_status": invoice.status if invoice else (
					"No Invoice Found" if can_read_invoices else "Not Available"
				),
			})
			if filters.get("credit_note") and filters["credit_note"] not in {credit.name for credit in invoice_credits}:
				continue
			if all(not filters.get(field) or enriched.get(field) == filters[field]
				for field in ("current_status", "invoice_no", "payment_status", "has_credit_note")):
				result.append(enriched)
	columns = [
		{"fieldname": f"{column['fieldname']}_name", "label": column["label"], "fieldtype": "Data", "width": 180}
		if column["fieldname"] in ("supervisor", "driver") else column
		for column in COLUMNS[:2] + EXTRA_COLUMNS + COLUMNS[2:]
		if column["fieldname"] not in ("driver_commission", "supervisor_commission")
	]
	return get_columns(columns), result


def credit_notes_by_invoice(invoice_names):
	"""Submitted returns against readable invoices; drafts/cancellations have no effect."""
	if not invoice_names or not frappe.has_permission("Sales Invoice", "read"):
		return {}
	credits = {}
	for credit in frappe.get_list(
		"Sales Invoice",
		filters={"return_against": ["in", invoice_names], "is_return": 1, "docstatus": 1},
		fields=["name", "return_against", "grand_total"],
		order_by="posting_date asc, creation asc, name asc",
		limit_page_length=0,
	):
		credits.setdefault(credit.return_against, []).append(credit)
	return credits
