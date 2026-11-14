import frappe
from frappe import _
from frappe.model.document import Document


class Container(Document):
	def after_insert(self):
		if frappe.db.exists("Item", self.name):
			return

		price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or _("Standard Selling")
		if not frappe.db.exists("Price List", {"name": price_list, "enabled": 1, "selling": 1}):
			frappe.throw(_("Set an enabled Selling Price List in Selling Settings before creating a Container."))

		# Container creation authorizes these fixed rental records, including for container-only roles.
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": self.name,
			"item_name": self.name,
			"item_group": _("Services"),
			"stock_uom": _("Nos"),
			"is_stock_item": 0,
			"is_sales_item": 1,
			"is_purchase_item": 0,
		}).insert(ignore_permissions=True)
		frappe.get_doc({
			"doctype": "Item Price",
			"item_code": item.name,
			"uom": item.stock_uom,
			"price_list": price_list,
			"price_list_rate": 500,
		}).insert(ignore_permissions=True)
