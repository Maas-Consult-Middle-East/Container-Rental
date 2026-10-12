import frappe


def execute():
	old_doctype = frappe.db.exists("DocType", "Cotainer Rent")
	new_doctype = frappe.db.exists("DocType", "Container Rent")
	old_table = frappe.db.table_exists("Cotainer Rent")
	new_table = frappe.db.table_exists("Container Rent")

	# A previously deleted Container Rent DocType can leave an empty table behind.
	if old_doctype and not new_doctype and new_table:
		if frappe.db.count("Container Rent"):
			frappe.throw("Cannot rename Cotainer Rent because Container Rent already contains records")
		frappe.db.sql_ddl("DROP TABLE `tabContainer Rent`")
		new_table = False

	if old_doctype and not new_doctype:
		frappe.rename_doc("DocType", "Cotainer Rent", "Container Rent", force=True)
		old_table = frappe.db.table_exists("Cotainer Rent")
		new_table = frappe.db.table_exists("Container Rent")

	# Recover safely if an earlier rename changed the DocType before its table.
	if frappe.db.exists("DocType", "Container Rent") and old_table:
		if not new_table:
			frappe.db.rename_table("Cotainer Rent", "Container Rent")
			return
		conflicts = frappe.db.sql(
			"""select old.name
			from `tabCotainer Rent` old
			inner join `tabContainer Rent` new on new.name = old.name""",
			pluck=True,
		)
		if conflicts:
			frappe.throw(
				"Cannot merge Cotainer Rent because these names already exist in Container Rent: "
				+ ", ".join(conflicts)
			)
		old_columns = set(frappe.db.get_table_columns("Cotainer Rent"))
		new_columns = set(frappe.db.get_table_columns("Container Rent"))
		columns = sorted(old_columns & new_columns)
		quoted = ", ".join(f"`{column}`" for column in columns)
		frappe.db.sql(
			f"INSERT INTO `tabContainer Rent` ({quoted}) "
			f"SELECT {quoted} FROM `tabCotainer Rent`"
		)
		missing = frappe.db.sql(
			"""select old.name
			from `tabCotainer Rent` old
			left join `tabContainer Rent` new on new.name = old.name
			where new.name is null""",
			pluck=True,
		)
		if missing:
			frappe.throw("Container Rent migration did not copy every record")
		frappe.db.sql_ddl("DROP TABLE `tabCotainer Rent`")
