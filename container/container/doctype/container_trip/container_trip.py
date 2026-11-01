import frappe
from frappe import _
from frappe.model.document import Document


class ContainerTrip(Document):
	def validate(self):
		if self.source_doctype and self.source_name and frappe.db.exists(
			"Container Trip",
			{
				"source_doctype": self.source_doctype,
				"source_name": self.source_name,
				"container": self.container,
				"docstatus": ["!=", 2],
				"name": ["!=", self.name],
			},
		):
			frappe.throw(_("An active Container Trip already exists for this container and source document."))
