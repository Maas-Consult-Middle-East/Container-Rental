from frappe.model.document import Document


class ContainerContract(Document):
	def validate(self):
		self.container_names = ", ".join(row.container for row in self.containers if row.container)
