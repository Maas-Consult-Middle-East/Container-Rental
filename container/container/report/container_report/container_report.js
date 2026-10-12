frappe.query_reports["Container Report"] = {
	filters: [
		{ fieldname: "container_status", label: __("Container Status"), fieldtype: "Select",
			options: ["", "Rented", "Pull", "Late", "Empty"] },
		{ fieldname: "from_date", label: __("From"), fieldtype: "Date",
			description: __("Rental start date, inclusive") },
		{ fieldname: "to_date", label: __("To"), fieldtype: "Date",
			description: __("Rental start date, inclusive") },
		{ fieldname: "container", label: __("Container"), fieldtype: "Link", options: "Container" },
		{ fieldname: "customer", label: __("Client"), fieldtype: "Link", options: "Customer" },
	],
	formatter(value, row, column, data, default_formatter) {
		if (column.fieldname === "location" && value &&
			/^https:\/\/www\.google\.com\/maps\?q=-?[\d.]+,-?[\d.]+$/.test(value)) {
			return `<a href="${frappe.utils.escape_html(value)}" target="_blank" rel="noopener noreferrer">${__("Map")}</a>`;
		}
		return default_formatter(value, row, column, data);
	},
};
