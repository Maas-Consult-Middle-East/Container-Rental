import frappe


def execute():
	if frappe.db.exists("DocType", "Container Rent") and not frappe.db.exists("DocType", "Rent A Container"):
		# Renames the table and repoints Link/Dynamic Link fields, Custom Fields, reports and workspaces.
		frappe.rename_doc("DocType", "Container Rent", "Rent A Container", force=True)
