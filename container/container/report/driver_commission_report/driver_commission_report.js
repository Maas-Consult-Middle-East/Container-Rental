frappe.query_reports["Driver Commission Report"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date" },
		{ fieldname: "driver", label: __("Driver"), fieldtype: "Link", options: "Driver" },
		{
			fieldname: "operation", label: __("Operation"), fieldtype: "Select",
			options: ["", "Rent A Container", "Pull Container", "Emptying Container"],
		},
		{ fieldname: "reference", label: __("Reference"), fieldtype: "Data" },
	],
};
