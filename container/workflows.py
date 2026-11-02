"""Mapped-document workflows for container operations and commissions."""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate


TRIP_SOURCES = ("Rent A Container", "Container Replacement", "Pull Container")


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
	filters = [["Rent A Container Item", "container", "=", container], ["docstatus", "!=", 2]]
	if operation_date:
		filters.append(["from", "<", add_days(getdate(operation_date), 1)])
	rows = frappe.get_list(
		"Rent A Container",
		filters=filters,
		fields=["name", "client", "classification", "address", "from", "to"],
		order_by="`tabRent A Container`.`from` desc, `tabRent A Container`.creation desc, `tabRent A Container`.name desc",
		limit_page_length=1,
	)
	return rows[0] if rows else None


def _selected_container(source):
	"""Return the container chosen for a mapped document; rentals and pulls can hold several."""
	containers = [row.container for row in source.containers]
	container = (frappe.flags.args or {}).get("container")
	if not container and len(containers) == 1:
		container = containers[0]
	if not container or container not in containers:
		frappe.throw(_("Select a container from {0}.").format(source.name))
	return container


def _trip_context(source):
	if source.doctype == "Rent A Container":
		return frappe._dict(
			container=_selected_container(source),
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
		container = _selected_container(source)
		rental_container = container
		operation_date = source.get("date")
	if source.get("rent_a_container"):
		rental = frappe._dict(client=source.client, classification=source.classification, address=source.address)
	else:
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
	context = _trip_context(source)
	if frappe.db.exists(
		"Container Trip",
		{
			"source_doctype": source_doctype,
			"source_name": source.name,
			"container": context.container,
			"docstatus": ["!=", 2],
		},
	):
		frappe.throw(_("An active Container Trip already exists for container {0}.").format(context.container))

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
def make_pull_from_container_rent(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	source = frappe.get_doc("Rent A Container", source_name)
	source.check_permission("read")
	frappe.has_permission("Pull Container", "create", throw=True)
	if source.docstatus == 2:
		frappe.throw(_("Cannot create a Pull Container from a cancelled rental."))
	containers = [
		frappe.db.get_value(
			"Container", row.container, ["name", "status", "container_size", "classification"], as_dict=True
		)
		for row in source.containers
	]
	containers = [c for c in containers if c and c.status in ("Rented", "Late")]
	if not containers:
		frappe.throw(_("Only a Rented or Late container can be selected for pulling."))

	def set_containers(source_doc, target):
		# Fill the fetched columns now; fetch_from would only run when the new pull is saved.
		for c in containers:
			target.append(
				"containers",
				{"container": c.name, "container_size": c.container_size, "classification": c.classification},
			)

	return get_mapped_doc(
		"Rent A Container",
		source_name,
		{
			"Rent A Container": {
				"doctype": "Pull Container",
				"field_map": {"name": "rent_a_container", "from": "rent_from", "to": "rent_to"},
				"field_no_map": ["amended_from"],
			}
		},
		target_doc,
		set_containers,
	)


@frappe.whitelist()
def make_trip_from_container_rent(source_name, target_doc=None):
	return _make_trip("Rent A Container", source_name, target_doc)


@frappe.whitelist()
def make_trip_from_container_replacement(source_name, target_doc=None):
	return _make_trip("Container Replacement", source_name, target_doc)


@frappe.whitelist()
def make_emptying_from_pull_container(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	source = frappe.get_doc("Pull Container", source_name)
	source.check_permission("read")
	frappe.has_permission("Emptying Container", "create", throw=True)
	if source.docstatus == 2:
		frappe.throw(_("Cannot create an Emptying Container from a cancelled pull."))
	container = _selected_container(source)
	if frappe.db.get_value("Container", container, "status") != "Pull":
		frappe.throw(_("Only a container with status Pull can be emptied."))

	def set_container(source_doc, target):
		target.container = container

	return get_mapped_doc(
		"Pull Container",
		source_name,
		{
			"Pull Container": {
				"doctype": "Emptying Container",
				"field_no_map": ["amended_from", "emptying_date"],
			}
		},
		target_doc,
		set_container,
	)


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


@frappe.whitelist(methods=["POST"])
def create_sales_invoice_from_container_rent(source_name):
	"""Create the rental invoice using the item's selling price."""
	frappe.has_permission("Sales Invoice", "create", throw=True)
	source = frappe.get_doc("Rent A Container", source_name)
	source.check_permission("read")
	# Serialize clicks against the same rental, including requests from other tabs.
	frappe.db.get_value("Rent A Container", source_name, "name", for_update=True)
	source.reload()
	if source.docstatus == 2:
		frappe.throw(_("Cannot invoice a cancelled rental."))
	existing = frappe.db.get_value(
		"Sales Invoice", {"container_rent": source.name, "docstatus": ["!=", 2], "is_return": 0}, "name"
	)
	if existing:
		frappe.get_doc("Sales Invoice", existing).check_permission("read")
		return existing
	invoice = _build_rental_invoice(source)
	invoice.insert()
	invoice.submit()
	return invoice.name


def _build_rental_invoice(source):
	"""Return an unsaved Sales Invoice priced from the rental's container Items."""
	from frappe.utils import today
	from erpnext.stock.get_item_details import get_price_list_rate_for

	if not source.client:
		frappe.throw(_("Select a Client on the rental before creating an invoice."))
	containers = [row.container for row in source.containers]
	if not containers:
		frappe.throw(_("Add at least one container to the rental before creating an invoice."))
	items = []
	for container in containers:
		if not frappe.db.exists("Item", container):
			frappe.throw(_("Create an Item with the same code as Container {0} and set its selling Item Price.").format(container))
		item = frappe.get_doc("Item", container)
		item.check_permission("read")
		if item.disabled or not item.is_sales_item:
			frappe.throw(_("The container Item {0} must be enabled for sales.").format(container))
		items.append(item)
	company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		frappe.throw(_("Set a default Company before creating an invoice."))
	company_doc = frappe.get_doc("Company", company)
	if not company_doc.default_income_account or not company_doc.cost_center:
		frappe.throw(_("Set the company's Default Income Account and Cost Center before creating an invoice."))
	invoice = frappe.new_doc("Sales Invoice")
	invoice.update({
		"company": company,
		"customer": source.client,
		"posting_date": today(),
		"currency": company_doc.default_currency,
		"conversion_rate": 1,
		"container_rent": source.name,
		"update_stock": 0,
		"remarks": _("Container rental {0}; containers {1}").format(source.name, ", ".join(containers)),
	})
	invoice.set_missing_values()
	if not invoice.selling_price_list:
		frappe.throw(_("Set a Selling Price List for the customer or in Selling Settings."))
	for item in items:
		price = get_price_list_rate_for(frappe._dict(
			price_list=invoice.selling_price_list,
			customer=source.client,
			uom=item.stock_uom,
			stock_uom=item.stock_uom,
			qty=1,
			conversion_factor=1,
			transaction_date=invoice.posting_date,
		), item.name)
		if price is None:
			frappe.throw(_("No valid Item Price found for {0} in {1}. Add one before creating the invoice.").format(item.name, invoice.selling_price_list))
		invoice.append("items", {
			"item_code": item.name,
			"qty": 1,
			"uom": item.stock_uom,
			"stock_uom": item.stock_uom,
			"conversion_factor": 1,
			"income_account": company_doc.default_income_account,
			"cost_center": company_doc.cost_center,
		})
	invoice.set_missing_values()
	invoice.calculate_taxes_and_totals()
	return invoice


@frappe.whitelist()
def make_payment_entry_from_container_rent(source_name, target_doc=None):
	"""Open a Payment Entry against the rental's outstanding Sales Invoice, or an advance for its total."""
	from frappe.utils import today
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_bank_cash_account, get_payment_entry
	from erpnext.accounts.party import get_party_account

	frappe.has_permission("Payment Entry", "create", throw=True)
	source = frappe.get_doc("Rent A Container", source_name)
	source.check_permission("read")
	if source.docstatus != 1:
		frappe.throw(_("Submit the rental before creating a payment."))
	invoices = frappe.get_list(
		"Sales Invoice",
		filters={"container_rent": source.name, "docstatus": 1, "is_return": 0},
		fields=["name", "outstanding_amount"],
		order_by="posting_date desc, creation desc",
	)
	if invoices:
		invoice = next((row for row in invoices if flt(row.outstanding_amount) > 0), None)
		if not invoice:
			frappe.throw(_("The Sales Invoice for rental {0} is already fully paid.").format(source.name))
		return get_payment_entry("Sales Invoice", invoice.name)

	# Not invoiced yet: take an unallocated advance priced exactly as the invoice will be.
	invoice = _build_rental_invoice(source)
	party_account = get_party_account("Customer", source.client, invoice.company)
	if frappe.get_cached_value("Account", party_account, "account_currency") != invoice.currency:
		frappe.throw(_("Receivable account {0} must be in {1} to take an advance.").format(party_account, invoice.currency))
	bank = get_bank_cash_account(invoice, None)
	if not bank:
		frappe.throw(_("Set a default Bank or Cash account for company {0}.").format(invoice.company))
	amount = invoice.rounded_total or invoice.grand_total
	payment = frappe.new_doc("Payment Entry")
	payment.update({
		"payment_type": "Receive",
		"company": invoice.company,
		"posting_date": today(),
		"party_type": "Customer",
		"party": source.client,
		"paid_from": party_account,
		"paid_to": bank.account,
		"paid_amount": amount,
		"received_amount": amount,
		"source_exchange_rate": 1,
		"target_exchange_rate": 1,
		"remarks": _("Advance for container rental {0}").format(source.name),
	})
	payment.setup_party_account_field()
	payment.set_missing_values()
	return payment
