"""Current availability across rental, pull, and emptying cycles."""

import frappe


def active_container_operations():
	"""Return active rental/pull sources, with pulls taking precedence over rentals."""
	# Rental submission updates modified; a draft may predate the previous emptying.
	# Pulls become active on insertion, so their creation timestamp starts the operation.
	operations = frappe.db.sql(
		"""
		select distinct item.container, rental.name as source_name, 'rental' as operation
		from `tabRent A Container Item` item
		inner join `tabRent A Container` rental on rental.name = item.parent
		where item.parenttype = 'Rent A Container' and rental.docstatus = 1
		and not exists (
			select 1 from `tabEmptying Container` emptying
			where emptying.container = item.container and emptying.docstatus != 2
			and emptying.creation > rental.modified
		)
		union
		select distinct item.container, pull.name as source_name, 'pull' as operation
		from `tabPull Container Item` item
		inner join `tabPull Container` pull on pull.name = item.parent
		where item.parenttype = 'Pull Container' and pull.docstatus != 2
		and not exists (
			select 1 from `tabEmptying Container` emptying
			where emptying.container = item.container and emptying.docstatus != 2
			and emptying.creation > pull.creation
		)
		""",
		as_dict=True,
	)
	pulled = {row.container for row in operations if row.operation == "pull"}
	return [row for row in operations if row.operation == "pull" or row.container not in pulled]


def available_container_filters():
	"""Exclude the same active containers counted by the rented and pull cards."""
	blocked = sorted({row.container for row in active_container_operations()})
	return [["name", "not in", blocked]] if blocked else []
