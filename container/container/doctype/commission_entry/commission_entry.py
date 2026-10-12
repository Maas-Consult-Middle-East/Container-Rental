import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class CommissionEntry(Document):
	def validate(self):
		trip = frappe.get_doc("Container Trip", self.trip)
		trip.check_permission("read")
		if trip.docstatus != 1:
			frappe.throw(_("Commission Entry requires a submitted Container Trip."))
		if self.commission_type == "Driver":
			if not self.driver or self.driver != trip.driver:
				frappe.throw(_("Driver must match the Container Trip."))
			self.supervisor = None
		elif self.commission_type == "Supervisor":
			if not self.supervisor or self.supervisor != trip.supervisor:
				frappe.throw(_("Supervisor must match the Container Trip."))
			self.driver = None
		else:
			frappe.throw(_("Select Driver or Supervisor as the commission type."))
		if flt(self.amount) <= 0:
			frappe.throw(_("Commission amount must be greater than zero."))
		if frappe.db.exists(
			"Commission Entry",
			{
				"trip": self.trip,
				"commission_type": self.commission_type,
				"docstatus": ["!=", 2],
				"name": ["!=", self.name],
			},
		):
			frappe.throw(_("An active commission of this type already exists for the trip."))
