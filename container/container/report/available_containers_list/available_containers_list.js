frappe.query_reports["Available Containers List"] = {
	filters: [
		{ fieldname: "name", label: __("Container"), fieldtype: "Link", options: "Container" },
		{ fieldname: "container_size", label: __("Container Size"), fieldtype: "Data" },
		{ fieldname: "classification", label: __("Classification"), fieldtype: "Select", options: "\n12\n20" },
		{ fieldname: "branch_name", label: __("Branch"), fieldtype: "Link", options: "Branch" },
	],
};
