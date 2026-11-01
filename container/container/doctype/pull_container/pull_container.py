import frappe
from frappe import _
from frappe.model.document import Document


class PullContainer(Document):
	def validate(self):
		containers = [row.container for row in self.containers]
		for row in self.containers:
			if containers.count(row.container) > 1:
				frappe.throw(_("Row #{0}: Container {1} is selected more than once.").format(row.idx, row.container))
		previous = self.get_doc_before_save()
		if previous and sorted(row.container for row in previous.containers) != sorted(containers):
			frappe.throw(_("The containers cannot be changed after saving. Create a new Pull Container instead."))
		if self.is_new():
			for row in self.containers:
				status = frappe.db.get_value("Container", row.container, "status", for_update=True)
				if status not in ("Rented", "Late"):
					frappe.throw(
						_("Row #{0}: Only a Rented or Late container can be selected for pulling.").format(row.idx)
					)

	def after_insert(self):
		for row in self.containers:
			frappe.db.set_value("Container", row.container, "status", "Pull")

	def on_cancel(self):
		self.restore_rented_status()

	def on_trash(self):
		if self.docstatus == 0:
			self.restore_rented_status()

	def restore_rented_status(self):
		for row in self.containers:
			status = frappe.db.get_value("Container", row.container, "status", for_update=True)
			other_pull = frappe.get_all(
				"Pull Container",
				filters=[
					["Pull Container Item", "container", "=", row.container],
					["name", "!=", self.name],
					["docstatus", "!=", 2],
				],
				limit_page_length=1,
			)
			if status == "Pull" and not other_pull:
				frappe.db.set_value("Container", row.container, "status", "Rented")
