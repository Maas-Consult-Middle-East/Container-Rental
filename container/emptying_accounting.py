"""Post the selected municipality fee against the driver's petty cash."""
from math import isfinite

import frappe
from frappe import _
from frappe.utils import flt, today

from container.setup import ensure_disposal_account


def create_disposal_journal(emptying):
	if emptying.docstatus != 1:
		frappe.throw(_("Submit the Emptying Container before posting the disposal fee."))
	frappe.db.get_value("Emptying Container", emptying.name, "name", for_update=True)
	existing = frappe.db.get_value("Journal Entry", {"container_emptying": emptying.name, "docstatus": ["!=", 2]}, ["name", "docstatus"], as_dict=True)
	if existing:
		if existing.docstatus != 1:
			frappe.throw(_("A draft Journal Entry already exists for this emptying. Resolve it before submitting."))
		return existing.name
	if not emptying.driver or not emptying.baladiayya:
		frappe.throw(_("Select a Driver and Baladiyya before submitting."))
	petty_cash = frappe.db.get_value("Driver", emptying.driver, "custom_petty_cash_account")
	if not petty_cash:
		frappe.throw(_("Set the Petty Cash Account on Driver {0} before submitting.").format(emptying.driver))
	credit = frappe.get_doc("Account", petty_cash)
	company = frappe.get_doc("Company", credit.company)
	municipality = frappe.get_doc("Baladiyya", emptying.baladiayya)
	amount = flt(municipality.rate)
	if municipality.docstatus == 2 or not isfinite(amount) or amount <= 0:
		frappe.throw(_("Select an active Baladiyya with a Rate greater than zero."))
	if credit.is_group or credit.disabled or credit.root_type != "Asset" or credit.account_type in ("Receivable", "Payable"):
		frappe.throw(_("The driver's Petty Cash Account must be an enabled, non-group asset account, not a receivable/payable account."))
	if credit.account_currency != company.default_currency:
		frappe.throw(_("The driver's Petty Cash Account must use the company currency for Baladiyya fees."))
	debit_name = ensure_disposal_account(company.name)
	if not debit_name:
		frappe.throw(_("Set up the company's expense chart of accounts before submitting."))
	debit = frappe.get_doc("Account", debit_name)
	if debit.is_group or debit.disabled or debit.root_type != "Expense" or debit.account_currency != company.default_currency:
		frappe.throw(_("Garbage Disposal Fee must be an enabled expense ledger in the company currency."))
	if not company.cost_center:
		frappe.throw(_("Set the company's default Cost Center before submitting."))
	journal = frappe.new_doc("Journal Entry")
	journal.update({
		"voucher_type": "Journal Entry", "company": company.name,
		"posting_date": emptying.emptying_date or today(),
		"container_emptying": emptying.name,
		"user_remark": _("Baladiyya fee for {0}; Driver {1}; Emptying Container {2}").format(municipality.name, emptying.driver, emptying.name),
	})
	journal.append("accounts", {"account": debit_name, "debit_in_account_currency": amount, "cost_center": company.cost_center})
	journal.append("accounts", {"account": petty_cash, "credit_in_account_currency": amount})
	journal.insert()
	journal.submit()
	return journal.name
