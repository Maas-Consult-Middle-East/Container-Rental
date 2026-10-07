"""Permission policy for Container app DocTypes."""

import frappe
from frappe.permissions import setup_custom_perms


CONTAINER_FULL_ACCESS_ROLES = (
	"System Manager",
	"Container Manager",
	"Container Operator",
	"Container Reports User",
	"Accounts User",
	"Accounts Manager",
	"Fleet Manager",
)

BASE_ACCESS = {
	"read": 1,
	"write": 1,
	"create": 1,
	"delete": 1,
	"report": 1,
	"export": 1,
	"import": 1,
	"share": 1,
	"print": 1,
	"email": 1,
	"select": 1,
}
SUBMIT_ACCESS = {"submit": 1, "cancel": 1, "amend": 1}


def has_container_full_access():
	return frappe.session.user == "Administrator" or bool(
		set(CONTAINER_FULL_ACCESS_ROLES) & set(frappe.get_roles())
	)


def sync_full_access_permissions():
	"""Apply full access even when Role Permission Manager overrides already exist."""
	for row in frappe.get_all(
		"DocType",
		filters={"module": "Container", "istable": 0},
		fields=["name", "is_submittable"],
	):
		setup_custom_perms(row.name)
		levels = {0}
		levels.update(
			int(field.permlevel)
			for field in frappe.get_meta(row.name).fields
			if field.permlevel
		)
		for level in levels:
			for role in CONTAINER_FULL_ACCESS_ROLES:
				values = {"read": 1, "write": 1}
				if level == 0:
					values.update(BASE_ACCESS)
					if row.is_submittable:
						values.update(SUBMIT_ACCESS)
				name = frappe.db.get_value(
					"Custom DocPerm",
					{"parent": row.name, "role": role, "permlevel": level, "if_owner": 0},
				)
				if name:
					frappe.db.set_value("Custom DocPerm", name, values, update_modified=False)
				else:
					frappe.get_doc(
						{
							"doctype": "Custom DocPerm",
							"parent": row.name,
							"parenttype": "DocType",
							"parentfield": "permissions",
							"role": role,
							"permlevel": level,
							**values,
						}
					).insert(ignore_permissions=True)
		frappe.clear_cache(doctype=row.name)
