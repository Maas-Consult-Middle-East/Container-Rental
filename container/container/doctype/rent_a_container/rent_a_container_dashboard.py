from frappe import _


def get_data():
	return {
		"fieldname": "container_rent",
		"internal_links": {"Container Contract": "container_contract"},
		"non_standard_fieldnames": {"Pull Container": "rent_a_container"},
		"transactions": [
			{"label": _("Contract"), "items": ["Container Contract"]},
			{"label": _("Billing"), "items": ["Sales Invoice"]},
			{"label": _("Operations"), "items": ["Pull Container"]},
		],
	}
