frappe.provide("container.utils");

// Trips, pulls and emptyings map one container each; ask which one when the source holds several.
container.utils.open_mapped_doc_for_container = function (frm, method) {
	const containers = (frm.doc.containers || []).map((row) => row.container).filter(Boolean);
	const open = (container) => frappe.model.open_mapped_doc({ method, frm, args: { container } });
	if (containers.length === 1) return open(containers[0]);
	frappe.prompt(
		{ fieldname: "container", fieldtype: "Select", label: __("Container"), options: containers, reqd: 1 },
		(values) => open(values.container),
		__("Select Container"),
	);
};
