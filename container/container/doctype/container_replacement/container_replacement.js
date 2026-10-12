frappe.ui.form.on("Container Replacement", {
	setup(frm) {
		frm.set_query("supervisor", () => ({
			filters: { designation: "Supervisor" },
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Container Trip"), () => {
				frappe.model.open_mapped_doc({
					method: "container.workflows.make_trip_from_container_replacement",
					frm,
				});
			}, __("Create"));
		}
	},
});
