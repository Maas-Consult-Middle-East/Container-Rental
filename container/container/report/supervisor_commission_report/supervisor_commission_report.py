"""Supervisor commission on each submitted container rental, with its sales invoice and payments."""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

from container.container.report.container_report.container_report import linked_records


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if filters.from_date and filters.to_date and getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))
	frappe.has_permission("Rent A Container", "read", throw=True)
	conditions = [["docstatus", "=", 1], ["supervisor", "is", "set"]]
	for field in ("supervisor", "name"):
		if filters.get(field):
			conditions.append([field, "=", filters.get(field)])
	if filters.from_date:
		conditions.append(["from", ">=", getdate(filters.from_date)])
	if filters.to_date:
		conditions.append(["from", "<", add_days(getdate(filters.to_date), 1)])
	rentals = frappe.get_list(
		"Rent A Container",
		filters=conditions,
		fields=["name", "from", "supervisor", "supervisor_commission"],
		order_by="`tabRent A Container`.`from` desc, `tabRent A Container`.name desc",
		limit_page_length=0,
	)
	employees = linked_records("Employee", [r.supervisor for r in rentals], ["employee_name"])
	invoices = invoices_by_rental([r.name for r in rentals])
	payments = payments_by_invoice([invoice.name for invoice in invoices.values()])
	rows = [
		{
			"date": rental.get("from"),
			"rent_a_container": rental.name,
			"supervisor": rental.supervisor,
			"supervisor_name": employees.get(rental.supervisor, {}).get("employee_name") or rental.supervisor,
			"sales_invoice": invoices.get(rental.name, {}).get("name"),
			"invoice_status": _(invoices.get(rental.name, {}).get("status") or ""),
			"payment_entry": payments.get(invoices.get(rental.name, {}).get("name")),
			"commission": flt(rental.supervisor_commission),
		}
		for rental in rentals
	]
	return get_columns(), rows


def invoices_by_rental(rentals):
	"""The active (not cancelled, not return) invoice of each rental the user may read."""
	if not rentals or not frappe.has_permission("Sales Invoice", "read"):
		return {}
	return {
		invoice.container_rent: invoice
		for invoice in frappe.get_list(
			"Sales Invoice",
			filters={"container_rent": ["in", rentals], "docstatus": ["!=", 2], "is_return": 0},
			fields=["name", "container_rent", "status"],
			order_by="creation asc",
			limit_page_length=0,
		)
	}


def payments_by_invoice(invoices):
	"""Payment entries (not cancelled) against each invoice, joined in one cell for part payments."""
	if not invoices or not frappe.has_permission("Payment Entry", "read"):
		return {}
	grouped = {}
	for payment in frappe.get_list(
		"Payment Entry",
		filters=[
			["Payment Entry Reference", "reference_doctype", "=", "Sales Invoice"],
			["Payment Entry Reference", "reference_name", "in", invoices],
			["docstatus", "!=", 2],
		],
		fields=["name", "`tabPayment Entry Reference`.reference_name as invoice"],
		order_by="`tabPayment Entry`.posting_date asc, `tabPayment Entry`.name asc",
		limit_page_length=0,
	):
		names = grouped.setdefault(payment.invoice, [])
		if payment.name not in names:
			names.append(payment.name)
	return {invoice: ", ".join(names) for invoice, names in grouped.items()}


def get_columns():
	return [
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "rent_a_container", "label": _("Rent A Container"), "fieldtype": "Link", "options": "Rent A Container", "width": 150},
		{"fieldname": "supervisor", "label": _("Supervisor"), "fieldtype": "Link", "options": "Employee", "width": 140},
		{"fieldname": "supervisor_name", "label": _("Supervisor Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "sales_invoice", "label": _("Sales Invoice"), "fieldtype": "Link", "options": "Sales Invoice", "width": 170},
		{"fieldname": "invoice_status", "label": _("Invoice Status"), "fieldtype": "Data", "width": 130},
		{"fieldname": "payment_entry", "label": _("Payment Entry"), "fieldtype": "Data", "width": 200},
		{"fieldname": "commission", "label": _("Supervisor Commission"), "fieldtype": "Currency", "width": 170},
	]
