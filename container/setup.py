"""Additive and repeatable installation. Never rewrites existing business records."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_migrate():
	for role in ["Container Manager", "Container Operator", "Container Reports User"]:
		if not frappe.db.exists("Role", role):
			frappe.get_doc(dict(doctype="Role", role_name=role, desk_access=1)).insert()
	for name in ["Rubble", "Trash", "Unlimited Contract"]:
		if not frappe.db.exists("Contract Type", name):
			frappe.get_doc(dict(doctype="Contract Type", name=name, contract_type=name)).insert()
	fields = {
		"Purchase Invoice": [
			dict(
				fieldname="container_truck",
				label="Truck",
				fieldtype="Link",
				options="Vehicle",
				insert_after="supplier",
			)
		],
		"Sales Invoice": [
			dict(
				fieldname="container_rent",
				label="Container Rent",
				fieldtype="Link",
				options="Container Rent",
				insert_after="customer",
				read_only=1,
				no_copy=1,
			),
			dict(
				fieldname="container_contract",
				label="Container Contract",
				fieldtype="Link",
				options="Container Contract",
				insert_after="customer",
				no_copy=1,
			)
		],
		"Vehicle": [
			dict(
				fieldname="container_truck_type", label="Truck Type", fieldtype="Data", insert_after="model"
			),
			dict(
				fieldname="container_driver",
				label="Driver",
				fieldtype="Link",
				options="Driver",
				insert_after="container_truck_type",
			),
			dict(
				fieldname="container_status",
				label="Fleet Status",
				fieldtype="Select",
				options="Active\nMaintenance\nInactive",
				default="Active",
				insert_after="container_driver",
			),
			dict(
				fieldname="container_registration_expiry",
				label="Registration Expiry",
				fieldtype="Date",
				insert_after="container_status",
			),
		],
	}
	# Existing equivalent standard insurance end date and license plate are reused.
	create_custom_fields(fields, update=False)

	from container.permissions import sync_full_access_permissions

	sync_full_access_permissions()
	setup_emptying_accounting()


DISPOSAL_ACCOUNT_NAME = "Gabage Disporsal Fee"


def ensure_disposal_account(company):
	"""Create a company-specific expense ledger, without duplicating existing accounts."""
	existing = frappe.db.get_value("Account", {"company": company, "account_name": DISPOSAL_ACCOUNT_NAME}, "name")
	if existing:
		return existing
	parent = frappe.db.get_value(
		"Account", {"company": company, "root_type": "Expense", "is_group": 1, "parent_account": ["is", "not set"]}, "name"
	)
	if not parent:
		return None  # The company may not have a chart of accounts yet.
	account = frappe.get_doc({
		"doctype": "Account", "account_name": DISPOSAL_ACCOUNT_NAME,
		"company": company, "parent_account": parent, "is_group": 0,
		"account_currency": frappe.get_cached_value("Company", company, "default_currency"),
	})
	account.insert(ignore_permissions=True)
	return account.name


def setup_company_disposal_account(doc, method=None):
	ensure_disposal_account(doc.name)


def setup_emptying_accounting():
	create_custom_fields({
		"Driver": [{"fieldname": "custom_petty_cash_account", "label": "Petty Cash Account",
			"fieldtype": "Link", "options": "Account", "insert_after": "address"}],
		"Journal Entry": [{"fieldname": "container_emptying", "label": "Emptying Container",
			"fieldtype": "Link", "options": "Emptying Container", "insert_after": "user_remark",
			"read_only": 1, "no_copy": 1}],
	}, update=False)
	for company in frappe.get_all("Company", pluck="name"):
		ensure_disposal_account(company)
