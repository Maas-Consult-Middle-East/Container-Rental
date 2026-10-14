# Copyright (c) 2026, Salman Adayatt and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ContainerRent(Document):
	def on_submit(self):
		container = frappe.get_doc("Container", self.container_number)
		container.status = "Rented"
		container.save()