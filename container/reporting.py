"""Complex reports use permission-aware ORM reads, never unrestricted SQL."""

import frappe
from frappe.utils import add_days, flt, getdate, today


def execute_report(name, filters=None):
	filters = frappe._dict(filters or {})
	if name == "Fleet Maintenance Due Report":
		return fleet_due()
	invoice_filters = {"docstatus": 1, "container_contract": ["is", "set"]}
	if filters.customer:
		invoice_filters["customer"] = filters.customer
	if filters.contract:
		invoice_filters["container_contract"] = filters.contract
	rows = frappe.get_list(
		"Sales Invoice",
		filters=invoice_filters,
		fields=["name", "container_contract", "customer", "currency", "grand_total", "outstanding_amount"],
		limit_page_length=0,
	)
	columns = [
		dict(fieldname=f, label=label, fieldtype=t, options=opt, width=150)
		for f, label, t, opt in [
			("name", "Invoice", "Link", "Sales Invoice"),
			("container_contract", "Contract", "Link", "Container Contract"),
			("customer", "Customer", "Link", "Customer"),
			("currency", "Currency", "Link", "Currency"),
			("grand_total", "Invoice Total", "Currency", "currency"),
			("outstanding_amount", "Outstanding", "Currency", "currency"),
		]
	]
	if name == "Contract Payment Report":
		# Settled includes payments, credits and write-offs, exactly as ERPNext outstanding does.
		columns.append(
			dict(
				fieldname="settled",
				label="Settled (incl. credits/write-offs)",
				fieldtype="Currency",
				options="currency",
				width=230,
			)
		)
		for row in rows:
			row["settled"] = flt(row.grand_total) - flt(row.outstanding_amount)
	else:
		rows = [r for r in rows if flt(r.outstanding_amount) != 0]
	return columns, rows


def fleet_due():
	columns = [
		dict(fieldname=f, label=l, fieldtype=t, options=o, width=180)
		for f, l, t, o in [
			("truck", "Truck", "Link", "Vehicle"),
			("maintenance", "Maintenance", "Data", None),
			("due_date", "Due Date", "Date", None),
			("due_km", "Due KM", "Int", None),
			("current_km", "Current KM", "Int", None),
			("status", "Status", "Data", None),
		]
	]
	rows = []

	def add(truck, kind, date=None, km=None, current=0):
		overdue = (date and getdate(date) < getdate(today())) or (km and current >= km)
		if (
			overdue
			or (date and getdate(date) <= getdate(add_days(today(), 30)))
			or (km and km - current <= 1000)
		):
			rows.append(
				dict(
					truck=truck,
					maintenance=kind,
					due_date=date,
					due_km=km,
					current_km=current,
					status="Overdue" if overdue else "Upcoming",
				)
			)

	for truck in frappe.get_list(
		"Vehicle",
		fields=["name", "last_odometer", "container_registration_expiry", "end_date"],
		limit_page_length=0,
	):
		add(truck.name, "Registration", truck.container_registration_expiry)
		add(truck.name, "Insurance", truck.end_date)
		oils = frappe.get_list(
			"Truck Oil Change",
			filters={"truck": truck.name, "docstatus": 1},
			fields=["next_oil_change_date", "next_oil_change_km"],
			order_by="oil_change_date desc, creation desc",
			limit_page_length=1,
		)
		if oils:
			add(
				truck.name,
				"Oil Change",
				oils[0].next_oil_change_date,
				oils[0].next_oil_change_km,
				truck.last_odometer,
			)
		for permit in frappe.get_list(
			"Truck Permit",
			filters={"truck": truck.name},
			fields=["permit_type", "expiry_date"],
			limit_page_length=0,
		):
			add(truck.name, permit.permit_type, permit.expiry_date)
	return columns, rows


@frappe.whitelist()
def outstanding_card(filters=None):
	"""Company-base currency only; never sum unrelated invoice currencies."""
	company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)
	if not company:
		return dict(value=0, fieldtype="Currency", route=["query-report", "Contract Outstanding Report"])
	frappe.get_doc("Company", company).check_permission("read")
	invoices = frappe.get_list(
		"Sales Invoice",
		filters={
			"company": company,
			"docstatus": 1,
			"container_contract": ["is", "set"],
			"outstanding_amount": [">", 0],
		},
		fields=["outstanding_amount", "conversion_rate"],
		limit_page_length=0,
	)
	return dict(
		value=sum(flt(r.outstanding_amount) * flt(r.conversion_rate) for r in invoices),
		fieldtype="Currency",
		options=frappe.db.get_value("Company", company, "default_currency"),
		route=["query-report", "Contract Outstanding Report"],
	)
