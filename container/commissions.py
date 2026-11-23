"""Signed rental commission amounts, derived from submitted credit notes.

Original operation amounts remain intact. Any submitted return reverses both rental
commissions in full, even for a partial credit, displaying the original amounts
as negative. Cancelling the last return restores the positive amounts.
No payment or general-ledger entry is created by this calculation.
"""

import frappe
from frappe.utils import flt
from container.invoice_sources import source_invoices


def reversed_rentals(rental_names):
	"""Internal helper for rental names already obtained through permission checks.

	Invoice visibility must not change commission entitlement. Read only the linkage
	and return a rental flag; invoice details remain permission-filtered by reports.
	"""
	if not rental_names:
		return set()
	invoices = source_invoices("container_rent", rental_names, submitted=True, ignore_permissions=True)
	if not invoices:
		return set()
	credited = set(frappe.get_all(
		"Sales Invoice",
		filters={"return_against": ["in", [invoice.name for invoice in invoices]],
			"is_return": 1, "docstatus": 1},
		pluck="return_against",
	))
	return {invoice.container_rent for invoice in invoices if invoice.name in credited}


def commission_amounts(amount, reversed):
	amount = flt(amount)
	return {
		"original_commission": amount,
		"commission_reversal": -amount if reversed else 0,
		"commission": -amount if reversed else amount,
	}
