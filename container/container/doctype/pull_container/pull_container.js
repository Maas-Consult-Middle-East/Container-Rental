frappe.ui.form.on("Pull Container", {
	setup(frm) {
		frm.set_query("container", () => ({
			filters: { status: "Rented" },
		}));
		frm.set_query("supervisor", () => ({
			filters: { designation: "Supervisor" },
		}));
	},

	refresh(frm) {
		frm.set_df_property("container", "read_only", !frm.is_new());
		if (!frm.is_new() && frm.doc.docstatus !== 2
			&& frappe.model.can_create("Emptying Container")) {
			frm.add_custom_button(__("Emptying Container"), () => {
				frappe.model.open_mapped_doc({
					method: "container.workflows.make_emptying_from_pull_container",
					frm,
				});
			}, __("Create"));
		}
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Container Trip"), () => {
				frappe.model.open_mapped_doc({
					method: "container.workflows.make_trip_from_pull_container",
					frm,
				});
			}, __("Create"));
		}
	},
});
