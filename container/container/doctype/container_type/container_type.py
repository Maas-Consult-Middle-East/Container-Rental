from frappe.model.document import Document

from container.operations import nonnegative


class ContainerType(Document):
	def validate(self):
		nonnegative(self, ["default_rental_rate"])
