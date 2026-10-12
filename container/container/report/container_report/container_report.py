"""Search container rentals without bypassing document permissions."""

import json
import math

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, strip_html


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if filters.from_date and filters.to_date and getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))
	if filters.container_status not in (None, "", "Rented", "Pull", "Late", "Empty"):
		frappe.throw(_("Select a valid container status."))
	frappe.has_permission("Container Rent", "read", throw=True)
	conditions = [["docstatus", "!=", 2]]
	if filters.container:
		conditions.append(["container_number", "=", filters.container])
	if filters.customer:
		conditions.append(["client", "=", filters.customer])
	if filters.from_date:
		conditions.append(["from", ">=", getdate(filters.from_date)])
	if filters.to_date:
		conditions.append(["from", "<", add_days(getdate(filters.to_date), 1)])
	rentals = frappe.get_list(
		"Container Rent",
		filters=conditions,
		fields=["name", "container_number", "client", "contact_number", "address", "driver",
			"classification", "from", "to", "latitude", "longitude", "location"],
		order_by="`tabContainer Rent`.`from` desc, creation desc, name desc",
		limit_page_length=0,
	)
	if not rentals:
		return get_columns(), []
	customers = linked_records("Customer", [r.client for r in rentals],
		["customer_name", "mobile_no", "primary_address"])
	drivers = linked_records("Driver", [r.driver for r in rentals], ["full_name"])
	containers = linked_records("Container", [r.container_number for r in rentals], ["status"])
	contracts = contracts_by_customer([r.client for r in rentals])
	rows = []
	for rental in rentals:
		customer = customers.get(rental.client, {})
		container = containers.get(rental.container_number)
		status = container.get("status") if container else None
		if filters.container_status and status != filters.container_status:
			continue
		contract = contract_for_rental(rental, contracts.get(rental.client, []))
		rows.append({
			"container_number": rental.container_number,
			"rent_number": rental.name,
			"client_name": customer.get("customer_name") or rental.client,
			"client_phone": rental.contact_number or customer.get("mobile_no"),
			"client_address": strip_html((customer.get("primary_address") or "").replace("<br>", ", ").replace("<br/>", ", ")),
			"driver_name": drivers.get(rental.driver, {}).get("full_name") or rental.driver,
			"address": rental.address,
			"from_date": rental.get("from"),
			"to_date": rental.get("to"),
			"amount": flt(contract.total) if contract else None,
			"container_status": _(status) if status else None,
			"location": map_url(rental),
		})
	return get_columns(), rows


def contracts_by_customer(customers):
	"""Return readable submitted contracts grouped by customer, newest first."""
	customers = sorted({customer for customer in customers if customer})
	if not customers or not frappe.has_permission("Container Contract", "read"):
		return {}
	grouped = {}
	for contract in frappe.get_list(
		"Container Contract",
		filters={"docstatus": 1, "customer": ["in", customers]},
		fields=["name", "customer", "classification", "contract_from", "contract_to", "total"],
		order_by="contract_from desc, modified desc, name desc",
		limit_page_length=0,
	):
		grouped.setdefault(contract.customer, []).append(contract)
	return grouped


def contract_for_rental(rental, contracts):
	"""Find the latest contract covering the rental date and classification."""
	rental_date = getdate(rental.get("from")) if rental.get("from") else None
	for contract in contracts:
		if rental_date and contract.contract_from and rental_date < getdate(contract.contract_from):
			continue
		if rental_date and contract.contract_to and rental_date > getdate(contract.contract_to):
			continue
		if contract.classification and contract.classification != rental.get("classification"):
			continue
		return contract
	return None


def linked_records(doctype, names, fields):
	"""Only enrich rows with related records the user may read."""
	names = sorted({name for name in names if name})
	if not names or not frappe.has_permission(doctype, "read"):
		return {}
	return {row.name: row for row in frappe.get_list(
		doctype, filters={"name": ["in", names]}, fields=["name", *fields], limit_page_length=0
	)}


def map_url(rental):
	latitude, longitude = rental.get("latitude"), rental.get("longitude")
	if latitude in (None, "") or longitude in (None, ""):
		try:
			geo = json.loads(rental.get("location") or "{}")
			if geo.get("type") == "FeatureCollection":
				geo = next((f.get("geometry", {}) for f in geo.get("features", [])
					if f.get("geometry", {}).get("type") == "Point"), {})
			elif geo.get("type") == "Feature":
				geo = geo.get("geometry") or {}
			if geo.get("type") != "Point":
				return None
			longitude, latitude = geo["coordinates"][:2]
		except (ValueError, TypeError, KeyError, AttributeError):
			return None
	try:
		latitude, longitude = float(latitude), float(longitude)
	except (ValueError, TypeError):
		return None
	if not (math.isfinite(latitude) and math.isfinite(longitude)
		and -90 <= latitude <= 90 and -180 <= longitude <= 180):
		return None
	return f"https://www.google.com/maps?q={latitude},{longitude}"


def get_columns():
	return [
		{"fieldname": field, "label": _(label), "fieldtype": kind, "width": width, **options}
		for field, label, kind, width, options in [
			("container_number", "Container Number", "Link", 150, {"options": "Container"}),
			("rent_number", "Rent Number", "Link", 150, {"options": "Container Rent"}),
			("client_name", "Client Name", "Data", 230, {}),
			("client_phone", "Client Phone Number", "Data", 170, {}),
			("client_address", "Client Address", "Data", 220, {}),
			("driver_name", "Driver Name", "Data", 180, {}),
			("address", "Address", "Data", 220, {}),
			("from_date", "From", "Datetime", 170, {}),
			("to_date", "To", "Datetime", 170, {}),
			("amount", "Agreed Container Amount", "Currency", 190, {}),
			("container_status", "Container Status", "Data", 160, {}),
			("location", "Location", "Data", 100, {}),
		]
	]
