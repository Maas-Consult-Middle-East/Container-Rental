import frappe


def execute():
	"""Copy each rental's single container into the new Containers table."""
	if "container_number" not in frappe.db.get_table_columns("Rent A Container"):
		return
	rentals = frappe.db.sql(
		"""select rent.name, rent.docstatus, rent.container_number
		from `tabRent A Container` rent
		where ifnull(rent.container_number, '') != ''
			and not exists (
				select 1 from `tabRent A Container Item` item
				where item.parent = rent.name and item.parenttype = 'Rent A Container'
			)""",
		as_dict=True,
	)
	for rental in rentals:
		container = frappe.db.get_value(
			"Container", rental.container_number, ["container_size", "classification"], as_dict=True
		) or {}
		frappe.get_doc(
			{
				"doctype": "Rent A Container Item",
				"parent": rental.name,
				"parenttype": "Rent A Container",
				"parentfield": "containers",
				"idx": 1,
				"docstatus": rental.docstatus,
				"container": rental.container_number,
				"container_size": container.get("container_size"),
				"classification": container.get("classification"),
			}
		).db_insert()
	frappe.db.set_value("Custom Field", "Sales Invoice-container_rent", "label", "Rent A Container")
