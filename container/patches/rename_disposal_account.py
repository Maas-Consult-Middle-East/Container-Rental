"""Correct the disposal account name while preserving ledger links and numbers."""

import frappe
from erpnext.accounts.doctype.account.account import update_account_number

from container.setup import DISPOSAL_ACCOUNT_NAME


def execute():
	# Rename parent-company accounts first; ERPNext also updates their descendants.
	for company in frappe.get_all("Company", pluck="name", order_by="lft"):
		accounts = frappe.get_all(
			"Account",
			filters={"company": company, "account_name": "Gabage Disporsal Fee"},
			fields=["name", "account_number"],
		)
		for account in accounts:
			if frappe.db.exists("Account", {"company": company, "account_name": DISPOSAL_ACCOUNT_NAME}):
				frappe.throw(
					f"Both disposal account spellings exist in {company}. Resolve the duplicate accounts before migrating."
				)
			update_account_number(account.name, DISPOSAL_ACCOUNT_NAME, account.account_number)
