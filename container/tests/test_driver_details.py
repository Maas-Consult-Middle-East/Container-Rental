"""Document detail access and response contract without changing site data."""
import unittest
from unittest.mock import MagicMock, patch

import frappe

from container import driver_api


class TestDriverDetails(unittest.TestCase):
	def setUp(self):
		self.doc = frappe._dict(
			doctype="Rent A Container", name="RENT-1", driver="DRIVER-1", docstatus=1,
			client="CUSTOMER-1", client_name="Customer", supervisor=None,
			latitude="24.7", longitude="46.6", cost="250", driver_commission="20",
			containers=[frappe._dict(container="C-1", container_size="12", classification="12"),
				frappe._dict(container="C-2", container_size="20", classification="20")],
			private_custom_field="must not be returned",
		)
		self.addCleanup(patch.stopall)
		patch.object(frappe.local, "flags", new=frappe._dict(in_test=True), create=True).start()
		patch.object(driver_api, "session_drivers", return_value=["DRIVER-1"]).start()
		self.get_doc = patch.object(frappe, "get_doc", return_value=self.doc).start()
		patch.object(frappe, "db", new=MagicMock()).start().get_value.return_value = "Display name"
		patch.object(driver_api, "_", side_effect=lambda value: value).start()
		patch.object(frappe, "throw", side_effect=lambda message, exception: self._raise(exception, message)).start()

	@staticmethod
	def _raise(exception, message):
		raise exception(message)

	def test_delivery_returns_full_original_rows_and_allowed_fields(self):
		result = driver_api.get_job_details("Rent A Container", "RENT-1")
		self.assertEqual(len(result["containers"]), 2)
		self.assertEqual(result["containers"][1]["classification"], "20")
		self.assertEqual(result["cost"], "250")
		self.assertEqual(result["latitude"], 24.7)
		self.assertNotIn("private_custom_field", result)

	def test_collection_includes_rental_and_notes(self):
		self.doc.update(doctype="Pull Container", docstatus=0, rent_a_container="RENT-1", notes="Use rear entrance")
		result = driver_api.get_job_details("Pull Container", "PULL-1")
		self.assertEqual(result["notes"], "Use rear entrance")
		self.assertEqual(result["rent_a_container"], "RENT-1")
		self.assertEqual(result["client_name"], "Display name")

	def test_another_driver_is_denied(self):
		self.doc.driver = "OTHER"
		with self.assertRaises(frappe.PermissionError):
			driver_api.get_job_details("Rent A Container", "RENT-1")

	def test_draft_delivery_and_cancelled_documents_are_denied(self):
		for doctype, status in [("Rent A Container", 0), ("Rent A Container", 2), ("Pull Container", 2)]:
			with self.subTest(doctype=doctype, status=status):
				self.doc.docstatus = status
				with self.assertRaises(frappe.PermissionError):
					driver_api.get_job_details(doctype, "DOC-1")

	def test_arbitrary_doctype_is_rejected_before_read(self):
		with self.assertRaises(frappe.ValidationError):
			driver_api.get_job_details("User", "Administrator")
		self.get_doc.assert_not_called()

	def test_unlinked_user_is_denied_before_read(self):
		with patch.object(driver_api, "session_drivers", side_effect=frappe.PermissionError):
			with self.assertRaises(frappe.PermissionError):
				driver_api.get_job_details("Rent A Container", "RENT-1")
		self.get_doc.assert_not_called()
