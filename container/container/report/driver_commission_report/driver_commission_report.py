"""Driver commissions from submitted container operations."""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

from container.container.report.container_report.container_report import linked_records


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if filters.from_date and filters.to_date and getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))
	rows = {}
	for doctype, date_field, column in (
		("Pull Container", "date", "pull_commission"),
		("Container Rent", "from", "rent_commission"),
		("Emptying Container", "emptying_date", "emptying_commission"),
	):
		frappe.has_permission(doctype, "read", throw=True)
		conditions = [["docstatus", "=", 1], ["driver", "is", "set"]]
		if filters.driver:
			conditions.append(["driver", "=", filters.driver])
		if filters.from_date:
			conditions.append([date_field, ">=", getdate(filters.from_date)])
		if filters.to_date:
			conditions.append([date_field, "<", add_days(getdate(filters.to_date), 1)])
		for operation in frappe.get_list(
			doctype, filters=conditions, fields=["driver", "driver_commission"], limit_page_length=0
		):
			row = rows.setdefault(operation.driver, {
				"driver": operation.driver, "pull_commission": 0,
				"rent_commission": 0, "emptying_commission": 0,
			})
			row[column] += flt(operation.driver_commission)
	drivers = linked_records("Driver", rows, ["full_name"])
	for driver, row in rows.items():
		row["driver_name"] = drivers.get(driver, {}).get("full_name") or driver
		row["total_commission"] = sum(row[key] for key in (
			"pull_commission", "rent_commission", "emptying_commission"
		))
	return get_columns(), sorted(rows.values(), key=lambda row: (row["driver_name"], row["driver"]))


def get_columns():
	return [
		{"fieldname": "driver", "label": _("Driver"), "fieldtype": "Link", "options": "Driver", "width": 160},
		{"fieldname": "driver_name", "label": _("Driver Name"), "fieldtype": "Data", "width": 220},
		*[
			{"fieldname": field, "label": _(label), "fieldtype": "Currency", "width": 190}
			for field, label in (
				("pull_commission", "Pull Commission"),
				("rent_commission", "Rent Commission"),
				("emptying_commission", "Emptying Commission"),
				("total_commission", "Total Commission"),
			)
		],
	]
