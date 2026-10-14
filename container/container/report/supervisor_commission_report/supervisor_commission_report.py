"""Supervisor commissions earned on submitted container rentals."""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

from container.container.report.container_report.container_report import linked_records


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if filters.from_date and filters.to_date and getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))
	frappe.has_permission("Container Rent", "read", throw=True)
	conditions = [["docstatus", "=", 1], ["supervisor", "is", "set"]]
	if filters.supervisor:
		conditions.append(["supervisor", "=", filters.supervisor])
	if filters.from_date:
		conditions.append(["from", ">=", getdate(filters.from_date)])
	if filters.to_date:
		conditions.append(["from", "<", add_days(getdate(filters.to_date), 1)])
	rows = {}
	for rental in frappe.get_list(
		"Container Rent", filters=conditions,
		fields=["supervisor", "supervisor_commission"], limit_page_length=0,
	):
		row = rows.setdefault(rental.supervisor, {
			"supervisor": rental.supervisor, "total_commission": 0,
		})
		row["total_commission"] += flt(rental.supervisor_commission)
	employees = linked_records("Employee", rows, ["employee_name"])
	for supervisor, row in rows.items():
		row["supervisor_name"] = employees.get(supervisor, {}).get("employee_name") or supervisor
	return get_columns(), sorted(rows.values(), key=lambda row: (row["supervisor_name"], row["supervisor"]))


def get_columns():
	return [
		{"fieldname": "supervisor", "label": _("Supervisor"), "fieldtype": "Link", "options": "Employee", "width": 180},
		{"fieldname": "supervisor_name", "label": _("Supervisor Name"), "fieldtype": "Data", "width": 240},
		{"fieldname": "total_commission", "label": _("Total Rent Commission"), "fieldtype": "Currency", "width": 200},
	]
