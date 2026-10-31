import frappe
from frappe import _
from frappe.model.document import Document


class EmptyingContainer(Document):
	def validate(self):
		previous = self.get_doc_before_save()
		if previous and previous.container != self.container:
			frappe.throw(_("The container cannot be changed after saving. Create a new Emptying Container instead."))
		if self.is_new():
			status = frappe.db.get_value("Container", self.container, "status", for_update=True)
			if status != "Pull":
				frappe.throw(_("Only a container with status Pull can be emptied."))

	def after_insert(self):
		frappe.db.set_value("Container", self.container, "status", "Empty")

	def on_submit(self):
		from container.emptying_accounting import create_disposal_journal

		self.db_set("journal_entry", create_disposal_journal(self))

	def on_cancel(self):
		if self.journal_entry:
			journal = frappe.get_doc("Journal Entry", self.journal_entry)
			if journal.docstatus == 1:
				journal.cancel()
		self.restore_pull_status()

	def on_trash(self):
		if self.docstatus == 0:
			self.restore_pull_status()

	def restore_pull_status(self):
		status = frappe.db.get_value("Container", self.container, "status", for_update=True)
		other_emptying = frappe.db.exists(
			"Emptying Container",
			{"container": self.container, "name": ["!=", self.name], "docstatus": ["!=", 2]},
		)
		if status == "Empty" and not other_emptying:
			frappe.db.set_value("Container", self.container, "status", "Pull")