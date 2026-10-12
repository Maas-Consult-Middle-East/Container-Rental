"""Mapped-document workflows for container operations and commissions."""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate


TRIP_SOURCES = ("Container Rent", "Container Replacement", "Pull Container")


def _new_doc(doctype, target_doc=None):
	if target_doc:
		return frappe.get_doc(frappe.parse_json(target_doc))
	return frappe.new_doc(doctype)


def _find_contract(customer, operation_date, classification=None):
	if not customer or not operation_date:
		return None
	filters = {
		"customer": customer,
		"docstatus": 1,
		"contract_from": ["<=", getdate(operation_date)],
	}
	contracts = frappe.get_list(
		"Container Contract",
		filters=filters,
		fields=["name", "classification", "contract_to", "total"],
		order_by="contract_from desc, modified desc, name desc",
		limit_page_length=0,
	)
	for contract in contracts:
		if contract.contract_to and getdate(operation_date) > getdate(contract.contract_to):
			continue
		if contract.classification and classification and contract.classification != classification:
			continue
		return contract
	return None


def _rental_for_container(container, operation_date):
	if not container:
		return None
	filters = [["container_number", "=", container], ["docstatus", "!=", 2]]
	if operation_date:
		filters.append(["from", "<", add_days(getdate(operation_date), 1)])
	rows = frappe.get_list(
		"Container Rent",
		filters=filters,
		fields=["name", "client", "classification", "address", "from", "to"],
		order_by="`tabContainer Rent`.`from` desc, creation desc, name desc",
		limit_page_length=1,
	)
	return rows[0] if rows else None


def _trip_context(source):
	if source.doctype == "Container Rent":
		return frappe._dict(
			container=source.container_number,
			customer=source.client,
			classification=source.classification,
			pickup_date=source.get("from"),
			delivery_date=source.get("to"),
			pickup_location=source.address,
			trip_cost=source.cost,
		)
	if source.doctype == "Container Replacement":
		container = source.new_container_number or source.rented_container_number
		rental_container = source.rented_container_number
		operation_date = source.replace_date
	else:
		container = source.container
		rental_container = container
		operation_date = source.emptying_date
	rental = _rental_for_container(rental_container, operation_date) or frappe._dict()
	return frappe._dict(
		container=container,
		customer=rental.get("client"),
		classification=rental.get("classification"),
		pickup_date=operation_date,
		pickup_location=rental.get("address"),
	)


def _make_trip(source_doctype, source_name, target_doc=None):
	if source_doctype not in TRIP_SOURCES:
		frappe.throw(_("Unsupported trip source."))
	frappe.has_permission("Container Trip", "create", throw=True)
	source = frappe.get_doc(source_doctype, source_name)
	source.check_permission("read")
	if source.docstatus != 1:
		frappe.throw(_("Submit {0} before creating a Container Trip.").format(source_doctype))
	if frappe.db.exists(
		"Container Trip",
		{"source_doctype": source_doctype, "source_name": source.name, "docstatus": ["!=", 2]},
	):
		frappe.throw(_("An active Container Trip already exists for this document."))

	context = _trip_context(source)
	contract = _find_contract(
		context.customer,
		context.pickup_date,
		context.classification,
	)
	trip = _new_doc("Container Trip", target_doc)
	trip.update(
		{
			"container": context.container,
			"customer": context.customer,
			"contract": contract.name if contract else None,
			"truck": source.get("truck"),
			"driver": source.get("driver"),
			"supervisor": source.get("supervisor"),
			"pickup_date": context.pickup_date,
			"delivery_date": context.get("delivery_date"),
			"pickup_location": context.pickup_location,
			"trip_status": "Planned",
			"trip_cost": flt(context.get("trip_cost")) or None,
			"driver_commission": flt(source.get("driver_commission")),
			"supervisor_commission": flt(source.get("supervisor_commission")),
			"remarks": source.get("notes"),
			"source_doctype": source.doctype,
			"source_name": source.name,
		}
	)
	return trip


@frappe.whitelist()
def make_trip_from_container_rent(source_name, target_doc=None):
	return _make_trip("Container Rent", source_name, target_doc)


@frappe.whitelist()
def make_trip_from_container_replacement(source_name, target_doc=None):
	return _make_trip("Container Replacement", source_name, target_doc)


@frappe.whitelist()
def make_trip_from_pull_container(source_name, target_doc=None):
	return _make_trip("Pull Container", source_name, target_doc)


def _make_commission(source_name, commission_type, target_doc=None):
	frappe.has_permission("Commission Entry", "create", throw=True)
	trip = frappe.get_doc("Container Trip", source_name)
	trip.check_permission("read")
	if trip.docstatus != 1:
		frappe.throw(_("Submit the Container Trip before creating a Commission Entry."))
	field = "driver" if commission_type == "Driver" else "supervisor"
	person = trip.get(field)
	amount = flt(trip.get(f"{field}_commission"))
	if not person or amount <= 0:
		frappe.throw(_("This trip has no {0} commission to create.").format(commission_type.lower()))
	if frappe.db.exists(
		"Commission Entry",
		{"trip": trip.name, "commission_type": commission_type, "docstatus": ["!=", 2]},
	):
		frappe.throw(_("An active {0} commission already exists for this trip.").format(commission_type.lower()))
	entry = _new_doc("Commission Entry", target_doc)
	entry.update(
		{
			"trip": trip.name,
			"commission_type": commission_type,
			"driver": person if commission_type == "Driver" else None,
			"supervisor": person if commission_type == "Supervisor" else None,
			"amount": amount,
		}
	)
	return entry


@frappe.whitelist()
def make_driver_commission(source_name, target_doc=None):
	return _make_commission(source_name, "Driver", target_doc)


@frappe.whitelist()
def make_supervisor_commission(source_name, target_doc=None):
	return _make_commission(source_name, "Supervisor", target_doc)
