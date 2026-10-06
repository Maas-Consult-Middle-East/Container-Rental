"""Rental operations. Submitted movements are the authoritative state transitions."""

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_datetime, getdate, nowdate

EMPTY = ("Empty", "Available")
RENTED = ("Rented", "Late", "Pull", "Pulling", "Emptying")


def fail(message):
	frappe.throw(_(message))


def nonnegative(doc, fields):
	for field in fields:
		if flt(doc.get(field)) < 0:
			fail(f"{field.replace('_', ' ').title()} cannot be negative")


def dates(start, end):
	if start and end and get_datetime(end) < get_datetime(start):
		fail("End date cannot be before start date")


def lock(doctype, name):
	if not name or not frappe.db.get_value(doctype, name, "name", for_update=True):
		fail(f"{doctype} does not exist")


def contract_for(doc, active=True):
	if not doc.contract or not doc.customer:
		fail("Customer and contract are required")
	lock("Container Contract", doc.contract)
	contract = frappe.get_doc("Container Contract", doc.contract)
	contract.check_permission("read")
	if contract.customer != doc.customer:
		fail("Customer must match the contract")
	if active and (contract.docstatus != 1 or contract.status != "Active"):
		fail("An active submitted contract is required")
	return contract


def assigned(doc):
	lock("Container", doc.container)
	container = frappe.get_doc("Container", doc.container)
	container.check_permission("read")
	if container.current_contract != doc.contract or container.current_customer != doc.customer:
		fail("Container is not assigned to this customer and contract")
	return container


def movement(source, container, kind, date, location=None):
	doc = frappe.get_doc(
		dict(
			doctype="Container Movement",
			container=container,
			movement_type=kind,
			customer=source.customer,
			contract=source.get("contract") or source.name,
			movement_date=date,
			to_location=location,
			source_doctype=source.doctype,
			source_name=source.name,
			truck=source.get("truck"),
			driver=source.get("driver"),
		)
	)
	doc.flags.operation_source = source
	doc.insert()
	doc.submit()
	return doc


def cancel_movements(source):
	rows = frappe.get_all(
		"Container Movement",
		filters=dict(source_doctype=source.doctype, source_name=source.name, docstatus=1),
		pluck="name",
		order_by="creation desc",
	)
	for name in rows:
		doc = frappe.get_doc("Container Movement", name)
		doc.flags.operation_source = source
		doc.cancel()


class ContainerBase(Document):
	def validate(self):
		if not frappe.db.get_value("Container Type", self.container_type, "active"):
			fail("Select an active container type")
		if self.status in RENTED:
			if not self.current_customer or not self.current_contract:
				fail("A rented container requires a customer and active contract")
			contract = frappe.get_doc("Container Contract", self.current_contract)
			if (
				contract.docstatus != 1
				or contract.status != "Active"
				or contract.customer != self.current_customer
			):
				fail("Container must reference an active contract for its customer")
		if self.status in EMPTY and (self.current_customer or self.current_contract):
			fail("An empty container cannot have an active assignment")
		if self.is_new() and (self.status not in EMPTY or self.current_contract or self.current_customer):
			fail("Create an empty container, then assign it through a submitted transaction")
		old = self.get_doc_before_save()
		if old and any(
			old.get(f) != self.get(f)
			for f in ["status", "current_customer", "current_contract", "current_location"]
		):
			fail("Use a Container Movement to change the current assignment or location")


class ContainerContractBase(Document):
	def validate(self):
		dates(self.contract_from, self.contract_to)
		dates(self.start_date, self.end_date)
		nonnegative(self, ["no_of_trips", "price", "unlimited_billing_amount"])
		if self.allow_extra_trips and not self.override_reason:
			fail("An override reason is required for extra trips")
		seen = set()
		for row in self.containers:
			if row.container in seen:
				fail("A container can only appear once in a contract")
			seen.add(row.container)
			dates(row.start_date, row.end_date)
			nonnegative(row, ["no_of_trips", "rate"])
			row.total = flt(row.no_of_trips) * flt(row.rate)
		if self.contract_type != "Unlimited Contract":
			if self.containers:
				self.no_of_trips = sum(cint(r.no_of_trips) for r in self.containers)
				self.total = sum(flt(r.total) for r in self.containers)
			else:
				self.total = cint(self.no_of_trips) * flt(self.price)
		else:
			self.total = 0
		self.used_trips = (
			frappe.db.count(
				"Container Trip",
				{"contract": self.name, "docstatus": 1, "trip_status": ["in", ["Delivered", "Returned"]]},
			)
			if not self.is_new()
			else 0
		)
		self.remaining_trips = (
			max(0, cint(self.no_of_trips) - self.used_trips)
			if self.contract_type != "Unlimited Contract"
			else 0
		)
		self.status = (
			"Draft"
			if self.docstatus == 0
			else (
				"Cancelled"
				if self.docstatus == 2
				else (self.status if self.status == "Completed" else "Active")
			)
		)
		from container.billing import invoice_preview

		self.contract_cost = (
			invoice_preview(self).grand_total
			if self.rental_item
			else (self.unlimited_billing_amount if self.contract_type == "Unlimited Contract" else self.total)
		)
		if not self.rental_item and self.tax_treatment not in ("Exempt", "Exempt from tax"):
			fail("Set a rental item and tax template to calculate the tax-inclusive contract cost")

	def before_submit(self):
		if self.allow_extra_trips and not ({"Container Manager", "System Manager"} & set(frappe.get_roles())):
			frappe.throw(
				_("A Container Manager must submit contracts with a trip override"), frappe.PermissionError
			)
		for container_type in sorted(
			{frappe.db.get_value("Container", row.container, "container_type") for row in self.containers}
		):
			lock("Container Type", container_type)
		for row in sorted(self.containers, key=lambda r: r.container):
			lock("Container", row.container)
			if frappe.db.get_value("Container", row.container, "status") not in EMPTY:
				fail("A contract container is already assigned")

	def on_submit(self):
		self.db_set("status", "Active")
		for row in self.containers:
			movement(self, row.container, "Delivery", self.contract_from, self.location)

	def on_cancel(self):
		if frappe.db.exists("Sales Invoice", {"container_contract": self.name, "docstatus": 1}):
			fail("Cancel the contract invoices first")
		cancel_movements(self)
		self.db_set("status", "Cancelled")

	@frappe.whitelist()
	def complete(self):
		self.check_permission("write")
		if "Container Manager" not in frappe.get_roles() and frappe.session.user != "Administrator":
			frappe.throw(_("Container Manager role required"), frappe.PermissionError)
		lock(self.doctype, self.name)
		self.reload()
		if self.docstatus != 1 or self.status != "Active":
			fail("Only an active contract can be completed")
		if frappe.db.exists("Container", {"current_contract": self.name}):
			fail("Return all assigned containers before completing the contract")
		self.db_set("status", "Completed")


class ContainerMovementBase(Document):
	def validate(self):
		contract = contract_for(self)
		container_type = frappe.db.get_value("Container", self.container, "container_type")
		lock("Container Type", container_type)
		lock("Container", self.container)
		c = frappe.get_doc("Container", self.container)
		c.check_permission("write")
		source = self.flags.operation_source if isinstance(self.flags.operation_source, Document) else None
		if (self.source_doctype or self.source_name) and not source:
			# Loaded submitted documents may be cancelled only through their source.
			if self.docstatus != 2:
				fail("Source references are maintained by the originating transaction")
		if self.movement_type == "Replacement" and not source:
			fail("Use Container Replacement to replace both containers atomically")
		if self.movement_type == "Delivery":
			if c.status not in EMPTY:
				fail("Container is already assigned; return it before renting it again")
			if getdate(self.movement_date) < getdate(contract.contract_from):
				fail("Delivery cannot precede contract start")
			if contract.contract_to and getdate(self.movement_date) > getdate(contract.contract_to):
				fail("Delivery cannot follow contract end")
			conflicts = frappe.get_all(
				"Rent Reservation",
				filters={
					"container_type": container_type,
					"docstatus": 1,
					"status": ["in", ["Reserved", "Confirmed"]],
					"from_date": ["<=", contract.contract_to or "9999-12-31"],
					"to_date": [">=", getdate(self.movement_date)],
				},
				fields=["customer", "container", "quantity"],
			)
			if any(r.customer != self.customer and r.container == self.container for r in conflicts):
				fail("Container has a conflicting reservation")
			reserved = sum(cint(r.quantity) for r in conflicts if r.customer != self.customer)
			available = frappe.db.count(
				"Container", {"container_type": container_type, "status": ["in", EMPTY]}
			)
			if available - 1 < reserved:
				fail("Delivery would consume capacity reserved for another customer")
		else:
			assigned(self)
		previous = frappe.get_all(
			"Container Movement",
			filters={"container": self.container, "docstatus": 1, "name": ["!=", self.name]},
			fields=["movement_date"],
			order_by="creation desc",
			limit=1,
		)
		if previous and get_datetime(self.movement_date) < get_datetime(previous[0].movement_date):
			fail("Movement cannot precede the latest submitted movement")

	def on_submit(self):
		c = frappe.get_doc("Container", self.container)
		values = {
			f: c.get(f)
			for f in ["status", "current_customer", "current_contract", "current_location", "condition"]
		}
		self.db_set("previous_state", json.dumps(values))
		updates = {}
		if self.movement_type == "Delivery":
			updates.update(status="Rented", current_customer=self.customer, current_contract=self.contract)
		elif self.movement_type in ("Pull", "Pickup"):
			updates["status"] = "Pull"
		elif self.movement_type == "Return":
			updates.update(status="Empty", current_customer=None, current_contract=None)
		if self.to_location:
			updates["current_location"] = self.to_location
		if updates:
			frappe.db.set_value("Container", self.container, updates)

	def before_cancel(self):
		lock("Container", self.container)
		if self.source_name and not isinstance(self.flags.operation_source, Document):
			fail("Cancel the originating transaction instead")
		previous_contract = json.loads(self.previous_state or "{}").get("current_contract")
		if (
			previous_contract
			and frappe.db.get_value("Container Contract", previous_contract, "status") != "Active"
		):
			fail("Cannot restore an assignment to a closed contract")
		latest = frappe.get_all(
			"Container Movement",
			filters={"container": self.container, "docstatus": 1},
			pluck="name",
			order_by="creation desc",
			limit=1,
		)
		if latest != [self.name]:
			fail("Cancel subsequent movements first")
		for dt in ["Container Trip", "Container Emptying"]:
			if frappe.db.exists(
				dt, {"container": self.container, "docstatus": 1, "creation": [">", self.creation]}
			):
				fail("Cancel subsequent operations first")

	def on_cancel(self):
		frappe.db.set_value("Container", self.container, json.loads(self.previous_state))


class RentReservationBase(Document):
	@frappe.whitelist()
	def set_reservation_status(self, status):
		self.check_permission("write")
		lock(self.doctype, self.name)
		self.reload()
		if self.docstatus != 1 or self.status not in ("Reserved", "Confirmed"):
			fail("Only an open submitted reservation can change status")
		if status not in ("Confirmed", "Completed"):
			fail("Use cancellation to cancel a reservation")
		self.db_set("status", status)

	def validate(self):
		dates(self.from_date, self.to_date)
		nonnegative(self, ["rental_rate"])
		if cint(self.quantity) < 1:
			fail("Quantity must be positive")
		lock("Container Type", self.container_type)
		if self.container:
			lock("Container", self.container)
			c = frappe.get_doc("Container", self.container)
			if self.quantity != 1 or c.container_type != self.container_type:
				fail("A specific container reservation must have quantity one and match its type")
		overlaps = frappe.get_all(
			"Rent Reservation",
			filters={
				"name": ["!=", self.name],
				"container_type": self.container_type,
				"docstatus": 1,
				"status": ["in", ["Reserved", "Confirmed"]],
				"from_date": ["<=", self.to_date],
				"to_date": [">=", self.from_date],
			},
			fields=["container", "quantity"],
		)
		if self.container and any(r.container == self.container for r in overlaps):
			fail("Container has an overlapping reservation")
		# Conservatively exclude currently assigned containers; future returns are not guaranteed.
		available = frappe.db.count(
			"Container", {"container_type": self.container_type, "status": ["in", EMPTY]}
		)
		if self.container and frappe.db.get_value("Container", self.container, "status") not in EMPTY:
			fail("Selected container is not available")
		if sum(cint(r.quantity) for r in overlaps) + self.quantity > available:
			fail("Insufficient available containers for this reservation period")
		self.status = "Draft" if self.docstatus == 0 else "Reserved"

	def on_cancel(self):
		self.db_set("status", "Cancelled")


class ContainerTripBase(Document):
	def validate(self):
		contract = contract_for(self)
		assigned(self)
		dates(self.pickup_date, self.delivery_date)
		nonnegative(self, ["trip_cost"])
		if self.trip_status in ("Delivered", "Returned") and not self.delivery_date:
			fail("Completed trips require a delivery date")
		if self.docstatus == 1:
			if self.trip_status not in ("Delivered", "Returned"):
				fail("Only completed trips may be submitted; keep planned trips in draft")
			used = frappe.db.count(
				"Container Trip", {"contract": self.contract, "docstatus": 1, "name": ["!=", self.name]}
			)
			if (
				contract.contract_type != "Unlimited Contract"
				and not contract.allow_extra_trips
				and used >= cint(contract.no_of_trips)
			):
				fail("Contract trip limit has been reached")

	def on_submit(self):
		movement(self, self.container, "Transfer", self.delivery_date, self.delivery_location)
		self.update_usage()

	def on_cancel(self):
		lock("Container Contract", self.contract)
		cancel_movements(self)
		self.update_usage()

	def update_usage(self):
		c = frappe.get_doc("Container Contract", self.contract)
		used = frappe.db.count("Container Trip", {"contract": self.contract, "docstatus": 1})
		frappe.db.set_value(
			"Container Contract",
			self.contract,
			dict(
				used_trips=used,
				remaining_trips=max(0, cint(c.no_of_trips) - used)
				if c.contract_type != "Unlimited Contract"
				else 0,
			),
		)


class ContainerEmptyingBase(Document):
	def validate(self):
		contract_for(self)
		assigned(self)
		nonnegative(self, ["charges"])

	def on_submit(self):
		movement(self, self.container, "Emptying", self.emptying_date, self.location)
		if self.condition_after:
			frappe.db.set_value("Container", self.container, "condition", self.condition_after)

	def on_cancel(self):
		cancel_movements(self)


class ContainerReplacementBase(Document):
	def validate(self):
		contract_for(self)
		nonnegative(self, ["charges"])
		if self.old_container == self.new_container:
			fail("Old and new containers must differ")
		for name in sorted([self.old_container, self.new_container]):
			lock("Container", name)
		old = frappe.get_doc("Container", self.old_container)
		if old.current_contract != self.contract or old.current_customer != self.customer:
			fail("Old container is not assigned to this contract")
		if frappe.db.get_value("Container", self.new_container, "status") not in EMPTY:
			fail("New container must be empty")

	def on_submit(self):
		location = frappe.db.get_value("Container", self.old_container, "current_location")
		movement(self, self.old_container, "Return", self.replacement_date)
		movement(self, self.new_container, "Delivery", self.replacement_date, location)
		for name, condition in [
			(self.old_container, self.old_container_condition),
			(self.new_container, self.new_container_condition),
		]:
			if condition:
				frappe.db.set_value("Container", name, "condition", condition)

	def on_cancel(self):
		cancel_movements(self)


class TruckKMReadingBase(Document):
	def validate(self):
		lock("Vehicle", self.truck)
		nonnegative(self, ["current_km"])
		previous = frappe.db.get_value("Vehicle", self.truck, "last_odometer") or 0
		if self.current_km < previous:
			fail("Odometer cannot decrease")
		self.previous_km = previous
		latest = frappe.get_all(
			self.doctype,
			filters={"truck": self.truck, "docstatus": 1},
			fields=["reading_date"],
			order_by="reading_date desc",
			limit=1,
		)
		if latest and getdate(self.reading_date) < getdate(latest[0].reading_date):
			fail("Reading cannot precede the latest reading")

	def on_submit(self):
		frappe.db.set_value("Vehicle", self.truck, "last_odometer", self.current_km)

	def on_cancel(self):
		lock("Vehicle", self.truck)
		if frappe.db.exists(
			self.doctype, {"truck": self.truck, "docstatus": 1, "creation": [">", self.creation]}
		):
			fail("Cancel later readings first")
		if frappe.db.get_value("Vehicle", self.truck, "last_odometer") != self.current_km:
			fail("Vehicle odometer has changed since this reading")
		frappe.db.set_value("Vehicle", self.truck, "last_odometer", self.previous_km)


class TruckOilChangeBase(Document):
	def validate(self):
		nonnegative(self, ["current_km", "next_oil_change_km", "cost"])
		dates(self.oil_change_date, self.next_oil_change_date)
		if self.next_oil_change_km and self.next_oil_change_km <= self.current_km:
			fail("Next oil change KM must exceed current KM")


class TruckPermitBase(Document):
	def validate(self):
		dates(self.issue_date, self.expiry_date)
		from frappe.utils import date_diff

		days = date_diff(self.expiry_date, nowdate())
		self.status = "Expired" if days < 0 else ("Expiring" if days <= 30 else "Valid")


class ClientWithdrawalBase(Document):
	def validate(self):
		contract = contract_for(self, active=False)
		if flt(self.amount) <= 0:
			fail("Withdrawal amount must be positive")
		lock("Payment Entry", self.payment_entry)
		payment = frappe.get_doc("Payment Entry", self.payment_entry)
		payment.check_permission("read")
		if (
			payment.docstatus != 1
			or payment.payment_type != "Pay"
			or payment.party_type != "Customer"
			or payment.party != self.customer
			or payment.company != contract.company
		):
			fail("Select a submitted customer refund Payment Entry for the contract company")
		if payment.paid_to_account_currency != contract.currency:
			fail("Refund currency must match contract currency")
		other = frappe.get_all(
			self.doctype,
			filters={"payment_entry": self.payment_entry, "docstatus": 1, "name": ["!=", self.name]},
			pluck="amount",
		)
		if sum(flt(x) for x in other) + flt(self.amount) > flt(payment.received_amount):
			fail("Withdrawals exceed the refunded amount")


class CommissionRuleBase(Document):
	def validate(self):
		dates(self.effective_from, self.effective_to)
		nonnegative(self, ["percentage", "fixed_amount"])
		if flt(self.percentage) > 100:
			fail("Commission percentage cannot exceed 100")


class CommissionEntryBase(Document):
	def validate(self):
		contract = contract_for(self, active=False)
		lock("Sales Invoice", self.invoice)
		invoice = frappe.get_doc("Sales Invoice", self.invoice)
		invoice.check_permission("read")
		rule = frappe.get_doc("Commission Rule", self.commission_rule)
		rule.check_permission("read")
		if (
			invoice.docstatus != 1
			or invoice.is_return
			or invoice.customer != self.customer
			or invoice.container_contract != self.contract
			or invoice.currency != contract.currency
		):
			fail("Commission requires a submitted non-return invoice for this contract")
		if (
			not rule.active
			or rule.sales_person != self.sales_person
			or (rule.customer and rule.customer != self.customer)
			or (rule.contract and rule.contract != self.contract)
		):
			fail("Commission rule does not apply")
		if getdate(invoice.posting_date) < getdate(rule.effective_from) or (
			rule.effective_to and getdate(invoice.posting_date) > getdate(rule.effective_to)
		):
			fail("Commission rule is not effective on the invoice date")
		if frappe.db.exists(
			self.doctype,
			{
				"invoice": self.invoice,
				"sales_person": self.sales_person,
				"docstatus": ["!=", 2],
				"name": ["!=", self.name],
			},
		):
			fail("Commission already exists for this invoice and sales person")
		self.base_amount = invoice.net_total
		self.commission_percentage = rule.percentage if rule.commission_type == "Percentage" else 0
		self.commission_amount = (
			flt(self.base_amount) * flt(rule.percentage) / 100
			if rule.commission_type == "Percentage"
			else rule.fixed_amount
		)
		self.status = "Accrued" if self.docstatus == 1 else "Draft"

	def on_cancel(self):
		self.db_set("status", "Cancelled")
