"""Use ERPNext's invoice controller for all tax and outstanding calculations."""

import frappe
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from frappe import _
from frappe.utils import flt


def invoice_preview(contract):
	invoice = frappe.new_doc("Sales Invoice")
	invoice.customer = contract.customer
	invoice.company = contract.company
	invoice.currency = contract.currency
	invoice.container_contract = contract.name if not contract.is_new() else None
	if contract.contract_type == "Unlimited Contract":
		lines = [(1, flt(contract.unlimited_billing_amount))]
	elif contract.containers:
		lines = [(row.no_of_trips, row.rate) for row in contract.containers if row.no_of_trips]
	else:
		lines = [(contract.no_of_trips, contract.price)]
	for qty, rate in lines:
		invoice.append(
			"items",
			dict(
				item_code=contract.rental_item,
				qty=qty,
				rate=rate,
				item_tax_template=contract.tax_template or None,
			),
		)
	exempt = contract.tax_treatment in ("Exempt", "Exempt from tax")
	if not exempt:
		if not contract.sales_tax_template:
			frappe.throw(_("A Sales Taxes and Charges Template is required"))
		template = frappe.get_doc("Sales Taxes and Charges Template", contract.sales_tax_template)
		template.check_permission("read")
		if template.company != contract.company:
			frappe.throw(_("Tax template company must match the contract"))
		invoice.taxes_and_charges = template.name
		for row in get_taxes_and_charges("Sales Taxes and Charges Template", template.name):
			row["included_in_print_rate"] = int(
				contract.tax_treatment in ("Price Includes Tax", "Price include tax")
			)
			invoice.append("taxes", row)
	invoice.set_missing_values()
	# ERPNext may populate default taxes; exemption must remain explicit.
	if exempt:
		invoice.set("taxes", [])
		invoice.taxes_and_charges = None
		for item in invoice.items:
			item.item_tax_template = None
			item.item_tax_rate = "{}"
	invoice.calculate_taxes_and_totals()
	return invoice


@frappe.whitelist()
def make_invoice(contract):
	doc = frappe.get_doc("Container Contract", contract)
	doc.check_permission("read")
	if not frappe.has_permission("Sales Invoice", "create"):
		raise frappe.PermissionError
	if doc.docstatus != 1 or doc.status != "Active":
		frappe.throw(_("An active contract is required"))
	if not doc.rental_item:
		frappe.throw(_("Select a rental Item on the contract before invoicing"))
	frappe.db.get_value("Container Contract", doc.name, "name", for_update=True)
	if doc.contract_type != "Unlimited Contract" and frappe.db.exists(
		"Sales Invoice", {"container_contract": doc.name, "docstatus": ["!=", 2], "is_return": 0}
	):
		frappe.throw(_("An invoice already exists for this fixed-trip contract"))
	invoice = invoice_preview(doc)
	if not invoice.items or flt(invoice.grand_total) <= 0:
		frappe.throw(_("Invoice amount must be positive"))
	invoice.insert()
	return invoice.name


def validate_invoice(doc, method=None):
	if not doc.get("container_contract"):
		return
	contract = frappe.get_doc("Container Contract", doc.container_contract)
	if (
		contract.docstatus != 1
		or doc.customer != contract.customer
		or doc.company != contract.company
		or doc.currency != contract.currency
	):
		frappe.throw(_("Invoice customer, company and currency must match the submitted container contract"))


def prevent_accounting_cancel(doc, method=None):
	target, field = (
		("Commission Entry", "invoice")
		if doc.doctype == "Sales Invoice"
		else ("Client Withdrawal", "payment_entry")
	)
	if frappe.db.exists(target, {field: doc.name, "docstatus": 1}):
		frappe.throw(_("Cancel linked {0} records first").format(target))
