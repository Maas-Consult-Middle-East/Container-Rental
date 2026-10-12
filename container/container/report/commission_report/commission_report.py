"""Commission summary report column definitions."""

from frappe import _


def get_columns():
	return [
		{
			"fieldname": "person_name",
			"label": _("Driver Name / Supervisor"),
			"fieldtype": "Data",
			"width": 240,
		},
		*[
			{
				"fieldname": fieldname,
				"label": _(label),
				"fieldtype": "Currency",
				"width": width,
			}
			for fieldname, label, width in [
				("cash_commissions", "Sum of Cash Commissions", 190),
				("contract_commissions", "Sum of Contracts Commissions", 210),
				("emptying_commissions", "Emptying", 130),
				("pull_commissions", "Pull", 130),
				("other_commissions", "Other Commissions", 160),
				("total_commissions", "Sum of All", 150),
				("unpaid_commissions", "Sum of Unpaid", 150),
			]
		],
	]


def get_operation_commissions(filters=None):
	"""Read the confirmed emptying/pull sources using the current user's permissions."""
	import frappe
	from frappe.utils import flt, getdate

	filters = frappe._dict(filters or {})
	if filters.person_type not in (None, "", "Driver", "Employee"):
		frappe.throw(_("Select Driver or Employee for the person type."))
	if filters.person and not filters.person_type:
		frappe.throw(_("Select a person type before selecting a person."))
	if filters.from_date and filters.to_date and getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))

	rows = {}
	for doctype, column in (
		("Emptying Container", "emptying_commissions"),
		("Pull Container", "pull_commissions"),
	):
		# Do not silently present partial totals when a source is inaccessible.
		frappe.has_permission(doctype, "read", throw=True)
		conditions = [["docstatus", "=", 1]]
		if filters.from_date:
			conditions.append(["emptying_date", ">=", getdate(filters.from_date)])
		if filters.to_date:
			conditions.append(["emptying_date", "<=", getdate(filters.to_date)])
		if filters.person:
			field = "driver" if filters.person_type == "Driver" else "supervisor"
			conditions.append([field, "=", filters.person])
		operations = frappe.get_list(
			doctype,
			filters=conditions,
			fields=["driver", "supervisor", "driver_commission", "supervisor_commission"],
			limit_page_length=0,
		)
		for operation in operations:
			for field, person_type in (("driver", "Driver"), ("supervisor", "Employee")):
				person = operation.get(field)
				if not person or (filters.person_type and filters.person_type != person_type):
					continue
				if filters.person and person != filters.person:
					continue
				key = (person_type, person)
				row = rows.setdefault(
					key,
					{
						"person_type": person_type,
						"person": person,
						"contract_commissions": 0,
						"emptying_commissions": 0,
						"pull_commissions": 0,
					},
				)
				row[column] += flt(operation.get(f"{field}_commission"))
	return list(rows.values())
