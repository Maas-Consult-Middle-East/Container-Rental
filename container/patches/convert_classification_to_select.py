"""Validate all legacy values before converting classification links to sizes."""

import re

import frappe

REMOVED_DOCTYPES = ("Classification", "Classification Type", "Classifcation Sizes")
FIELDS = {
	"Container": "classification",
	"Rent A Container": "classification",
	"Rent A Container Item": "classification",
	"Pull Container": "classification",
	"Pull Container Item": "classification",
	"Container Contract": "classification",
	"Container Replacement": "new_container_classification",
	"Contract Container": "container_type",
}


def normalize_size(value):
	text = str(value or "").strip().translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
	if not text:
		return ""
	match = re.fullmatch(r"(12|20)(?:\s*(?:yards?|yd|ياردة|يارد|ياردات))?", text, re.IGNORECASE)
	return match.group(1) if match else None


def execute():
	# Unmanaged site customizations must be resolved before removing their targets.
	for dt, parent_field in (("DocField", "parent"), ("Custom Field", "dt")):
		for field in frappe.get_all(dt, filters={"options": ["in", REMOVED_DOCTYPES]},
			fields=[parent_field, "fieldname"]):
			parent = field.get(parent_field)
			if parent not in REMOVED_DOCTYPES and (dt == "Custom Field" or FIELDS.get(parent) != field.fieldname):
				frappe.throw(f"Resolve classification reference {parent}.{field.fieldname} before migration.")
	for prop in frappe.get_all("Property Setter", filters={"doc_type": ["in", list(FIELDS)],
		"property": ["in", ["fieldtype", "options", "fetch_from"]]},
		fields=["doc_type", "field_name"]):
		if FIELDS[prop.doc_type] == prop.field_name:
			frappe.throw(f"Remove the classification Property Setter on {prop.doc_type}.{prop.field_name} before migration.")

	mapping = {}
	if frappe.db.exists("DocType", "Classification"):
		for row in frappe.get_all("Classification", fields=["name", "classification_name"]):
			mapping[row.name] = normalize_size(row.classification_name) or normalize_size(row.name)
	updates = []
	invalid = []
	for doctype, fieldname in FIELDS.items():
		if not frappe.db.table_exists(doctype) or not frappe.db.has_column(doctype, fieldname):
			continue
		for row in frappe.get_all(doctype, fields=["name", fieldname]):
			old = row.get(fieldname)
			new = mapping.get(old) if old in mapping else normalize_size(old)
			if new is None:
				invalid.append(f"{doctype} {row.name}: {old}")
			elif old and old != new:
				updates.append((doctype, row.name, fieldname, new))
	if invalid:
		frappe.throw("Map these classification values to 12 or 20 before migration: " + "; ".join(invalid))
	for doctype, name, fieldname, value in updates:
		frappe.db.set_value(doctype, name, fieldname, value, update_modified=False)
