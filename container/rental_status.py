"""Maintain overdue status for the current container rental."""

import frappe
from frappe.utils import add_days, getdate, today


def mark_late_containers():
	"""Mark rentals Late starting on day 11; pulled/empty containers are untouched."""
	cutoff = getdate(add_days(today(), -10))
	updated = 0
	for name in frappe.get_all("Container", filters={"status": "Rented"}, pluck="name"):
		# Pull creation takes the same lock, so it cannot be overwritten by this job.
		if frappe.db.get_value("Container", name, "status", for_update=True) != "Rented":
			continue
		# Use the latest submitted rental, never an old rental from a previous cycle.
		rentals = frappe.get_all(
			"Rent A Container",
			filters=[["Rent A Container Item", "container", "=", name], ["docstatus", "=", 1]],
			fields=["from"],
			order_by="`tabRent A Container`.creation desc, `tabRent A Container`.name desc",
			limit_page_length=1,
		)
		if rentals and rentals[0].get("from") and getdate(rentals[0].get("from")) < cutoff:
			frappe.db.set_value("Container", name, "status", "Late")
			updated += 1
	return updated
