import unittest
from unittest.mock import patch

import frappe

from container.container.report.rented_containers_list import rented_containers_list as report


class TestRentedContainersList(unittest.TestCase):
	def run_report(self, filters=None, can_read=True, invoices=None, credits=None, reversed=None):
		rows = [frappe._dict(name="RENT-1", container="C1", driver="DR-001", supervisor="EMP-001", driver_commission=20, supervisor_commission=30),
			frappe._dict(name="RENT-1", container="C2"),
			frappe._dict(name="RENT-2", container="C3")]
		with patch.object(report, "get_rows", return_value=rows), \
			patch.object(report, "source_invoices", return_value=invoices or []), \
			patch.object(report, "reversed_rentals", return_value=reversed or set()), \
			patch.object(report, "linked_records", return_value={
				"C1": {"status": "Rented"}, "C2": {"status": "Pull"}, "C3": {"status": "Empty"},
				"DR-001": {"full_name": "Demo Driver"}, "EMP-001": {"employee_name": "Demo Supervisor"}}), \
			patch.object(frappe, "has_permission", return_value=can_read), \
			patch.object(frappe, "get_list", side_effect=lambda doctype, **kwargs:
				(credits or []) if kwargs["filters"].get("is_return") else (invoices or [])) as query:
			result = report.execute(filters)
			if can_read:
				if invoices:
					self.assertEqual(query.call_args.kwargs["filters"]["docstatus"], 1)
					self.assertEqual(query.call_args.kwargs["filters"]["is_return"], 1)
					self.assertEqual(query.call_args.kwargs["filters"]["return_against"], ["in", [i.name for i in invoices]])
			else:
				query.assert_not_called()
			return result

	def test_multiple_containers_status_and_invoice(self):
		columns, rows = self.run_report(invoices=[frappe._dict(
			name="INV-1", container_rent="RENT-1", status="Partly Paid")])
		self.assertEqual([r.current_status for r in rows], ["Rented", "Pulled", "Empty"])
		self.assertEqual([r.invoice_no for r in rows], ["INV-1", "INV-1", None])
		self.assertEqual([r.payment_status for r in rows], ["Partly Paid", "Partly Paid", "No Invoice Found"])
		self.assertEqual(next(c for c in columns if c["fieldname"] == "invoice_no")["options"], "Sales Invoice")
		self.assertEqual(rows[0].driver_name, "Demo Driver")
		self.assertEqual(rows[0].supervisor_name, "Demo Supervisor")
		self.assertFalse(any(c["fieldname"] in ("driver", "supervisor") for c in columns))
		self.assertEqual([c["label"] for c in columns if "Commission" in c["label"]],
			["Driver Commission", "Supervisor Commission"])
		self.assertTrue(all(row.has_credit_note == "No" for row in rows))

	def test_filters_and_multiple_invoices(self):
		_, rows = self.run_report({"current_status": "Pulled", "payment_status": "Paid", "invoice_no": "INV-2"},
			invoices=[frappe._dict(name="INV-1", container_rent="RENT-1", status="Unpaid"),
				frappe._dict(name="INV-2", container_rent="RENT-1", status="Paid")])
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].container, "C2")

	def test_invoice_permissions(self):
		_, rows = self.run_report(can_read=False)
		self.assertTrue(all(r.invoice_no is None and r.payment_status == "Not Available" for r in rows))
		self.assertTrue(all(not r.credit_notes for r in rows))
		self.assertTrue(all(r.has_credit_note == "Not Available" for r in rows))

	def test_multiple_credit_notes_linked_through_original_invoice(self):
		invoice = frappe._dict(name="INV-1", container_rent="RENT-1", status="Credit Note Issued", currency="SAR")
		credits = [frappe._dict(name="CN-1", return_against="INV-1", grand_total=-100),
			frappe._dict(name="CN-2", return_against="INV-1", grand_total=-200)]
		_, rows = self.run_report(invoices=[invoice], credits=credits)
		self.assertEqual(len(rows), 3)
		self.assertEqual(rows[0].credit_notes, "CN-1, CN-2")
		self.assertEqual(rows[0].credited_amount, 300)
		self.assertEqual(rows[0].has_credit_note, "Yes")
		self.assertEqual(rows[0].invoice_currency, "SAR")
		self.assertEqual(rows[2].credited_amount, 0)
		_, filtered = self.run_report({"credit_note": "CN-2"}, invoices=[invoice], credits=credits)
		self.assertEqual([row.container for row in filtered], ["C1", "C2"])
		_, credited = self.run_report({"has_credit_note": "Yes"}, invoices=[invoice], credits=credits)
		self.assertEqual([row.container for row in credited], ["C1", "C2"])
		_, uncredited = self.run_report({"has_credit_note": "No"}, invoices=[invoice], credits=credits)
		self.assertEqual([row.container for row in uncredited], ["C3"])

	def test_full_commission_reversal_without_invoice_visibility(self):
		_, rows = self.run_report(can_read=False, reversed={"RENT-1"})
		self.assertEqual(rows[0].driver_commission, 20)
		self.assertEqual(rows[0].supervisor_commission, 30)
		self.assertEqual(rows[0].net_driver_commission, -20)
		self.assertEqual(rows[0].net_supervisor_commission, -30)
