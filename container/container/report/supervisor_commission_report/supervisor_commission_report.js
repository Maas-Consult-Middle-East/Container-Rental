frappe.query_reports["Supervisor Commission Report"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date" },
		{
			fieldname: "supervisor", label: __("Supervisor"), fieldtype: "Link", options: "Employee",
			get_query: () => ({ filters: { designation: "Supervisor" } }),
		},
		{ fieldname: "name", label: __("Rent A Container"), fieldtype: "Link", options: "Rent A Container" },
	],
};
