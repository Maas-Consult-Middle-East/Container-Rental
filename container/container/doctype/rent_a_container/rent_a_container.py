# Copyright (c) 2026, Salman Adayatt and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class RentAContainer(Document):
	def validate(self):
		seen = set()
		for row in self.containers:
			if row.container in seen:
				frappe.throw(_("Row #{0}: Container {1} is selected more than once.").format(row.idx, row.container))
			seen.add(row.container)
		self.update_container_names()

	def update_container_names(self):
		self.container_names = ", ".join(row.container for row in self.containers if row.container)

	def on_submit(self):
		for row in self.containers:
			container = frappe.get_doc("Container", row.container)
			container.status = "Rented"
			container.save()
