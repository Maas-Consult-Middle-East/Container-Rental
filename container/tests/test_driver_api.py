"""Driver app lists: own documents only, pulled/emptied containers drop out."""

import unittest
from unittest.mock import patch

import frappe

from container import driver_api


class TestDriverApi(unittest.TestCase):
	def test_lists_are_scoped_to_driver_and_cycle(self):
		frappe.db.savepoint("driver_api_test")
		try:
			def driver(name):
				return frappe.get_doc({"doctype": "Driver", "full_name": name, "status": "Active"}).insert().name

			me, other = driver("TEST-DRV-ME"), driver("TEST-DRV-OTHER")
			containers = []
			for _ in range(3):
				name = "TEST-DRV-" + frappe.generate_hash(length=10)
				frappe.get_doc({"doctype": "Container", "name": name, "container_number": name,
					"status": "Empty"}).db_insert()
				containers.append(name)
			rent_type = frappe.get_doc({"doctype": "Rent Type",
				"rent_type": "TEST-DRV-" + frappe.generate_hash(length=10)}).insert()

			def rental(driver_name, names):
				doc = frappe.get_doc({"doctype": "Rent A Container", "rent_type": rent_type.name,
					"driver": driver_name, "latitude": "24.7", "longitude": "46.6",
					"containers": [{"container": n} for n in names]}).insert()
				doc.submit()
				return doc.name

			mine = rental(me, containers[:2])
			theirs = rental(other, containers[2:])

			with patch.object(driver_api, "session_drivers", return_value=[me]):
				deliveries = {d["name"]: d for d in driver_api.get_deliveries()}
				self.assertIn(mine, deliveries)
				self.assertNotIn(theirs, deliveries)
				self.assertEqual(len(deliveries[mine]["containers"]), 2)
				self.assertEqual((deliveries[mine]["latitude"], deliveries[mine]["longitude"]), (24.7, 46.6))

				pull = frappe.get_doc({"doctype": "Pull Container", "driver": me, "rent_a_container": mine,
					"containers": [{"container": containers[0]}]}).insert()
				deliveries = {d["name"]: d for d in driver_api.get_deliveries()}
				self.assertEqual([c["container"] for c in deliveries[mine]["containers"]], [containers[1]])
				self.assertIn(pull.name, [p["name"] for p in driver_api.get_pulls()])

				frappe.get_doc({"doctype": "Pull Container", "driver": me,
					"containers": [{"container": containers[1]}]}).insert()
				self.assertNotIn(mine, [d["name"] for d in driver_api.get_deliveries()])

				frappe.get_doc({"doctype": "Emptying Container", "container": containers[0]}).insert()
				self.assertNotIn(pull.name, [p["name"] for p in driver_api.get_pulls()])

			with patch.object(driver_api, "session_drivers", return_value=[other]):
				self.assertEqual([d["name"] for d in driver_api.get_deliveries() if d["name"] in (mine, theirs)],
					[theirs])
				self.assertNotIn(pull.name, [p["name"] for p in driver_api.get_pulls()])
		finally:
			frappe.db.rollback(save_point="driver_api_test")

	def test_driver_user_field_signs_in(self):
		from container.setup import setup_driver_user_field

		setup_driver_user_field()  # Schema change, as after_migrate does; runs before the savepoint.
		fieldname = driver_api.driver_user_fields()[0]
		frappe.db.savepoint("driver_user_test")
		try:
			email = f"test-driver-{frappe.generate_hash(length=8)}@example.com"
			frappe.get_doc({"doctype": "User", "email": email, "first_name": "Test Driver",
				"send_welcome_email": 0}).insert(ignore_permissions=True)
			driver = frappe.get_doc({"doctype": "Driver", "full_name": "TEST-DRV-USER", "status": "Active",
				fieldname: email}).insert()
			frappe.set_user(email)
			self.assertEqual(driver_api.session_drivers(), [driver.name])
			self.assertEqual(driver_api.get_me()["driver"], driver.name)
			frappe.set_user("Administrator")
			driver.db_set("status", "Left")
			frappe.set_user(email)
			with self.assertRaises(frappe.PermissionError):
				driver_api.session_drivers()
		finally:
			frappe.set_user("Administrator")
			frappe.db.rollback(save_point="driver_user_test")

	def test_user_without_driver_is_refused(self):
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				driver_api.get_deliveries()
		finally:
			frappe.set_user("Administrator")
