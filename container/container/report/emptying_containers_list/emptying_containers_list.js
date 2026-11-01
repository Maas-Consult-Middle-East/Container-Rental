frappe.query_reports["Emptying Containers List"] = {
	filters: [
		{ fieldname: "name", label: __("Emptying ID"), fieldtype: "Link", options: "Emptying Container" },
		{ fieldname: "docstatus", label: __("Document Status"), fieldtype: "Select", options: ["", "Draft", "Submitted"] },
		{ fieldname: "container", label: __("Container"), fieldtype: "Link", options: "Container" },
		{ fieldname: "emptying_date", label: __("Emptying Date"), fieldtype: "DateRange" },
		{ fieldname: "baladiayya", label: __("Baladiyya"), fieldtype: "Link", options: "Baladiyya" },
		{ fieldname: "driver", label: __("Driver"), fieldtype: "Link", options: "Driver" },
		{ fieldname: "driver_commission", label: __("Driver Commission"), fieldtype: "Data" },
		{ fieldname: "supervisor", label: __("Supervisor"), fieldtype: "Link", options: "Employee" },
		{ fieldname: "truck", label: __("Truck"), fieldtype: "Link", options: "Vehicle" },
		{ fieldname: "journal_entry", label: __("Journal Entry"), fieldtype: "Link", options: "Journal Entry" },
		{ fieldname: "notes", label: __("Notes"), fieldtype: "Data" },
	],
};
