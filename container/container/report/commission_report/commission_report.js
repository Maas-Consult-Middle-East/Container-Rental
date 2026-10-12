frappe.query_reports["Commission Report"] = {
	filters: [
		{
			fieldname: "person_type",
			label: __("Driver / Supervisor"),
			fieldtype: "Select",
			options: ["", "Driver", "Employee"],
			on_change(report) {
				report.set_filter_value("person", "");
				report.refresh();
			},
		},
		{
			fieldname: "person",
			label: __("Person"),
			fieldtype: "Dynamic Link",
			options: "person_type",
			get_query() {
				return { filters: {} };
			},
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
	],
};
