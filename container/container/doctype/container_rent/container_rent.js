frappe.ui.form.on("Container Rent", {
	setup(frm) {
		frm.set_query("supervisor", () => ({
			filters: { designation: "Supervisor" },
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Container Trip"), () => {
				frappe.model.open_mapped_doc({
					method: "container.workflows.make_trip_from_container_rent",
					frm,
				});
			}, __("Create"));
		}
	},

	container_number(frm) {
		console.log("Container field changed");
		console.log("Selected:", frm.doc.container_number);
	},
});
