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
