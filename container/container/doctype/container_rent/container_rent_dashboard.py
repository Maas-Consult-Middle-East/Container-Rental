from frappe import _


def get_data():
	return {
		"fieldname": "container_rent",
		"transactions": [{"label": _("Billing"), "items": ["Sales Invoice"]}],
	}
