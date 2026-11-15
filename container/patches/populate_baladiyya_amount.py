"""Preserve historical fees while replacing municipality selection with an amount."""

import frappe


def execute():
	for row in frappe.get_all(
		"Emptying Container",
		fields=["name", "baladiayya", "baladiyya_amount", "journal_entry"],
	):
		if row.baladiyya_amount:
			continue
		amount = None
		if row.journal_entry:
			# The posted amount is authoritative even if the municipality rate changed later.
			amount = frappe.db.get_value("Journal Entry", row.journal_entry, "total_debit")
		if amount is None and row.baladiayya:
			amount = frappe.db.get_value("Baladiyya", row.baladiayya, "rate")
		if amount is not None:
			frappe.db.set_value(
				"Emptying Container", row.name, "baladiyya_amount", amount, update_modified=False
			)
