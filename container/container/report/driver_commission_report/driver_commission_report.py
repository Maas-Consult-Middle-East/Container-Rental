"""Driver commission on each submitted rental, pull and emptying, with the rental's invoice and payments."""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

from container.container.report.container_report.container_report import linked_records
from container.container.report.supervisor_commission_report.supervisor_commission_report import (
	invoices_by_rental,
	payments_by_invoice,
)

# (operation doctype, its date field, the field holding the rental it belongs to)
OPERATIONS = (
	("Rent A Container", "from", "name"),
	("Pull Container", "date", "rent_a_container"),
	("Emptying Container", "emptying_date", None),
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if filters.from_date and filters.to_date and getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))
	operations = []
	for doctype, date_field, rental_field in OPERATIONS:
		if filters.operation and filters.operation != doctype:
			continue
		frappe.has_permission(doctype, "read", throw=True)
		conditions = [["docstatus", "=", 1], ["driver", "is", "set"]]
		if filters.driver:
			conditions.append(["driver", "=", filters.driver])
		if filters.reference:
			conditions.append(["name", "like", f"%{filters.reference}%"])
		if filters.from_date:
			conditions.append([date_field, ">=", getdate(filters.from_date)])
		if filters.to_date:
			conditions.append([date_field, "<", add_days(getdate(filters.to_date), 1)])
		fields = ["name", f"`tab{doctype}`.`{date_field}` as date", "driver", "driver_commission"]
		if rental_field:
			fields.append(f"`tab{doctype}`.`{rental_field}` as rent_a_container")
		for operation in frappe.get_list(doctype, filters=conditions, fields=fields, limit_page_length=0):
			operation.operation = doctype
			operations.append(operation)

	drivers = linked_records("Driver", [op.driver for op in operations], ["full_name"])
	invoices = invoices_by_rental(sorted({op.rent_a_container for op in operations if op.get("rent_a_container")}))
	payments = payments_by_invoice([invoice.name for invoice in invoices.values()])
	rows = []
	for op in operations:
		invoice = invoices.get(op.get("rent_a_container")) or {}
		rows.append({
			"date": op.date,
			"operation": op.operation,
			"reference": op.name,
			"driver": op.driver,
			"driver_name": drivers.get(op.driver, {}).get("full_name") or op.driver,
			"sales_invoice": invoice.get("name"),
			"invoice_status": _(invoice.get("status") or ""),
			"payment_entry": payments.get(invoice.get("name")),
			"commission": flt(op.driver_commission),
		})
	rows.sort(key=lambda row: (str(row["date"] or ""), row["reference"]), reverse=True)
	return get_columns(), rows


def get_columns():
	return [
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "operation", "label": _("Operation"), "fieldtype": "Link", "options": "DocType", "width": 160},
		{"fieldname": "reference", "label": _("Reference"), "fieldtype": "Dynamic Link", "options": "operation", "width": 140},
		{"fieldname": "driver", "label": _("Driver"), "fieldtype": "Link", "options": "Driver", "width": 150},
		{"fieldname": "driver_name", "label": _("Driver Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "sales_invoice", "label": _("Sales Invoice"), "fieldtype": "Link", "options": "Sales Invoice", "width": 170},
		{"fieldname": "invoice_status", "label": _("Invoice Status"), "fieldtype": "Data", "width": 130},
		{"fieldname": "payment_entry", "label": _("Payment Entry"), "fieldtype": "Data", "width": 200},
		{"fieldname": "commission", "label": _("Driver Commission"), "fieldtype": "Currency", "width": 160},
	]
