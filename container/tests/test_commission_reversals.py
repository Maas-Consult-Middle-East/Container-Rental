import unittest
from unittest.mock import patch

import frappe

from container import commissions
from container.container.report.driver_commission_report import driver_commission_report as driver
from container.container.report.supervisor_commission_report import supervisor_commission_report as supervisor


class TestCommissionReversals(unittest.TestCase):
	def test_partial_and_multiple_returns_reverse_once_and_cancellation_restores(self):
		invoices = [frappe._dict(name="INV-1", container_rent="RENT-1")]
		for active_returns, expected in ((["INV-1"], {"RENT-1"}),
			(["INV-1", "INV-1"], {"RENT-1"}), ([], set())):
			with self.subTest(active_returns=active_returns), patch.object(
				frappe, "get_all", return_value=active_returns
			) as query, patch.object(commissions, "source_invoices", return_value=invoices):
				self.assertEqual(commissions.reversed_rentals(["RENT-1"]), expected)
				self.assertEqual(query.call_args.kwargs["filters"], {
					"return_against": ["in", ["INV-1"]], "is_return": 1, "docstatus": 1})
				self.assertEqual(query.call_args_list[0].kwargs["filters"]["docstatus"], 1)
		# The credit amount deliberately has no bearing on the reversal amount.
		self.assertEqual(commissions.commission_amounts("50", True), {
			"original_commission": 50, "commission_reversal": -50, "commission": -50})
		self.assertEqual(commissions.commission_amounts("50", False)["commission"], 50)

	def test_no_rentals_or_invoices(self):
		with patch.object(frappe, "get_all", return_value=[]) as query:
			self.assertEqual(commissions.reversed_rentals([]), set())
			query.assert_not_called()
			self.assertEqual(commissions.reversed_rentals(["RENT-1"]), set())
			self.assertEqual(query.call_count, 2)

	def test_supervisor_report_preserves_original_and_reverses_full_amount(self):
		rental = frappe._dict(name="RENT-1", supervisor="EMP-1", supervisor_commission="30")
		with patch.object(frappe, "has_permission", return_value=True), \
			patch.object(frappe, "get_list", return_value=[rental]), \
			patch.object(supervisor, "linked_records", return_value={}), \
			patch.object(supervisor, "invoices_by_rental", return_value={}), \
			patch.object(supervisor, "payments_by_invoice", return_value={}), \
			patch.object(supervisor, "reversed_rentals", return_value={"RENT-1"}):
			_, rows = supervisor.execute()
		self.assertEqual(rows[0]["original_commission"], 30)
		self.assertEqual(rows[0]["commission_reversal"], -30)
		self.assertEqual(rows[0]["commission"], -30)

	def test_driver_report_reverses_rental_but_not_separate_operations(self):
		operations = [[frappe._dict(name="RENT-1", rent_a_container="RENT-1", driver="D1", driver_commission=20)],
			[frappe._dict(name="PULL-1", rent_a_container="RENT-1", driver="D1", driver_commission=10)],
			[frappe._dict(name="EMPTY-1", driver="D1", driver_commission=15)]]
		with patch.object(frappe, "has_permission", return_value=True), \
			patch.object(frappe, "get_list", side_effect=operations), \
			patch.object(driver, "linked_records", return_value={}), \
			patch.object(driver, "invoices_by_rental", return_value={}), \
			patch.object(driver, "payments_by_invoice", return_value={}), \
			patch.object(driver, "reversed_rentals", return_value={"RENT-1"}):
			_, rows = driver.execute()
		by_name = {row["reference"]: row for row in rows}
		self.assertEqual(by_name["RENT-1"]["commission_reversal"], -20)
		self.assertEqual(by_name["RENT-1"]["commission"], -20)
		self.assertEqual(by_name["PULL-1"]["commission"], 10)
		self.assertEqual(by_name["EMPTY-1"]["commission"], 15)
