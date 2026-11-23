"""Remove obsolete master definitions after all replacement fields are synced."""

import frappe

from container.patches.convert_classification_to_select import FIELDS


def execute():
	for doctype, fieldname in FIELDS.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		field = frappe.get_meta(doctype, cached=False).get_field(fieldname)
		if not field or field.fieldtype != "Select" or field.options.split() != ["12", "20"]:
			frappe.throw(f"Sync the classification Select field on {doctype} before removing masters.")
		for row in frappe.get_all(doctype, fields=["name", fieldname]):
			if row.get(fieldname) not in (None, "", "12", "20"):
				frappe.throw(f"Unconverted classification on {doctype} {row.name}; masters were not removed.")
	for name in ("Classifcation Sizes", "Classification", "Classification Type"):
		if frappe.db.exists("DocType", name):
			frappe.delete_doc("DocType", name, ignore_permissions=True)
	frappe.clear_cache()
