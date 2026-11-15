"""Current availability across rental, pull, and emptying cycles."""

import frappe


def available_container_filters():
	"""Exclude submitted rentals and saved pulls not followed by an emptying."""
	# Rental submission updates modified; a draft may predate the previous emptying.
	# Pulls become active on insertion, so their creation timestamp starts the operation.
	blocked = frappe.db.sql(
		"""
		select distinct item.container
		from `tabRent A Container Item` item
		inner join `tabRent A Container` rental on rental.name = item.parent
		where item.parenttype = 'Rent A Container' and rental.docstatus = 1
		and not exists (
			select 1 from `tabEmptying Container` emptying
			where emptying.container = item.container and emptying.docstatus != 2
			and emptying.creation > rental.modified
		)
		union
		select distinct item.container
		from `tabPull Container Item` item
		inner join `tabPull Container` pull on pull.name = item.parent
		where item.parenttype = 'Pull Container' and pull.docstatus != 2
		and not exists (
			select 1 from `tabEmptying Container` emptying
			where emptying.container = item.container and emptying.docstatus != 2
			and emptying.creation > pull.creation
		)
		""",
		pluck=True,
	)
	return [["name", "not in", blocked]] if blocked else []
