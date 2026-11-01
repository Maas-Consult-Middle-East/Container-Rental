import frappe


def execute():
	"""Copy each pull's single container into the new Containers table."""
	if "container" not in frappe.db.get_table_columns("Pull Container"):
		return
	pulls = frappe.db.sql(
		"""select pull.name, pull.docstatus, pull.container
		from `tabPull Container` pull
		where ifnull(pull.container, '') != ''
			and not exists (
				select 1 from `tabPull Container Item` item
				where item.parent = pull.name and item.parenttype = 'Pull Container'
			)""",
		as_dict=True,
	)
	for pull in pulls:
		container = frappe.db.get_value(
			"Container", pull.container, ["container_size", "classification"], as_dict=True
		) or {}
		frappe.get_doc(
			{
				"doctype": "Pull Container Item",
				"parent": pull.name,
				"parenttype": "Pull Container",
				"parentfield": "containers",
				"idx": 1,
				"docstatus": pull.docstatus,
				"container": pull.container,
				"container_size": container.get("container_size"),
				"classification": container.get("classification"),
			}
		).db_insert()
