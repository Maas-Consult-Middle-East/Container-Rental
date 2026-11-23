"""Keep existing invoice connections when source references move to item rows."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from container.setup import INVOICE_ITEM_SOURCE_FIELDS


def execute():
	create_custom_fields({"Sales Invoice Item": INVOICE_ITEM_SOURCE_FIELDS}, update=False)
	for field in ("container_rent", "container_contract"):
		frappe.db.sql(f"""
			UPDATE `tabSales Invoice Item` item
			JOIN `tabSales Invoice` invoice ON invoice.name = item.parent
			SET item.`{field}` = invoice.`{field}`
			WHERE item.parenttype = 'Sales Invoice' AND item.parentfield = 'items'
			AND COALESCE(invoice.`{field}`, '') != ''
			AND COALESCE(item.`{field}`, '') = ''
			AND NOT EXISTS (
				SELECT 1 FROM (SELECT parent, `{field}` FROM `tabSales Invoice Item`) existing
				WHERE existing.parent = invoice.name AND COALESCE(existing.`{field}`, '') != ''
			)
		""")
