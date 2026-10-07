"""Integration suite runnable against an initialized site; all records roll back."""

import unittest
import uuid

import frappe
from frappe.utils import add_days, now_datetime, today

from container.billing import make_invoice
from container.reporting import execute_report


class TestWorkflows(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.savepoint("container_test")
		self.prefix = "CTEST-" + uuid.uuid4().hex[:8]
		self.company = frappe.get_all("Company", pluck="name", limit=1)[0]
		self.currency = frappe.db.get_value("Company", self.company, "default_currency")
		self.type = self.create("Container Type", name=self.prefix, container_type=self.prefix)
		self.customer = self.create(
			"Customer",
			customer_name=self.prefix,
			customer_type="Company",
			customer_group=frappe.db.get_value("Customer Group", {"is_group": 0}, "name"),
			territory=frappe.db.get_value("Territory", {"is_group": 0}, "name"),
		)
		self.item = self.create(
			"Item",
			item_code=self.prefix,
			item_name=self.prefix,
			item_group=frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
			stock_uom="Nos",
			is_stock_item=0,
		)
		self.a = self.create("Container", name=self.prefix + "-A", container_type=self.type.name)
		self.b = self.create("Container", name=self.prefix + "-B", container_type=self.type.name)
		self.vehicle = self.create(
			"Vehicle",
			license_plate=self.prefix,
			make="Test",
			model="Test",
			last_odometer=100,
			fuel_type="Diesel",
			uom="Litre",
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="container_test")
		frappe.clear_cache()

	def create(self, doctype, **values):
		name = values.pop("name", None)
		doc = frappe.get_doc(dict(doctype=doctype, **values))
		if name:
			doc.name = name
		return doc.insert()

	def contract(self, kind="Rubble", trips=2, container=None, **kw):
		return self.create(
			"Container Contract",
			name=self.prefix + "-" + kind,
			contract_type=kind,
			customer=self.customer.name,
			company=self.company,
			currency=self.currency,
			rental_item=self.item.name,
			contract_date=today(),
			contract_from=today(),
			contract_to=add_days(today(), 10),
			tax_treatment="Exempt",
			no_of_trips=trips,
			price=100,
			containers=[dict(container=container or self.a.name, no_of_trips=trips, rate=100)],
			**kw,
		).submit()

	def move(self, c, kind, container=None):
		return self.create(
			"Container Movement",
			container=container or self.a.name,
			contract=c.name,
			customer=self.customer.name,
			movement_type=kind,
			movement_date=now_datetime(),
		).submit()

	def trip(self, c):
		return self.create(
			"Container Trip",
			container=self.a.name,
			customer=self.customer.name,
			contract=c.name,
			truck=self.vehicle.name,
			pickup_date=now_datetime(),
			delivery_date=now_datetime(),
			trip_status="Delivered",
		).submit()

	def test_rubble_pull_return_and_cancel(self):
		c = self.contract()
		self.a.reload()
		self.assertEqual((self.a.status, self.a.current_contract), ("Rented", c.name))
		pull = self.move(c, "Pull")
		self.assertEqual(self.a.reload().status, "Pull")
		ret = self.move(c, "Return")
		self.assertEqual(self.a.reload().status, "Empty")
		with self.assertRaises(frappe.ValidationError):
			pull.cancel()
		ret.cancel()
		self.assertEqual(self.a.reload().status, "Pull")
		pull.reload().cancel()
		self.assertEqual(self.a.reload().status, "Rented")
		c.reload().cancel()
		self.assertEqual(self.a.reload().status, "Empty")

	def test_trash_calculation(self):
		c = self.contract("Trash", 3)
		self.assertEqual(c.total, 300)
		self.assertEqual(c.contract_cost, 300)

	def test_trip_limit_and_cancellation(self):
		c = self.contract(trips=1)
		t = self.trip(c)
		self.assertEqual(c.reload().used_trips, 1)
		with self.assertRaises(frappe.ValidationError):
			self.trip(c)
		t.cancel()
		self.assertEqual(c.reload().used_trips, 0)
		self.trip(c)
		self.assertEqual(c.reload().remaining_trips, 0)

	def test_unlimited_trips(self):
		c = self.contract("Unlimited Contract", 0, unlimited_billing_amount=500)
		self.trip(c)
		self.trip(c)
		self.assertEqual(c.reload().used_trips, 2)
		self.assertEqual(c.total, 0)

	def test_replacement_and_cancellation(self):
		c = self.contract()
		r = self.create(
			"Container Replacement",
			customer=self.customer.name,
			contract=c.name,
			old_container=self.a.name,
			new_container=self.b.name,
			replacement_date=now_datetime(),
			reason="Service",
			old_container_condition="Repair",
			new_container_condition="Good",
		).submit()
		self.assertEqual(self.a.reload().status, "Empty")
		self.assertEqual(self.b.reload().status, "Rented")
		r.cancel()
		self.assertEqual(self.a.reload().status, "Rented")
		self.assertEqual(self.b.reload().status, "Empty")

	def test_emptying_preserves_assignment(self):
		c = self.contract()
		e = self.create(
			"Container Emptying",
			container=self.a.name,
			customer=self.customer.name,
			contract=c.name,
			emptying_date=now_datetime(),
			condition_after="Good",
		).submit()
		self.assertEqual(self.a.reload().current_contract, c.name)
		self.assertEqual(self.a.condition, "Good")
		e.cancel()
		self.assertFalse(self.a.reload().condition)

	def test_reservation_overlap(self):
		args = dict(
			customer=self.customer.name,
			reservation_date=today(),
			from_date=today(),
			to_date=add_days(today(), 2),
			container_type=self.type.name,
			quantity=1,
			container=self.a.name,
		)
		self.create("Rent Reservation", **args).submit()
		with self.assertRaises(frappe.ValidationError):
			self.create("Rent Reservation", **args)

	def test_negative_and_date_validation(self):
		with self.assertRaises(frappe.ValidationError):
			self.contract(trips=-1)
		with self.assertRaises(frappe.ValidationError):
			self.create(
				"Truck Permit",
				truck=self.vehicle.name,
				permit_type="Road",
				permit_number="T",
				issue_date=today(),
				expiry_date=add_days(today(), -1),
			)

	def test_odometer(self):
		r = self.create(
			"Truck KM Reading", truck=self.vehicle.name, reading_date=today(), current_km=120
		).submit()
		self.assertEqual(self.vehicle.reload().last_odometer, 120)
		with self.assertRaises(frappe.ValidationError):
			self.create("Truck KM Reading", truck=self.vehicle.name, reading_date=today(), current_km=110)
		r.cancel()
		self.assertEqual(self.vehicle.reload().last_odometer, 100)

	def test_double_assignment(self):
		c = self.contract()
		with self.assertRaises(frappe.ValidationError):
			self.move(c, "Delivery")
		with self.assertRaises(frappe.ValidationError):
			self.contract("Trash")

	def test_invoice_payment_outstanding(self):
		c = self.contract()
		invoice = frappe.get_doc("Sales Invoice", make_invoice(c.name))
		invoice.submit()
		self.assertEqual(invoice.grand_total, 200)
		with self.assertRaises(frappe.ValidationError):
			make_invoice(c.name)
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		bank = frappe.db.get_value(
			"Account", {"company": self.company, "account_type": "Cash", "is_group": 0}, "name"
		)
		payment = get_payment_entry("Sales Invoice", invoice.name, bank_account=bank)
		payment.reference_no = self.prefix
		payment.reference_date = today()
		payment.insert()
		payment.submit()
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice.name, "outstanding_amount"), 0)
		_, rows = execute_report("Contract Payment Report", {"contract": c.name})
		self.assertEqual(rows[0].settled, 200)

	def test_reports_metadata(self):
		for r in frappe.get_all(
			"Report", filters={"module": "Container"}, fields=["name", "ref_doctype", "report_type", "json"]
		):
			self.assertTrue(frappe.db.exists("DocType", r.ref_doctype))
			if r.report_type == "Report Builder":
				import json

				for f, dt in json.loads(r.json)["fields"]:
					self.assertTrue(
						f == "name" or f == "docstatus" or frappe.get_meta(dt).has_field(f), (r.name, f)
					)
			elif r.report_type == "Script Report":
				execute_report(r.name)
		self.assertTrue(frappe.db.exists("Workspace", "Container Management"))

	def test_no_manual_assignment(self):
		self.a.status = "Rented"
		with self.assertRaises(frappe.ValidationError):
			self.a.save()

	def tax_template(self):
		account = frappe.db.get_value(
			"Account", {"company": self.company, "account_type": "Tax", "is_group": 0}, "name"
		)
		if not account:
			parent = frappe.db.get_value(
				"Account", {"company": self.company, "root_type": "Liability", "is_group": 1}, "name"
			)
			account = self.create(
				"Account",
				account_name=self.prefix + " VAT",
				company=self.company,
				parent_account=parent,
				account_type="Tax",
			).name
		return self.create(
			"Sales Taxes and Charges Template",
			title=self.prefix,
			company=self.company,
			taxes=[dict(charge_type="On Net Total", account_head=account, description="Test VAT", rate=15)],
		)

	def test_tax_inclusive_and_exclusive(self):
		template = self.tax_template()
		from container.billing import invoice_preview

		c = self.contract()
		c.tax_treatment = "Price Excludes Tax"
		c.sales_tax_template = template.name
		invoice = invoice_preview(c)
		self.assertAlmostEqual(invoice.grand_total, 230, places=2)
		c.tax_treatment = "Price Includes Tax"
		invoice = invoice_preview(c)
		self.assertAlmostEqual(invoice.grand_total, 200, places=2)
		self.assertAlmostEqual(invoice.net_total, 173.91, places=2)
		c.tax_treatment = "Exempt"
		invoice = invoice_preview(c)
		self.assertEqual(invoice.grand_total, 200)
		self.assertFalse(invoice.taxes)

	def test_commission_rule_and_duplicate(self):
		c = self.contract()
		invoice = frappe.get_doc("Sales Invoice", make_invoice(c.name))
		invoice.submit()
		person = self.create(
			"Sales Person",
			sales_person_name=self.prefix,
			parent_sales_person=frappe.db.get_value("Sales Person", {"is_group": 1}, "name"),
		)
		rule = self.create(
			"Commission Rule",
			sales_person=person.name,
			commission_type="Percentage",
			percentage=10,
			effective_from=today(),
			active=1,
		)
		args = dict(
			contract=c.name,
			customer=self.customer.name,
			sales_person=person.name,
			invoice=invoice.name,
			commission_rule=rule.name,
		)
		entry = self.create("Commission Entry", **args).submit()
		self.assertEqual(entry.commission_amount, 20)
		with self.assertRaises(frappe.ValidationError):
			self.create("Commission Entry", **args)
		with self.assertRaises(frappe.ValidationError):
			invoice.cancel()
		entry.cancel()
		invoice.reload().cancel()

	def test_refund_traceability(self):
		c = self.contract()
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		invoice = frappe.get_doc("Sales Invoice", make_invoice(c.name))
		invoice.submit()
		bank = frappe.db.get_value(
			"Account", {"company": self.company, "account_type": "Cash", "is_group": 0}, "name"
		)
		pay = get_payment_entry("Sales Invoice", invoice.name, bank_account=bank)
		pay.set("references", [])
		pay.payment_type = "Pay"
		pay.paid_from, pay.paid_to = pay.paid_to, pay.paid_from
		pay.paid_from_account_currency, pay.paid_to_account_currency = (
			pay.paid_to_account_currency,
			pay.paid_from_account_currency,
		)
		pay.reference_no = self.prefix
		pay.reference_date = today()
		pay.insert()
		pay.submit()
		args = dict(
			customer=self.customer.name,
			contract=c.name,
			date=today(),
			amount=200,
			payment_entry=pay.name,
			reason="Refund",
		)
		withdrawal = self.create("Client Withdrawal", **args).submit()
		with self.assertRaises(frappe.ValidationError):
			self.create("Client Withdrawal", **args)
		with self.assertRaises(frappe.ValidationError):
			pay.cancel()
		withdrawal.cancel()
		pay.reload().cancel()

	def test_operator_permissions(self):
		user = self.create(
			"User",
			email=self.prefix.lower() + "@example.invalid",
			first_name="Container Test",
			send_welcome_email=0,
			roles=[dict(role="Container Operator")],
		)
		frappe.set_user(user.name)
		self.assertTrue(frappe.has_permission("Container Movement", "create"))
		self.assertTrue(frappe.has_permission("Container Contract", "cancel"))
		self.assertFalse(frappe.has_permission("Sales Invoice", "create"))
		self.assertTrue(frappe.has_permission("Commission Entry", "read"))
		with self.assertRaises(frappe.PermissionError):
			execute_report("Contract Outstanding Report")

	def test_related_roles_have_full_container_permissions(self):
		roles = {
			"System Manager",
			"Container Manager",
			"Container Operator",
			"Container Reports User",
			"Accounts User",
			"Accounts Manager",
			"Fleet Manager",
		}
		actions = {
			"read",
			"write",
			"create",
			"delete",
			"report",
			"export",
			"import",
			"share",
			"print",
			"email",
			"select",
		}
		for doctype in frappe.get_all(
			"DocType", filters={"module": "Container", "istable": 0}, pluck="name"
		):
			meta = frappe.get_meta(doctype)
			permissions = {row.role: row for row in meta.permissions if not row.permlevel}
			self.assertTrue(roles.issubset(permissions), doctype)
			for role in roles:
				for action in actions:
					self.assertEqual(permissions[role].get(action), 1, f"{doctype}: {role}: {action}")
				if meta.is_submittable:
					for action in ("submit", "cancel", "amend"):
						self.assertEqual(permissions[role].get(action), 1, f"{doctype}: {role}: {action}")

	def test_reservation_completion_releases_capacity(self):
		args = dict(
			customer=self.customer.name,
			reservation_date=today(),
			from_date=today(),
			to_date=add_days(today(), 2),
			container_type=self.type.name,
			quantity=2,
		)
		reservation = self.create("Rent Reservation", **args).submit()
		reservation.set_reservation_status("Confirmed")
		self.assertEqual(reservation.reload().status, "Confirmed")
		reservation.set_reservation_status("Completed")
		self.create("Rent Reservation", **args).submit()

	def test_late_and_complete(self):
		c = self.contract()
		frappe.db.set_value("Container Contract", c.name, "contract_to", add_days(today(), -1))
		from container.tasks import daily

		daily()
		self.assertEqual(self.a.reload().status, "Late")
		with self.assertRaises(frappe.ValidationError):
			c.complete()
		self.move(c, "Return")
		c.reload().complete()
		self.assertEqual(c.reload().status, "Completed")

	def test_delivery_protects_reserved_capacity(self):
		other = self.create(
			"Customer",
			customer_name=self.prefix + " other",
			customer_type="Company",
			customer_group=self.customer.customer_group,
			territory=self.customer.territory,
		)
		self.create(
			"Rent Reservation",
			customer=other.name,
			reservation_date=today(),
			from_date=today(),
			to_date=add_days(today(), 2),
			container_type=self.type.name,
			quantity=2,
		).submit()
		with self.assertRaises(frappe.ValidationError):
			self.contract()

	def test_return_cannot_reopen_closed_contract(self):
		c = self.contract()
		ret = self.move(c, "Return")
		c.reload().complete()
		with self.assertRaises(frappe.ValidationError):
			ret.cancel()

	def test_workspace_and_cards(self):
		import json

		workspace = frappe.get_doc("Workspace", "Container Management")
		for link in workspace.links:
			if link.type == "Link":
				self.assertTrue(frappe.db.exists(link.link_type, link.link_to), link.link_to)
		for row in workspace.number_cards:
			card = frappe.get_doc("Number Card", row.number_card_name)
			if card.type == "Document Type":
				frappe.get_list(
					card.document_type,
					filters=json.loads(card.filters_json),
					fields=["name"],
					limit_page_length=1,
				)
			else:
				from container.reporting import outstanding_card

				self.assertIn("value", outstanding_card())


def run():
	suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestWorkflows)
	result = unittest.TextTestRunner(verbosity=2).run(suite)
	frappe.db.rollback()
	if not result.wasSuccessful():
		raise RuntimeError("Container integration tests failed")
	return {"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors)}
