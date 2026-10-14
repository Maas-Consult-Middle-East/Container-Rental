from frappe import _


def get_data():
	return {
		"fieldname": "container_rent",
		"internal_links": {"Container Contract": "container_contract"},
		"transactions": [
			{"label": _("Contract"), "items": ["Container Contract"]},
			{"label": _("Billing"), "items": ["Sales Invoice"]},
		],
	}
