# Copyright (c) 2026, Salman Adayatt and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PullContainer(Document):
	def validate(self):
		previous = self.get_doc_before_save()
		if previous and previous.container != self.container:
			frappe.throw(_("The container cannot be changed after saving. Create a new Pull Container instead."))
		if self.is_new():
			status = frappe.db.get_value("Container", self.container, "status", for_update=True)
			if status not in ("Rented", "Late"):
				frappe.throw(_("Only a Rented or Late container can be selected for pulling."))

	def after_insert(self):
		frappe.db.set_value("Container", self.container, "status", "Pull")

	def on_cancel(self):
		self.restore_rented_status()

	def on_trash(self):
		if self.docstatus == 0:
			self.restore_rented_status()

	def restore_rented_status(self):
		status = frappe.db.get_value("Container", self.container, "status", for_update=True)
		other_pull = frappe.db.exists(
			"Pull Container",
			{"container": self.container, "name": ["!=", self.name], "docstatus": ["!=", 2]},
		)
		if status == "Pull" and not other_pull:
			frappe.db.set_value("Container", self.container, "status", "Rented")
