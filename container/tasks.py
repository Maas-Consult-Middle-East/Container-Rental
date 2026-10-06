import frappe
from frappe.utils import today


def daily():
	# Never complete a contract or clear an assignment automatically.
	for row in frappe.get_all("Container", filters={"status": "Rented"}, fields=["name", "current_contract"]):
		end = frappe.db.get_value("Container Contract", row.current_contract, "contract_to")
		if end and str(end) < today():
			frappe.db.get_value("Container", row.name, "name", for_update=True)
			if frappe.db.get_value("Container", row.name, "status") == "Rented":
				frappe.db.set_value("Container", row.name, "status", "Late")
	for name in frappe.get_all("Truck Permit", pluck="name"):
		doc = frappe.get_doc("Truck Permit", name)
		doc.validate()
		doc.db_set("status", doc.status)
